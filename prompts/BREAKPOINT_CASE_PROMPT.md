# SciPIvot Case-Writing Task

You are a case writer. Given a JSON object with breakpoint information, investigate the actual research run and the target research repo, and reconstruct zero or one SciPIvot benchmark case from it. You are responsible for selecting the target commit and writing the five supervision fields for this case.

## What this benchmark question is

The model being evaluated will see:

1. The state of the target research repo at a particular Git commit;
2. The fixed question: **Please list the next experiment step.**

The model being evaluated must answer this fixed question. You are to produce the historical supervision information for this question: identify from the evidence the wrong experiment plan that the research system gave at the time, then distill the human correction and the research system's subsequent research understanding into a correct experiment plan for the same state. Your output is a case record, not a plan for a researcher to execute, nor a standalone answer to the fixed question.

The meanings of the five output fields:

- `commit`: The state of the target repo before the wrong plan appeared. The wrong plan has not yet appeared at this commit, but the next step is already close to formulating it.
- `wrong`: The wrong experiment plan that the research system actually proposed when answering the fixed question from this state.
- `wrong_reason`: Why this plan does not fit the research objectives or experimental logic.
- `correct`: A correct experiment plan for the same commit state and the same fixed question, distilled from the human correction and the research system's subsequent research understanding.
- `correct_reason`: Why this plan is correct, and how it resolves the problems in `wrong`.

## Fields in the input JSON

`<BREAKPOINT_INFO>` is a JSON object containing only the necessary location information and limited evidence. Each breakpoint member's location information and its corresponding evidence are placed in the same object.

```json
{
  "project": {
    "slug": "Name of the target research repo",
    "repo_path": "Local path of the target repo",
    "remote_url": "Remote URL of the target repo"
  },
  "aggregate": {
    "start": "YYYYMMDD-HHMM",
    "end": "YYYYMMDD-HHMM",
    "breakpoints": [
      {
        "signal": "session-talk",
        "time": "YYYYMMDD-HHMM",
        "session_id": "Session ID",
        "log_path": "Path to the full session log",
        "human_turns": [
          {
            "time": "YYYYMMDD-HHMM",
            "text": "Selected verbatim text from the human"
          }
        ]
      },
      {
        "signal": "sec5-write",
        "time": "YYYYMMDD-HHMM",
        "commit": "40-character Git commit SHA",
        "added": "Example of added content",
        "removed": "Example of removed content"
      }
    ]
  }
}
```

Additional rules:

- Keep each member's location information together with its corresponding evidence; `session-talk` corresponds to the session conversation, and `sec5-write` corresponds to Git changes in `STATE.md` §5.
- When evidence has no readable or useful content, omit it; do not fill it with empty strings.
- When `added` and `removed` are present, they must be complete, untruncated, usable diffs; also omit content that consists only of template placeholders.

### Input JSON

<BREAKPOINT_INFO>

## Investigation and case criteria

Based on the input evidence and your own investigation, determine whether it supports a clear benchmark case. The case needs to include: the repo state before the wrong plan appeared, the wrong experiment plan the research system actually proposed, the human correction, and the research understanding the research system developed afterward.

`commit` must be a real commit in the target repo and must precede the wrong plan. Use subsequent execution results to understand the correction; `correct` must contain only the research plan that should have been formulated at the time, not an execution log.

The question is limited to research direction, experiment design, and experiment planning: research directions, hypotheses, priorities, datasets, splits, metrics, baselines, controls, ablations, evaluation protocols, evidence requirements, and plans for the next round of experiments. Scheduling, session management, resume, notifications, Git operations, coding, code bugs, dependencies, servers, GPUs, paths, permissions, synchronization, writing, and formatting do not by themselves constitute a question.

If the evidence is insufficient to reconstruct a clear pre-error state, the error cannot be matched to the correction, necessary Git evidence is unavailable, or a key state exists only in uncommitted files, output the not-a-case result below. Each case must select one research-planning decision that can be explained independently. If a breakpoint contains multiple errors, select the one with the clearest evidence and the clearest correction.

The research system's workflow is `topic → landscape summary → idea → proposal → experiment → paper/report`; the experiment pipeline uses the proposal to run experiments, baselines, and ablations, evaluate results, and plan subsequent work.

Git commit times may include a local time zone, while session log times are usually UTC; normalize them to the same time zone before comparing timelines. Do not directly compare bare times or compact timestamps.

