#!/usr/bin/env python3
"""Run SciPIvot cases with a coding agent, the way the paper ran them.

For each case and option order, one fresh agent session reads the prompt from
prompts/BENCH_ASK_PROMPT.md.  In the `project` condition the case's snapshot is
mounted read-only at /project; in `options-only` nothing is mounted.  The
agent runs inside bubblewrap with an empty scratch HOME, so it sees the
snapshot and the system, and not your home directory, your agent settings or
any other case.  `--reconsider 2` continues the same session twice with
prompts/BENCH_RECONSIDER_PROMPT.md, as in the paper's review stages.

Engines (the CLI must be installed on the host and is mounted into the sandbox):
    claude  Claude Code; uses ANTHROPIC_API_KEY (and ANTHROPIC_BASE_URL if set).
            Tools: Read, Grep, Glob only; --safe-mode, no skills, no MCP.
    codex   Codex CLI; uses OPENAI_API_KEY (and OPENAI_BASE_URL if set).
            No AGENTS.md, no rules, no web search.

Output is one JSON line per answer, ready for scripts/score.py:
    {"id": "case_000", "order": "ab", "stage": 0, "response": "<raw reply>", ...}

Example:
    python scripts/fetch_records.py --id case_000 --out records
    python scripts/run_project.py --id case_000 --engine claude --model claude-opus-5 \\
        --effort medium --records records --out runs/opus.jsonl
    python scripts/score.py runs/opus.jsonl
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_records  # noqa: E402
import make_prompt  # noqa: E402
import score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROJECT_AT, HOME_AT, TOOLS_AT = "/project", "/home/agent", "/opt/agent"
SYSTEM_RO = ("/usr", "/etc/resolv.conf", "/etc/alternatives", "/etc/ssl", "/etc/pki",
             "/etc/crypto-policies", "/etc/fonts")
MERGED_USR_LINKS = (("usr/bin", "/bin"), ("usr/sbin", "/sbin"),
                    ("usr/lib", "/lib"), ("usr/lib64", "/lib64"))
TMP_BYTES = 64 * 1024 * 1024
TIMEOUT = 900
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def bwrap_argv(project: Path | None, home: Path, tools: dict, env: dict) -> list:
    if shutil.which("bwrap") is None:
        raise SystemExit("bubblewrap not found (apt install bubblewrap); "
                         "it keeps the agent away from everything but the snapshot")
    argv = ["bwrap", "--unshare-all", "--share-net", "--die-with-parent", "--new-session"]
    for path in SYSTEM_RO:
        argv += ["--ro-bind-try", path, path]
    for target, link in MERGED_USR_LINKS:
        argv += ["--symlink", target, link]
    argv += ["--proc", "/proc", "--dev", "/dev", "--size", str(TMP_BYTES), "--tmpfs", "/tmp"]
    if project is not None:
        argv += ["--ro-bind", str(project.resolve()), PROJECT_AT]
    argv += ["--bind", str(home.resolve()), HOME_AT]
    for name, source in tools.items():
        argv += ["--ro-bind", str(Path(source).resolve()), f"{TOOLS_AT}/{name}"]
    argv += ["--chdir", PROJECT_AT if project is not None else HOME_AT, "--clearenv"]
    for key, value in env.items():
        argv += ["--setenv", key, str(value)]
    return argv + ["--"]


def sandbox_path() -> str:
    roots = tuple(p for p in SYSTEM_RO if Path(p).is_dir())
    links = tuple(link for _, link in MERGED_USR_LINKS)
    keep = []
    for entry in os.environ.get("PATH", "").split(":"):
        if entry and entry not in keep and (entry in links or any(
                entry == r or entry.startswith(r + "/") for r in roots)):
            keep.append(entry)
    return ":".join([f"{TOOLS_AT}/bin", *keep])


def _which(name: str) -> Path:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"`{name}` is not on PATH")
    return Path(found).resolve()


def _toml(value: str) -> str:
    return json.dumps(value)


def claude_command(project, home, model, effort, resume):
    binary = _which("claude")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("set ANTHROPIC_API_KEY")
    env = {"HOME": HOME_AT, "USER": "agent", "PATH": sandbox_path(), "LANG": "C.UTF-8",
           "TERM": "dumb", "ANTHROPIC_API_KEY": key}
    if os.environ.get("ANTHROPIC_BASE_URL"):
        env["ANTHROPIC_BASE_URL"] = os.environ["ANTHROPIC_BASE_URL"]
    (home / ".claude").mkdir(exist_ok=True)
    if binary.suffix == ".js":  # an npm install: cli.js run by node
        tools = {"bin/node": _which("node"), "claude": binary.parent}
        exe = [f"{TOOLS_AT}/bin/node", f"{TOOLS_AT}/claude/{binary.name}"]
    else:  # the native binary
        tools = {"bin/claude": binary}
        exe = [f"{TOOLS_AT}/bin/claude"]
    argv = bwrap_argv(project, home, tools, env) + exe + [
        "--print", *(["--continue"] if resume else []),
        "--output-format", "stream-json", "--verbose",
        "--safe-mode", "--disable-slash-commands", "--strict-mcp-config",
        "--model", model,
        "--allowed-tools", "Read,Grep,Glob",
        "--disallowed-tools", "Bash,Write,Edit,NotebookEdit,WebSearch,WebFetch,Task",
        "--effort", effort,
    ]
    return argv, None


def claude_reply(stdout: str) -> tuple:
    """The final answer and the number of tool calls, from stream-json."""
    text, calls = "", 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            text = event["result"].strip()
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                calls += 1
    return text or stdout.strip(), calls


# codex prints its transcript on stderr; a tool call is a line holding just its name.
CODEX_CALL = re.compile(r"^(exec|apply_patch|web_search|tool)\s*$", re.M)


def codex_command(project, home, model, effort, resume):
    codex_js = _which("codex")
    package = codex_js.parent.parent  # .../@openai/codex/bin/codex.js
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("set OPENAI_API_KEY")
    codex_home = home / ".codex"
    codex_home.mkdir(exist_ok=True)
    skills = codex_home / "skills"  # codex installs its own skills unless it cannot
    skills.mkdir(exist_ok=True)
    skills.chmod(0o500)
    lines = [f"model = {_toml(model)}", 'approval_policy = "never"',
             'sandbox_mode = "danger-full-access"', "hide_full_access_warning = true",
             "project_doc_max_bytes = 0", f"model_reasoning_effort = {_toml(effort)}"]
    if os.environ.get("OPENAI_BASE_URL"):
        lines.insert(1, 'model_provider = "scipivot"')
    lines += ["", "[tools]", "web_search = false"]
    if os.environ.get("OPENAI_BASE_URL"):
        lines += ["", "[model_providers.scipivot]", 'name = "scipivot"',
                  f"base_url = {_toml(os.environ['OPENAI_BASE_URL'])}",
                  'env_key = "OPENAI_API_KEY"', 'wire_api = "responses"']
    work = PROJECT_AT if project is not None else HOME_AT
    lines += ["", f"[projects.{_toml(work)}]", 'trust_level = "trusted"', ""]
    (codex_home / "config.toml").write_text("\n".join(lines), encoding="utf-8")
    env = {"HOME": HOME_AT, "USER": "agent", "PATH": sandbox_path(), "LANG": "C.UTF-8",
           "TERM": "dumb", "CODEX_HOME": f"{HOME_AT}/.codex", "OPENAI_API_KEY": key}
    tools = {"bin/node": _which("node"), "codex": package}
    argv = bwrap_argv(project, home, tools, env) + [
        f"{TOOLS_AT}/bin/node", f"{TOOLS_AT}/codex/bin/codex.js", "exec",
        *(["resume", "--last"] if resume else []),
        "--skip-git-repo-check", "--ignore-rules",
        "--output-last-message", f"{HOME_AT}/reply.txt", "-",
    ]
    return argv, home / "reply.txt"


ENGINES = {"claude": claude_command, "codex": codex_command}


def run_session(case, condition, order, args, project) -> list:
    """One fresh session: the question, then each reconsideration."""
    home = Path(tempfile.mkdtemp(prefix="scipivot-home-"))
    rows = []
    try:
        prompts = [make_prompt.render(case, condition, order)]
        prompts += [make_prompt.RECONSIDER.read_text(encoding="utf-8")] * args.reconsider
        for stage, prompt in enumerate(prompts):
            argv, reply_file = ENGINES[args.engine](project, home, args.model, args.effort, stage > 0)
            if reply_file is not None:
                reply_file.unlink(missing_ok=True)
            start = time.monotonic()
            try:
                done = subprocess.run(argv, input=prompt, capture_output=True, text=True,
                                      timeout=args.timeout)
                out, err, code = done.stdout, done.stderr, done.returncode
            except subprocess.TimeoutExpired as exc:
                out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                err, code = f"timed out after {args.timeout}s", -1
            seconds = round(time.monotonic() - start, 1)
            if reply_file is not None:
                text = reply_file.read_text(encoding="utf-8").strip() if reply_file.exists() else ""
                calls = len(CODEX_CALL.findall(err))
            else:
                text, calls = claude_reply(out)
            transcript = args.transcripts / f"{case['id']}_{condition}_{order}_stage{stage}.log"
            transcript.write_text(f"===== stdout\n{out}\n===== stderr\n{err}\n", encoding="utf-8")
            rows.append({"id": case["id"], "order": order, "condition": condition, "stage": stage,
                         "engine": args.engine, "model": args.model, "effort": args.effort,
                         "response": text, "exit_code": code, "seconds": seconds,
                         "tool_calls": calls, "transcript": str(transcript),
                         **({"stderr_tail": err[-2000:]} if code != 0 else {})})
            if code != 0:
                break
    finally:
        skills = home / ".codex" / "skills"
        if skills.is_dir():
            skills.chmod(0o700)
        shutil.rmtree(home, ignore_errors=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", action="append", help="case id (repeatable)")
    ap.add_argument("--all", action="store_true", help="every case")
    ap.add_argument("--condition", default="project", choices=["project", "options-only"],
                    help="project mounts the case's record at /project; options-only mounts nothing")
    ap.add_argument("--order", default="both", choices=["ab", "ba", "both"],
                    help="option order; both (default) runs ab and ba, as the paper scores them")
    ap.add_argument("--engine", required=True, choices=sorted(ENGINES),
                    help="claude (Claude Code) or codex (Codex CLI)")
    ap.add_argument("--model", required=True, help="model name as your endpoint knows it")
    ap.add_argument("--effort", default="medium", choices=EFFORTS,
                    help="reasoning effort (default: medium, as in the paper's main table)")
    ap.add_argument("--reconsider", type=int, default=0, choices=[0, 1, 2],
                    help="continue each session this many times with the reconsideration prompt")
    ap.add_argument("--records", default="records", help="where fetch_records.py unpacks snapshots")
    ap.add_argument("--fetch", action="store_true", help="download missing snapshots first")
    ap.add_argument("--out", required=True,
                    help="JSON lines file, one per condition, engine, model and effort. Running "
                         "again resumes: finished sessions are kept and skipped, failed or "
                         "unfinished ones are dropped from the file and run again")
    ap.add_argument("--transcripts", type=Path,
                    help="where each session's full output is kept (default: <out>.transcripts/)")
    ap.add_argument("--jobs", type=int, default=2, help="sessions run at once (default: 2)")
    ap.add_argument("--timeout", type=int, default=TIMEOUT,
                    help=f"seconds per answer (default: {TIMEOUT})")
    args = ap.parse_args()

    cases = json.loads(make_prompt.QUESTIONS.read_text(encoding="utf-8"))
    if args.all:
        selected = cases
    elif args.id:
        selected = [c for c in cases if c["id"] in set(args.id)]
        if len(selected) != len(set(args.id)):
            raise SystemExit("unknown case id")
    else:
        ap.error("give --id CASE or --all")
    orders = ["ab", "ba"] if args.order == "both" else [args.order]
    manifest = fetch_records.load_manifest()
    records = Path(args.records)

    checked = {}

    def project_of(case):
        if args.condition != "project":
            return None
        row = manifest[case["snapshot"]]
        target = fetch_records.target_of(row, records)
        if target in checked:
            return target
        if not target.is_dir() and not args.fetch:
            raise SystemExit(f"{case['id']}: {target} is missing; run fetch_records.py "
                             f"--id {case['id']} --out {records}, or pass --fetch")
        try:  # an existing tree is checked against the manifest before it is used
            fetch_records.restore(row, records)
        except fetch_records.RecordError as exc:
            raise SystemExit(str(exc)) from None
        checked[target] = True
        return target

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Resume: a session is finished when every stage it asks for answered with exit 0.
    setting = (args.condition, args.engine, args.model, args.effort)
    old = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()
           if line.strip()] if out.exists() else []
    sessions = {}
    for row in old:
        if (row.get("condition"), row.get("engine"), row.get("model"), row.get("effort")) != setting:
            raise SystemExit(f"{out} holds runs of another condition, engine, model or effort; "
                             f"use a separate --out file")
        sessions.setdefault((row["id"], row["order"]), []).append(row)
    finished = {key for key, rows in sessions.items()
                if sorted(r["stage"] for r in rows if r.get("exit_code") == 0)
                == list(range(args.reconsider + 1))}
    kept = [row for row in old if (row["id"], row["order"]) in finished]
    if len(kept) != len(old):
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept),
                       encoding="utf-8")
        print(f"dropped {len(old) - len(kept)} answers of failed or unfinished sessions", flush=True)
    todo = [(c, o) for c in selected for o in orders if (c["id"], o) not in finished]
    if len(todo) < len(selected) * len(orders):
        print(f"{len(selected) * len(orders) - len(todo)} sessions already finished in {out}",
              flush=True)
    jobs = [(case, order, project_of(case)) for case, order in todo]
    args.transcripts = args.transcripts or out.with_name(out.name + ".transcripts")
    args.transcripts.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.jobs) as pool, out.open("a", encoding="utf-8") as handle:
        futures = [pool.submit(run_session, c, args.condition, o, args, p) for c, o, p in jobs]
        for future in futures:
            for row in future.result():
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                print(f"{row['id']} {row['order']} stage {row['stage']}: exit {row['exit_code']}, "
                      f"{row['seconds']}s, {score.parse_choice(row['response']) or '(no choice)'}",
                      flush=True)


if __name__ == "__main__":
    main()
