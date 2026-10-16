# SciPIvot

<p align="center">
  <strong>Knowing what to try next.</strong><br>
  A benchmark for the scientific judgment of AI research agents.
</p>
<p align="center">
  <a href="https://autoresearch-factory.github.io/SciPIvot/"><img src="https://img.shields.io/badge/landing-page-004488?style=for-the-badge" alt="Landing page"></a>
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/data"><img src="https://img.shields.io/badge/questions-248%20cases-a67c13?style=for-the-badge" alt="248 cases"></a>
  <img src="https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey?style=for-the-badge" alt="CC BY 4.0">
</p>
<p align="center">
  &#128279; <a href="https://autoresearch-factory.github.io/SciPIvot/">Landing page</a> &#183;
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/data">Question set</a> &#183;
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/prompts">Prompts</a> &#183;
  <a href="https://github.com/AutoResearch-Factory/SciPIvot/tree/main/results">Results</a>
</p>


**Benchmarking Principal-Investigator Judgment at Pivotal Moments of Scientific AutoResearch Agents**

SciPIvot is a 248-case benchmark of **scientific judgment** built from human corrections in six months of real frontier research: senior researchers ran LLM agents on 26 PhD-level projects across six scientific fields and repeatedly intervened to correct the agents' research judgments. Each case asks an evaluator to choose between the **original LLM plan** and the **human-corrected alternative**, using only the project record that existed before the correction.

> Frontier models systematically prefer the original LLM plan over the human-corrected one. At medium reasoning effort with the project record, four of five frontier models score below chance on the selected cases. The best score across tested models and effort settings is **63.5%**, against **73.4%** for fresh researchers.

Paper: *SciPIvot: Benchmarking Principal-Investigator Judgment at Pivotal Moments of Scientific AutoResearch Agents* (arXiv preprint coming soon).

## What is in this repository

| Path | Contents |
|------|----------|
| `data/questions.json` | The complete 248-case question set: case id, both options in exact wording, reference answer |
| `data/questions.txt` | Same set in plain text |
| `prompts/` | Exact evaluation prompts (project / options-only / reconsideration) and the case-writing prompt |
| `results/` | Aggregate model results for all twelve evaluation conditions |
| `scripts/make_prompt.py` | Render the evaluation prompt for any case, in either option order |
| `scripts/score.py` | Score model responses against reference answers |

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
  "reference_answer": "B"
}
```

Case ids are anonymized. Options follow the same English `Goal:` / `Plan:` format on both sides. Reference answers name the human-corrected plan.

## Project records

The frozen project records behind each case are too large for this repository and will be hosted separately. Everything needed to run the question-answering evaluation (questions, prompts, aggregate baselines) is here.

## Release hygiene

The question set and prompts are scrubbed before release: personal identifiers and account information were removed during the question export (anonymized case ids, with identifier substitutions in 19 cases), and internal system names, workspace names, and internal tool paths in the prompts were genericized (see `prompts/README.md` and `prompts/sources.json`, which preserve digests of the byte-exact internal originals where the released copies differ).

## Citation

```bibtex
@misc{scipivot2026,
  author = {{AutoResearch-Factory}},
  title = {{SciPIvot}: Benchmarking Principal-Investigator Judgment at Pivotal Moments of Scientific AutoResearch Agents},
  year = {2026},
  url = {https://github.com/AutoResearch-Factory/SciPIvot}
}
```

## License

Released under the [Creative Commons Attribution 4.0 International](LICENSE) license (research and training use permitted with attribution).

## Contact

Corresponding authors: Eric Yang (`ey@gradientdata.ai`), Haizhao Yang (`hzyang@umd.edu`).
