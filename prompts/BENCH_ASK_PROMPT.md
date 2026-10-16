# Question wording

`BREAKPOINT_CASE_PROMPT.md` creates the questions; this file asks them. The evaluation harness reads it, so changes take effect immediately.

`{a}` and `{b}` are the text of the two plans. In `project`, the project is mounted read-only at `/project`; in `blind`, nothing is mounted, and only the two plans are provided.

## project

`/project` is the current state of a research project. You need to think about what to do next.

Read idea.md first, then proposal.md, then STATE.md, and then other files if you think it is necessary.

Below are two candidate plans. Please choose the one you think is better.

<option_A>
(A) {a}
</option_A>

<option_B>
(B) {b}
</option_B>

Output format:

```
{
  "argument": "The reason for your choice",
  "response": "A or B"
}
```

Note:

- Only read the contents of `/project`. Do not go to parent directories. Do not access the network.

## blind

Below are two candidate next-step plans for a research project in a particular state. Please choose the one you think is better.

<option_A>
(A) {a}
</option_A>

<option_B>
(B) {b}
</option_B>

Output format:

```
{
  "argument": "The reason for your choice",
  "response": "A or B"
}
```
