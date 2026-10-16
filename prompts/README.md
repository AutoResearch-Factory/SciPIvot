# Prompt snapshots and provenance

These are byte-for-byte copies of three generic prompts from the source benchmark repository:

- `BENCH_ASK_PROMPT.md`: the `project` and `blind` (options-only) question templates.
- `BENCH_RECONSIDER_PROMPT.md`: the follow-up used for the second and third answers.
- `BREAKPOINT_CASE_PROMPT.md`: instructions for constructing a case from a historical research record.

`sources.json` records SHA256, byte size, and content hashes, byte sizes, and verification scope for each copied file and for the files used to verify provenance.
All source paths are relative to the source repository root.
No accounts, credentials, retained sessions, or raw research conversations are included.

## Template extraction

The evaluation harness finds headings with the multiline regular expression `^##\s+(project|blind)\s*$`.
Each template is the text after its heading and before the next matching heading (or end of file), with `.strip("\n") + "\n"` applied.
`ask_sha256` hashes this UTF-8 template, not the full Markdown file.
The project template hash is `22613fc33bc22f626ba5918e7a5b667a7495f69de63b7b035002b55aa1b8b54a`; the blind template hash is `de9dddb5cdd01bee3474734b465fc184fd4dc5dad4aac911fc7b0d43e5d285b2`.
For repeat 0, `{a}` receives the rejected plan and `{b}` the corrected plan; repeat 1 reverses them.
The implementation strips each plan, substitutes `{a}` then `{b}` with `str.replace`, and hashes the rendered prompt as `prompt_sha256`.

## Matching prompts to evaluation records

Verification covered the logged questions at medium reasoning effort, matching exact case and option hashes and retaining the last log row per the report module's `latest_only` key (listed in `sources.json`).
All project runs and all options-only runs match both their current extracted template hash and the complete prompt reconstructed from the frozen options.
Each arm covers the released cases, two option orders, and five models.
All reconsideration and all third-answer runs also match the copied continuation prompt in both recorded hash fields.
These checks establish agreement with the logged digests; they do not independently recover full sessions, system messages, tool configuration, or historical code versions.

The copied case-construction prompt matches the `prompt_sha256` declared in the frozen case manifest.
The benchmark retains 248 questions from this pool with the same plans and prompts.
This is manifest-level agreement, not independent verification of every historical writer call or its adherence to the instructions.
