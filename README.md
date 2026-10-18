# SciPIvot

<p align="center">
  <strong>Knowing what to try next.</strong><br>
  A benchmark for the scientific judgment of AI research agents.
</p>
<p align="center">
  <a href="https://autoresearch-factory.github.io/SciPIvot/"><img src="https://img.shields.io/badge/landing-page-004488?style=for-the-badge" alt="Landing page"></a>
  <a href="https://arxiv.org/abs/2610.21082"><img src="https://img.shields.io/badge/arXiv-2610.21082-b31b1b?style=for-the-badge" alt="arXiv"></a>
  <a href="https://huggingface.co/datasets/sun1245/SciPIvot"><img src="https://img.shields.io/badge/project%20records-Hugging%20Face-ffcc4d?style=for-the-badge" alt="Project records on Hugging Face"></a>
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/data"><img src="https://img.shields.io/badge/questions-248%20cases-a67c13?style=for-the-badge" alt="248 cases"></a>
  <img src="https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey?style=for-the-badge" alt="CC BY 4.0">
</p>
<p align="center">
  &#128279; <a href="https://autoresearch-factory.github.io/SciPIvot/">Landing page</a> &#183;
  <a href="https://arxiv.org/abs/2610.21082">Paper</a> &#183;
  <a href="https://huggingface.co/datasets/sun1245/SciPIvot">Project records</a> &#183;
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/data">Question set</a> &#183;
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/prompts">Prompts</a> &#183;
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/results">Results</a>
</p>


**Benchmarking Principal-Investigator Judgment at Pivotal Moments of Scientific AutoResearch Agents**

SciPIvot is a 248-case benchmark of **scientific judgment** built from human corrections in six months of real frontier research: senior researchers ran LLM agents on 26 PhD-level projects across six scientific fields and repeatedly intervened to correct the agents' research judgments. Each case asks an evaluator to choose between the **original LLM plan** and the **human-corrected alternative**, using only the project record that existed before the correction.

> Frontier models systematically prefer the original LLM plan over the human-corrected one. At medium reasoning effort with the project record, four of five frontier models score below chance on the selected cases. The best score across tested models and effort settings is **63.5%**, against **73.4%** for fresh researchers.

