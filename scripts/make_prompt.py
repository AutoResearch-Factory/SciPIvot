#!/usr/bin/env python3
"""Render SciPIvot evaluation prompts from questions.json.

Reads the canonical prompt templates from prompts/BENCH_ASK_PROMPT.md
(sections "project" and "blind") and substitutes the two option texts.

Example:
    python scripts/make_prompt.py --id case_000 --condition project --order ab
    python scripts/make_prompt.py --all --condition options-only --order ba > prompts_ba.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASK_TEMPLATE = ROOT / "prompts" / "BENCH_ASK_PROMPT.md"
RECONSIDER = ROOT / "prompts" / "BENCH_RECONSIDER_PROMPT.md"
QUESTIONS = ROOT / "data" / "questions.json"

CONDITIONS = {"project": "project", "options-only": "blind", "blind": "blind"}


def load_section(template_path: Path, section: str) -> str:
    """Return the body of '## <section>' up to the next '## ' heading."""
    text = template_path.read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(section)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit(f"section '{section}' not found in {template_path}")
    return m.group(1).strip() + "\n"


def render(case: dict, condition: str, order: str) -> str:
    template = load_section(ASK_TEMPLATE, CONDITIONS[condition])
    opt_a, opt_b = case["options"]["A"], case["options"]["B"]
    if order == "ba":
        opt_a, opt_b = opt_b, opt_a
    elif order != "ab":
        raise SystemExit(f"unknown order: {order}")
    return template.replace("{a}", opt_a).replace("{b}", opt_b)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id", help="case id, e.g. case_000")
    ap.add_argument("--all", action="store_true", help="render every case")
    ap.add_argument("--condition", default="project",
                    choices=sorted(CONDITIONS), help="evaluation condition")
    ap.add_argument("--order", default="ab", choices=["ab", "ba"],
                    help="option order; ba swaps the two texts")
    ap.add_argument("--reconsider", action="store_true",
                    help="print the reconsideration prompt instead")
    ap.add_argument("--questions", default=str(QUESTIONS))
    args = ap.parse_args()

    if args.reconsider:
        sys.stdout.write(RECONSIDER.read_text(encoding="utf-8"))
        return

    cases = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if args.all:
        selected = cases
    elif args.id:
        selected = [c for c in cases if c["id"] == args.id]
        if not selected:
            raise SystemExit(f"case not found: {args.id}")
    else:
        ap.error("give --id CASE or --all")

    for case in selected:
        print(f"===== {case['id']} (order {args.order}, {args.condition}) =====")
        print(render(case, args.condition, args.order))


if __name__ == "__main__":
    main()
