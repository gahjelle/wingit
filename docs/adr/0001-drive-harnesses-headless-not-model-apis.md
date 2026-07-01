# Drive harnesses in headless mode; don't call model APIs

wingit dispatches prompts by shelling out to an agent harness's own non-interactive
mode (Claude Code `-p`, Codex `exec`, etc.) rather than calling model APIs directly.
This gives us the harness's full agentic capability — tools, file edits, model access —
for free, at the cost of giving up fine control over output format (which we reclaim by
driving harnesses in structured mode internally and rendering plain text ourselves).

## Considered Options

- **Shell out to harnesses' headless mode** (chosen).
- **Call model APIs directly** — rejected: makes wingit a raw-LLM CLI and forces us to
  reimplement agent loops the harnesses already provide, losing tool use for prompts
  like `a "count the words in the current diff"`.
