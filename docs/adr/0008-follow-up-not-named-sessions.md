# Memory is a follow-up to the last run, not a named session

wingit ships **one** memory affordance: a follow-up flag meaning *continue my last `a` run
here*. There are no session names, no `-s <name>`, and no name→identifier registry. The
follow-up resumes an explicit harness-native session id that wingit recorded after the
previous run, in a small bounded pointer store — a cache, not a registry.

Decided in [issue #17](https://github.com/gahjelle/wingit/issues/17). Supersedes
[ADR-0002](0002-sessions-build-on-native-harness-sessions.md) and closes the open question
in [ADR-0004](0004-xdg-state-pwd-scoping-deferred.md).

## Why the registry died

ADR-0002 assumed the job that
[issue #9](https://github.com/gahjelle/wingit/issues/9) later ruled out of scope: the
short-horizon task-doer, going away to do a piece of work with memory across invocations.
Named, managed conversations are worth their registry only for that job. The two jobs that
survived — *transform* (text in a pipe) and *ask* (questions about the cwd) — need
something much smaller. When an *ask* answer comes back slightly wrong, the user wants a
cheap "and also…", not a conversation they have to name first.

Dropping memory entirely was considered and rejected. Without a follow-up, the recourse for
a near-miss answer is retyping the whole prompt or abandoning `a` for the interactive
harness — the exact reflex-break that
[issue #14](https://github.com/gahjelle/wingit/issues/14) says to protect.

## Why not plain `--continue`

All five harnesses have a native continue flag, so the zero-state option is real: make the
follow-up a passthrough. It was rejected because *"the most recent session in this
directory"* is a target other tools move.

- The user's own interactive harness session in the same repo can be newer than `a`'s, so
  a follow-up lands in a conversation `a` never saw.
- The reverse also holds: `a`'s one-off can be the newest session, so the user's *own*
  `--continue` resumes wingit's work.
- Copilot's `--continue` falls back to the **globally** most recent session when the cwd
  has none, so a follow-up can silently jump repos.

Each of those is a silently-wrong answer, the worst failure mode for a tool people put in
pipes. Resuming an explicit id makes the follow-up mean exactly one thing on all five
harnesses. "Resume by id" is uniformly available; "continue" is uniformly available but not
uniformly *meaningful*.

## Decisions

1. **One flag, no names.** A follow-up flag (letter allocated in
   [issue #23](https://github.com/gahjelle/wingit/issues/23)) resumes the last `a` run.
   No `-s <name>`, no user-facing session identity, no prune/rename/delete surface.
2. **wingit records a pointer after each run**: harness, session id, and key. The store is
   a **bounded LRU map**, sized to span repo×harness pairs. The bound is what keeps it a
   cache rather than the registry this ADR removes — entries age out, so nothing needs
   managing.
3. **Keyed on (repo root, harness)**, falling back to the literal working directory outside
   a repo. Repo root matches both user intent (`cd src/` should not lose the thread) and
   what the harnesses do internally — Claude Code scopes lookup to the project directory
   and its git worktrees; Opencode's cwd-scoping was verified empirically.
4. **A miss starts a fresh session**, with a short stderr notice. A different harness than
   the one that created the pointer is simply a miss: a session is bound to its harness, so
   that memory genuinely does not exist for the harness now running. No refusal path, and
   the follow-up flag never silently changes which binary runs.
5. **`a` names the sessions it creates**, prompt-derived (`-n` on Claude Code, Copilot and
   Pi; `--title` on Opencode). Because the follow-up requires persistence, every `a` run
   leaves a session in the user's own harness history; naming turns "wingit litters my
   session list" into "wingit's entries are labelled". Codex has no naming flag and
   degrades unmarked.
6. **`store_sessions`, a global config toggle**, pydantic default `true` per
   [ADR-0007](0007-self-materializing-config-defaults-in-code.md) — so it reaches the TOML
   only if the user actually sets it. Set false, runs are ephemeral
   (`--no-session-persistence`, `--ephemeral`, `--no-session`) and the follow-up does not
   work. It is global, not per-harness: it expresses a stance about leaving transcripts on
   disk, which does not vary by which binary is spawned.
7. **`store_sessions = false` refuses on Opencode and Copilot**, which have no ephemeral
   flag (both `--help`s read directly). This is the MVP's first live refuse trigger under
   [ADR-0006](0006-tool-posture-ladder.md)'s rule that safety gaps refuse and fidelity gaps
   degrade: the setting is a privacy constraint, and degrading does precisely the thing the
   user opted out of while announcing it on a stream pipeline users routinely discard.
8. **The seam grows two optional fields**: `argv` takes an optional resume id, which each
   driver spells its own way (`-r`, `-s`, `--session`, `codex exec resume`); `finish`
   returns an optional session id, **read back from the run** rather than pre-assigned.

## Why read the id back rather than pre-assign it

Only Claude Code and Copilot accept a caller-chosen `--session-id`, and Opencode's ids are
not UUIDs (`ses_08b1ff…`), so it can never take one of ours. Pre-assignment is an
orchestrator feature: it matters when the id must be known *before* the process starts.
wingit writes its pointer *after* the run, so pre-assignment buys nothing and costs a second
code path. All five report their id in their event stream. A driver that returns no id
writes no pointer, and the next follow-up is an ordinary miss — the degrade path already
specified, with no extra machinery.

## What this changes in ADR-0004

ADR-0004 deferred whether sessions are pwd-scoped. **They are** — keyed on repo root
(decision 3) — but for a pointer cache, since the registry the question was originally about
no longer exists. ADR-0004's open question is closed.

## Considered Options

- **Follow-up flag over a wingit-recorded id** (chosen).
- **Follow-up flag as a passthrough to native `--continue`** — zero state, but its meaning
  is set by the user's other tools.
- **The ADR-0002 name→UUID registry** — built for a job now out of scope.
- **No memory at all** — a sharper, more Unix-shaped v1, but it sends the near-miss case
  back to the interactive harness.