Paper: *SciPIvot: Benchmarking Principal-Investigator Judgment at Pivotal Moments of Scientific AutoResearch Agents* ([arXiv:2610.21082](https://arxiv.org/abs/2610.21082)).

## What is in this repository

| Path | Contents |
|------|----------|
| `data/questions.json` | The complete 248-case question set: case id, both options in exact wording, reference answer, and `snapshot`, the project record it is asked against |
| `data/snapshots.jsonl` | The 230 project records: archive and unpacked-tree checksums, sizes, file counts |
| `data/questions.txt` | Same set in plain text |
| `prompts/` | Exact evaluation prompts (project / options-only / reconsideration) and the case-writing prompt |
| `results/` | Aggregate model results for all twelve evaluation conditions |
| `scripts/make_prompt.py` | Render the evaluation prompt for any case, in either option order |
| `scripts/score.py` | Score model responses against reference answers |
| `scripts/fetch_records.py` | Download, check and unpack the project records from Hugging Face |
| `scripts/run_project.py` | Run cases with Claude Code or Codex in a sandbox, as in the paper |

## The task

A case presents two candidate next-step plans for a research project at a frozen state:

- one plan is the **original LLM plan** actually proposed by the research agent (the *rejected* plan),
- the other is the **human-corrected plan**, reconstructed from the senior researcher's intervention and the project's subsequent investigation (the *reference* plan).

The evaluator reads both plans and chooses which better advances the scientific question. **Choosing the reference plan counts as correct.** In the *project* condition the evaluator additionally receives the project record as it stood before the intervention (code, experimental logs, progress notes); in the *options-only* condition it sees only the two plans.

Each case is evaluated in two sessions with the option order reversed; correctness is averaged over the two orders, then cases are weighted equally. Chance accuracy is 50%.

## Quickstart

```bash
# 1. Render a prompt for one case (order ab puts options.A in slot A)
python scripts/make_prompt.py --id case_000 --condition project --order ab

# 2. Ask your model. It should answer with JSON:
#    {"argument": "The reason for your choice", "response": "A or B"}

# 3. Score the responses
python scripts/score.py predictions.json
```

`predictions.json` (or `.jsonl`) contains one object per run:

```json
{"id": "case_000", "order": "ab", "response": "B"}
```

### The project condition

The *project* condition needs the project record each case was asked against. The records are on [Hugging Face](https://huggingface.co/datasets/sun1245/SciPIvot): accept the terms there once (name and affiliation; access is immediate), then

```bash
# Python 3.12+
python3 -m venv .venv && . .venv/bin/activate
pip install huggingface_hub zstandard
hf auth login                      # or export HF_TOKEN=hf_...

# Download, check and unpack the records for some cases
python scripts/fetch_records.py --id case_000 --id case_001 --out records

# Check that every record restores, keeping only a few GB on disk at a time
python scripts/fetch_records.py --all --out records --remove-after-verify

# Run them as in the paper: both option orders, one fresh session each
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY for --engine codex
python scripts/run_project.py --id case_000 --id case_001 --condition project \
    --engine claude --model claude-opus-5 --effort medium --records records --out runs/opus.jsonl
python scripts/score.py runs/opus.jsonl
```

Unpacking all 230 records takes 91 GB, and the 21 GB of archives stay in the Hugging Face cache (`~/.cache/huggingface`) unless `--remove-after-verify` is given. Each archive is checked against its `sha256` and each unpacked tree against its `tree_sha256`; a tree already in `--out` is checked again rather than trusted, and `--remove-after-verify` keeps it.

`run_project.py` needs Linux with [bubblewrap](https://github.com/containers/bubblewrap) (`apt install bubblewrap`) and the agent's CLI (`claude` or `codex`) on `PATH`. Each session sees the record read-only at `/project`, an empty scratch HOME, and the system; not your home directory, your agent settings, or any other record. The agents are configured exactly as in the paper. Claude Code runs with `--print --safe-mode --disable-slash-commands --strict-mcp-config`, pre-approves Read, Grep and Glob, and denies Bash, Write, Edit, NotebookEdit, WebSearch, WebFetch and Task; other tools that need permission are refused in `--print` mode. Codex runs `exec` with `approval_policy = "never"` and `sandbox_mode = "danger-full-access"` inside the bubblewrap sandbox, with no `AGENTS.md` (`project_doc_max_bytes = 0`), `--ignore-rules`, web search off, and its built-in skills blocked (hence a harmless `failed to install system skills` line in its log). The network stays up because the agent must reach its API; the prompt tells it not to use it otherwise. `--condition options-only` mounts nothing. `--reconsider 2` continues each session twice with the reconsideration prompt; score a stage with `score.py --stage 1` or `--stage 2`. Write each condition, engine, model and effort to its own `--out` file; `score.py` refuses a file that mixes them. Running the same command again resumes: finished sessions are skipped, and failed ones are dropped from the file and run again. Every session's full output is kept beside it in `<out>.transcripts/`, and each answer records `tool_calls`, so a run that never opened the project is visible.

`response` may also be the raw model output containing a JSON object with a `response` field; unparsed outputs are scored as incorrect. With both option orders present per case, `score.py` reproduces the paper's main score (orders averaged within case, then cases equally weighted). Add `--ci` for the paper's 95% case-bootstrap intervals (10,000 resamples, seed 20261004).

## Evaluation protocol

- **Conditions.** Two base conditions, *project* and *options-only*, each at requested effort settings low / medium / high / xhigh / max, plus two reconsideration stages that continue the medium-effort project session without correctness feedback (12 conditions in total).
- **Option orders.** Every condition runs in both orders (`ab`, `ba`).
- **Scoring.** Exact choice matching. A completed response without a parseable choice counts as incorrect.
- **Prompts.** `prompts/BENCH_ASK_PROMPT.md` holds the exact evaluation instructions (sections `project` and `blind` = options-only); `prompts/BENCH_RECONSIDER_PROMPT.md` is the reconsideration prompt; `prompts/BREAKPOINT_CASE_PROMPT.md` is the case-writing prompt used during construction.

## Headline results

Accuracy (%) on all 248 cases, averaged over both option orders. *Project* and *Options only* use medium effort; *Best project* is the highest score among seven conditions (five effort settings and two reviews at medium effort).

| Model | Project | Options only | Best project | Setting |
|-------|---------|--------------|--------------|---------|
| GPT-6 Astra | 59.5 | 63.7 | 63.5 | xhigh |
| Claude Opus 5 | 38.9 | 58.9 | 46.8 | max |
| Grok 4.6 | 33.1 | 54.0 | 38.1 | high |
| GPT-5.6 Sol | 35.1 | 46.8 | 37.7 | medium, after review 2 |
| GPT-5.6 Terra | 29.2 | 55.8 | 52.0 | medium, after review 1 |
| Human baseline | 73.4 | — | — | agent assistant available |

Full tables with 95% intervals, per-condition scores, and reconsideration transitions are in `results/`.

## Data schema

```json
{
  "id": "case_000",
  "options": {"A": "Goal: ... Plan: ...", "B": "Goal: ... Plan: ..."},
  "reference_answer": "B",
  "snapshot": "snapshots/<project>/<commit>.tar.zst"
}
```

Case ids are anonymized. Options follow the same English `Goal:` / `Plan:` format on both sides. Reference answers name the human-corrected plan.

## Project records

The 230 project records behind the 248 cases are in the Hugging Face dataset [sun1245/SciPIvot](https://huggingface.co/datasets/sun1245/SciPIvot), one `.tar.zst` per commit (21 GB in all). A record is the project's git tree at the case's commit, without `.git`: no history, and nothing written after the correction. It is exactly what the models in the paper saw at `/project`. Links that point outside the project were not mounted then and are not in the archive; `data/snapshots.jsonl` lists them under `skipped`. `fetch_records.py` checks each archive's `sha256` and each unpacked tree's `tree_sha256` against that file.

## Release hygiene

The question set and prompts are scrubbed before release: personal identifiers and account information were removed during the question export (anonymized case ids, with identifier substitutions in 19 cases), and internal system names, workspace names, and internal tool paths in the prompts were genericized (see `prompts/README.md` and `prompts/sources.json`, which preserve digests of the byte-exact internal originals where the released copies differ).

## Citation

```bibtex
@misc{scipivot2026,
  title         = {{SciPIvot}: Benchmarking Principal-Investigator Judgment at Pivotal Moments of Scientific AutoResearch Agents},
  author        = {Sun, Youran and Ren, Xingyu and Yi, Chugang and Zhang, Kejia and Wu, Di and Cao, Yingkang and Zhou, Allen and Ye, Jianping and Liu, Suying and Guo, Jiaxuan and Du, Jianda and Ye, Weicheng and Liu, Kecheng and Zhang, Hefan and Wang, Haixin and Xiao, Jie and Yang, Eric and Yang, Haizhao},
  year          = {2026},
  eprint        = {2610.21082},
  archivePrefix = {arXiv},
  url           = {https://arxiv.org/abs/2610.21082}
}
```

## License

Released under the [Creative Commons Attribution 4.0 International](LICENSE) license (research and training use permitted with attribution).

## Contact

Corresponding authors: Eric Yang (`ey@gradientdata.ai`), Haizhao Yang (`hzyang@umd.edu`).
