# wingit

A thin, pipeable CLI (`a`) that dispatches a prompt to an agent harness running in
headless mode and returns the harness's output. Wraps existing harnesses rather than
talking to model APIs directly; adds a uniform front-end, model/harness switching, and
named sessions on top.

## Language

**Harness**:
The underlying coding-agent CLI that wingit drives in headless mode (e.g. Claude Code,
Codex, Copilot, Opencode, Pi). wingit shells out to it and normalizes its interface; the
harness supplies the actual agentic capability (tools, file edits, model access).
_Avoid_: backend, provider, engine, model

**One-off**:
A single stateless prompt → answer invocation with no memory. The default mode: every
`a "…"` is a one-off unless attached to a session.
_Avoid_: single-shot, oneshot, query

**Session**:
A named, resumable conversation with a harness. Opting into a session (`-s <name>`) is
how the user "selectively" turns on memory; the harness does the actual remembering. A
session is bound to the harness that created it and does not transfer between harnesses.
_Avoid_: conversation, thread, context, chat

**Session name**:
The short, memorable label the user assigns to a session (e.g. `1`, `refactor`). wingit
keeps a registry mapping each session name to the harness's native session identifier so
the user never has to type a UUID.
_Avoid_: alias, session id, handle

**Model alias**:
A short, per-harness name for a model, defined in config and selected with `-m` (e.g.
`-m h` → latest Haiku under Claude Code; `-m g` → GLM-5.2 under Opencode). The same alias
can resolve to different models depending on the active harness.
_Avoid_: shortcut, model name, tag

## Output contract

**Answer**:
The core result of a prompt, written to **stdout** as plain text so `a` composes cleanly
in pipes.
_Avoid_: result, response, output

**Reasoning**:
Explanatory or intermediate output (the harness's thinking, progress, tool chatter),
routed to **stderr** to keep stdout carrying only the answer.
_Avoid_: logs, thoughts, trace
