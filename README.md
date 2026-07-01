# wingit

Run your agent harness in headless mode.

wingit (aliased to `a`) is a thin, pipeable CLI that sends a prompt to an agent
**harness** — Claude Code, Copilot, Codex, Opencode, Pi — running in headless mode and
returns its answer. It wraps existing harnesses rather than calling model APIs, so you
get their full agentic capability behind one uniform, Unix-friendly front-end, with
harness/model switching and named sessions on top.

```console
$ a "count the number of words in the current diff"   # one-off; the harness does the work
$ git diff | a "count the words"                       # pipe data in, get the answer out
$ a -m h "quick sanity check on this regex: ..."       # switch model via an alias
$ a --harness copilot "explain this stack trace"       # switch harness
$ a -s refactor "start refactoring the auth module"    # create/resume a named session
```

The **answer** goes to stdout as plain text so `a` composes cleanly in pipes; reasoning
and progress go to stderr. Prompts are one-offs by default; opt into a named session with
`-s` to selectively carry memory across turns.

> Status: early. See [issue #1](https://github.com/gahjelle/wingit/issues/1) for the MVP
> vision, `CONTEXT.md` for the vocabulary, and `docs/adr/` for the architecture decisions.
