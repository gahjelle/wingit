# wingit

A thin, pipeable CLI (`a`) that dispatches a prompt to an agent harness running in
headless mode and returns the harness's answer. Wraps existing harnesses rather than
talking to model APIs directly, because the user's harness is already logged in
([ADR-0013](docs/adr/0013-wrap-harnesses-because-they-are-already-logged-in.md)); adds a
uniform front-end, harness and model switching, a tool-posture ladder, and a one-flag
follow-up on top.

`a` does two jobs: **transform** (text in a pipe) and **ask** (questions about the
working directory, using the harness's own tools).

This glossary is the project's ubiquitous language. Prefer these words in code, tests,
issues and docs; the `_Avoid_` lines are the synonyms that cause drift.

## Language

**Harness**:
The underlying coding-agent CLI that wingit drives in headless mode. Five are supported as
peers: Claude Code, Copilot CLI, Opencode, Codex, Pi. wingit shells out to it and adapts
to it; the harness supplies the actual agentic capability (tools, file edits, model
access). wingit detects a harness on `PATH` and **never touches its auth**.
_Avoid_: backend, provider, engine, model

**Driver**:
wingit's adapter for one harness, implementing the seam's three methods — `argv`, `feed`,
`finish` — and **declaring** that harness's capabilities. All harness-specific divergence
lives inside a driver; the core has no per-harness special cases
([ADR-0005](docs/adr/0005-capability-negotiating-harness-seam.md)).
_Avoid_: adapter, plugin, backend, wrapper

**Run**:
A single `a` invocation: one prompt in, one answer out, one harness process spawned. The
unit everything else is scoped to.
_Avoid_: call, request, query, invocation

**Follow-up**:
Continuing the previous run in this repo, on this harness, via `-c`/`--continue`. The
whole of wingit's memory surface — there are no session names and nothing to manage
([ADR-0008](docs/adr/0008-follow-up-not-named-sessions.md)).
_Avoid_: continue-session, resume, thread, conversation

## The harness seam

**Capability**:
Something a harness can or cannot do, **declared statically by its driver** and negotiated
by the core rather than assumed uniform. Four are user-visible: streams, shows reasoning,
supports `--tools none`, can run without storing a session.
_Avoid_: feature, support, ability, flag

**Degrade**:
What wingit does when a **fidelity** gap means a harness cannot deliver something the user
asked for: do the next-best thing and say so with a notice. The worst case is a less
pleasant answer.
_Avoid_: fall back, downgrade, skip, ignore

**Refuse**:
What wingit does when a **safety** gap means a harness cannot honour something the user
asked for: error out rather than proceed. Degrading here would do precisely the thing the
user opted out of. The MVP's only live refuse trigger is `store_sessions = false` on
Opencode and Copilot.
_Avoid_: reject, abort, fail, block

**Notice**:
A short stderr message explaining that wingit could not deliver something. Fires **only
when the user asked for something this run** that wingit could not deliver — and config
counts as asking ([ADR-0012](docs/adr/0012-capability-disclosure-is-pull-first.md)).
Never fires to report an unchanging fact.
_Avoid_: warning, log, message, error

## Output contract

**Answer**:
The core result of a prompt — final model prose — written to **stdout** as plain text so
`a` composes cleanly in pipes. Whether it is streamed is a per-harness **capability**, not
a promise: Copilot and Pi stream, Claude Code will not (its stream can diverge from its own
result), Opencode and Codex cannot.
_Avoid_: result, response, output

**Reasoning**:
Explanatory or intermediate output (the harness's thinking, progress, tool chatter), routed
to **stderr** to keep stdout carrying only the answer. **Best-effort**: where a harness does
not separate it, this degrades to silence rather than polluting stdout.
_Avoid_: logs, thoughts, trace

**Data block**:
The delimited wrapper around piped stdin when a prompt argument is also given, marking
where the instruction ends and the data begins. An anti-injection **hint**, explicitly
**not** a boundary — never describe or rely on it as a security control.
_Avoid_: fence, delimiter, guard, sandbox

## Safety posture

**Rung**:
One of the three levels of the **tool ladder** — `none` (no tools), `read` (read tools, no
shell, no network), `write` (all tools approved). The default is `write` on **every**
invocation: piped, TTY, script and CI alike. Rungs govern *reach*, not just the filesystem
([ADR-0006](docs/adr/0006-tool-posture-ladder.md)).
_Avoid_: level, mode, permission, policy, sandbox

**Inherited environment**:
The harness's own project context — instruction files, MCP servers, skills, agents, **and
hooks** — which `a` picks up whole and unconditionally. There is no hermetic mode and no
suppression flag. Because hooks are not tools, rung `none` does not mean "nothing can
happen", and since `-p` skips the workspace trust dialog **`a` is strictly more permissive
than the harness it wraps**
([ADR-0011](docs/adr/0011-project-environment-inherited-whole.md)).
_Avoid_: context, project config, workspace, sandbox

## Configuration and memory

**Detected harness**:
The harness wingit picked on first run by **ranked** detection — Claude Code > Pi >
Opencode > Copilot > Codex, highest-ranked on `PATH` wins. Detection is never interactive
and the choice is **frozen** once written; changing it is an explicit repair, not a silent
re-detection ([ADR-0007](docs/adr/0007-self-materializing-config-defaults-in-code.md)).
_Avoid_: default harness, active harness, selected harness

**Model alias**:
A short, per-harness name for a model, selected with `-m` (e.g. `-m h` → latest Haiku under
Claude Code). The alias table lives as a **pydantic field default** in wingit's source —
config files hold only true choices, never the table. The same alias can resolve to
different models depending on the active harness.
_Avoid_: shortcut, model name, tag

**Session**:
A harness-native conversation. wingit does **not** expose sessions: there are no session
names, no `-s`, no listing, and no user-facing session identity. A session is bound to the
harness that created it. wingit **names** the sessions it creates so its entries stay
identifiable in the user's own harness history.
_Avoid_: conversation, thread, context, chat

**Pointer cache**:
The bounded LRU store mapping **(repo root, harness)** to the harness-native session id
read back from the last run. It is a *cache*, not a registry — entries age out, so nothing
needs managing, and a miss simply starts a fresh session with a notice.
_Avoid_: registry, database, index, session store
