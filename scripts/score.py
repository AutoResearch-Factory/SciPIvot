#!/usr/bin/env python3
"""Score SciPIvot responses against reference answers.

Input: a .json or .jsonl predictions file with one object per run:
    {"id": "case_000", "order": "ab", "response": "B"}
"response" may be the bare choice ("A"/"B") or raw model output containing
a JSON object with a "response" field. Unparsed outputs score as incorrect.

Orders are averaged within each case, then cases are weighted equally
(the paper's main score). Use --ci for 95% case-bootstrap intervals
(10,000 resamples, seed 20261004).

Example:
    python scripts/score.py predictions.json --ci
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "questions.json"
SEED = 20261004


def load_predictions(path: Path) -> list:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    return data if isinstance(data, list) else [data]


def parse_choice(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if s in ("A", "B"):
        return s
    # Pull "response": "A" out of a raw model output.
    m = re.search(r'"response"\s*:\s*"?(A|B)"?(?![A-Za-z])', s)
    return m.group(1) if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("predictions", help=".json or .jsonl predictions file")
    ap.add_argument("--questions", default=str(QUESTIONS))
    ap.add_argument("--stage", type=int, default=0,
                    help="for run_project.py output: 0 = first answer, 1 and 2 = "
                         "after one and two reconsiderations (rows without a stage always count)")
    ap.add_argument("--ci", action="store_true",
                    help="95%% case-bootstrap interval (paper settings)")
    args = ap.parse_args()

    refs = {c["id"]: c["reference_answer"]
            for c in json.loads(Path(args.questions).read_text(encoding="utf-8"))}
    preds = load_predictions(Path(args.predictions))

    # per case -> per order -> correctness
    per_case: dict = {}
    unparsed = 0
    unknown_ids = 0
    settings = {tuple(row.get(k) for k in ("condition", "engine", "model", "effort"))
                for row in preds if row.get("stage", args.stage) == args.stage}
    if len(settings) > 1:
        sys.exit("the file mixes runs of different condition/engine/model/effort: "
                 + "; ".join(str(s) for s in sorted(settings, key=str)) + ". Score one per file.")
    for row in preds:
        case_id = row.get("id")
        if case_id not in refs:
            unknown_ids += 1
            continue
        if row.get("stage", args.stage) != args.stage:
            continue
        order = str(row.get("order", "ab")).lower()
        choice = parse_choice(row.get("response", row.get("choice")))
        if choice is None:
            unparsed += 1
            choice_correct = 0.0  # unparsed counts as incorrect
        else:
            ref = refs[case_id]
            if order == "ba":
                ref = "B" if ref == "A" else "A"
            elif order != "ab":
                sys.exit(f"unknown order {order!r} for {case_id}")
            choice_correct = float(choice == ref)
        if order in per_case.get(case_id, {}):
            sys.exit(f"two answers for {case_id} order {order}: score one condition, "
                     f"model and effort per file")
        per_case.setdefault(case_id, {})[order] = choice_correct

    if not per_case:
        sys.exit("no scorable predictions found")

    # average orders within case, then cases equally
    case_scores = {cid: sum(v.values()) / len(v) for cid, v in per_case.items()}
    scores = list(case_scores.values())
    acc = sum(scores) / len(scores)

    print(f"cases scored      : {len(scores)} / {len(refs)}")
    print(f"runs scored       : {sum(len(v) for v in per_case.values())}")
    print(f"unparsed runs     : {unparsed} (scored as incorrect)")
    if unknown_ids:
        print(f"unknown ids skipped: {unknown_ids}")
    print(f"accuracy          : {acc * 100:.1f}%")
    one_order = sum(len(v) == 1 for v in per_case.values())
    if one_order:
        print(f"warning           : {one_order} case(s) have only one option order; "
              f"the paper's score averages both")

    if args.ci:
        rng = random.Random(SEED)
        boots = []
        n = len(scores)
        for _ in range(10000):
            draw = [scores[rng.randrange(n)] for _ in range(n)]
            boots.append(sum(draw) / n)
        boots.sort()
        lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]
        print(f"95% case-bootstrap: [{lo * 100:.1f}, {hi * 100:.1f}]")


if __name__ == "__main__":
    main()
