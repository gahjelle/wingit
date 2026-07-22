# wingit

Run your agent harness in headless mode.

wingit (aliased to `a`) is a thin, pipeable CLI that sends a prompt to an agent
**harness** — Claude Code, Copilot, Codex, Opencode, Pi — running in headless mode and
returns its answer. It wraps existing harnesses rather than calling model APIs, so it
needs no API key of its own: your harness is already installed and already logged in.

`a` does two jobs — **transform** (text in a pipe) and **ask** (questions about the
working directory, using the harness's own tools).

```console
$ a "how many Python files are in this directory?"    # ask; the harness does the work
$ git diff | a "count the words"                       # pipe data in, get the answer out
$ cat error.log | a                                    # stdin can be the whole prompt
$ a -m h "quick sanity check on this regex: ..."       # switch model via an alias
$ a -cp "explain this stack trace"                     # switch harness (Copilot)
$ a -c "and how do I fix it?"                          # follow up on the previous run
$ a -r "summarise this repo"                           # read-only tools for this run
```

The **answer** goes to stdout as plain text so `a` composes cleanly in pipes; reasoning
and progress go to stderr, best-effort. Every run is independent unless you pass `-c`,
which continues the previous run in this repo on the same harness.

> **Status: pre-release — not yet installable.** The CLI is being built as a sequence of
> tracer bullets tracked in [Epic: MVP](https://github.com/gahjelle/wingit/issues/34); the
> design behind it was settled in [the replan map](https://github.com/gahjelle/wingit/issues/8).
> Installation instructions and full documentation land with the last few slices.
> Meanwhile: `CONTEXT.md` for the vocabulary, `docs/adr/` for the architecture decisions.