The investigation may involve two repositories (the repository pointed to by project.repo_path and its enclosing workspace repository); case.commit must come from the repository pointed to by project.repo_path.

Session logs can be large. Do not read or output an entire log at once; first locate it using `log_path`, then filter by line or perform targeted searches for the relevant time range and messages to avoid output truncation.

Do not search for or read existing SciPIvot case results from past runs; investigate and write the case independently.

## Neutral wording for the two plans

`wrong` and `correct` will be shown verbatim as two answer options in random order to another agent or a human. Each must state an independent research plan only, without revealing which field corresponds to the wrong or the correct plan.
This template standardizes the wording only; it does not change the research content of either plan.

Use the following template:

```
Goal: [What this plan aims to do or the question it aims to answer]

Plan: [Describe the plan's experimental or analytical arrangements in order]
```

- Write all text fields in English.
- Use plain, everyday language and follow ASD-STE100.
- Use this order for both options. Write one sentence for each `Goal` and one paragraph for each `Plan`. Do not add other subheadings or filler just to satisfy a format or length. Keep the two options similar in length and detail level.
- Within the limited space, narrow the scope of the plan; do not compress the entire STATE. Use a few complete sentences in `Plan` to explain one concrete arrangement. Do not use semicolons, slashes, strings of nouns, or jargon to cram multiple lines of experimentation into one sentence.
- Use the same narrative perspective, tense, structure, and roughly the same level of detail in both fields. State only the plan itself, without evaluations, reasons, investigation findings, sources, or meta-commentary.
- Do not use or imply evaluative framing such as `wrong`, `correct`, `should`, `should not`, `deviation`, `waste`, `the true main line`, `honest`, or `solving the problem`, and do not use obviously positive or negative adjectives to describe either plan.
- `wrong` and `correct` must state only what will actually be done and any indispensable conditions. Omit conditions that are the same by default and items that are not planned. If deleting a passage does not affect the reader's understanding of the plan, delete it. Remove modifiers that suggest a plan is more economical, faster, more rigorous, more adequate, more reliable, more reasonable, or more valuable, as well as abstract words such as `freeze`, `lock`, `align`, `controlled`, `auditable`, and `repeatable` that do not specify concrete arrangements. If cost, speed, rigor, or similar factors are themselves explicit objects of study or control in the plan, you may state the specific budget, time limit, or protocol, but do not evaluate them.
- Do not use constructions such as `retain ... but change to ...`, `rather than ...`, `compared with ...`, or `therefore ...` to contrast one plan with the other plan or with a conclusion. Each plan should be stated independently; necessary experimental constraints within the plan may be retained, but express them in factual terms.
- Explanations of why a plan is correct or incorrect may appear only in `wrong_reason` and `correct_reason`.
- Although `correct` is reconstructed from subsequent evidence, it must still be written as a plan that could have been proposed at the time, not as a retrospective evaluation or a summary of results.
- Before writing the result, read only `wrong` and `correct` for a blind-reading check: a reader unfamiliar with the project must not be able to guess which option is the answer based only on tone, adjectives, length, structure, or formatting.
- Before writing the result, check that the two options are roughly similar in length. If one is clearly longer (you often make the correct one longer), first narrow its scope so that both options focus on the same question; do not make the original content denser by omitting normal sentence components or piling up technical terms.

### Example

In `Complete external baseline coverage at d=100 for 7 PDE families` vs `Determine the external baseline difficulty for 7 PDE families at a controlled cost`, "controlled cost" hints at the correct answer, so write `Determine the external baseline difficulty for 7 PDE families` instead.

## Output

The case result must be written to the specified result file. The file must contain only the following JSON object, without Markdown or any other text:

```json
{
  "case": {
    "commit": "Full 40-character Git SHA of the target project",
    "wrong": "the research system's wrong experiment plan",
    "wrong_reason": "Reason why it is wrong",
    "correct": "Correct experiment plan",
    "correct_reason": "Reason why it is correct"
  },
  "environment_difficulties": "Report the environmental difficulties actually encountered during the investigation"
}
```

If no case can be made, output the following not-a-case result:

```json
{
  "case": {
    "commit": null,
    "not_a_case_reason": "..."
  },
  "environment_difficulties": "Report the environmental difficulties actually encountered during the investigation"
}
```

If there are no environmental difficulties, set "environment_difficulties" to "".

The target repo and historical logs are read-only; do not check out, modify, commit, or push. Complete the investigation first and write the formal result to that file; do not put the formal result in the chat reply.
