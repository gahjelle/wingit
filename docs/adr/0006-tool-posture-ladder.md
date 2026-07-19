# A three-rung tool posture, defaulting to read-write on every invocation

`a` grants the harness one of three tool postures — `none`, `read`, `write` — selected by
`--tools` and defaulting to `write` regardless of how `a` was invoked. Each rung means the
same thing on every harness; where a harness cannot express a rung, `a` degrades to the
nearest one and says so on stderr.

Decided in [issue #15](https://github.com/gahjelle/wingit/issues/15). Refines
[ADR-0005](0005-capability-negotiating-harness-seam.md) §4 and supersedes the TTY-inferred
default from [issue #9](https://github.com/gahjelle/wingit/issues/9).

## The ladder

| rung | meaning |
| --- | --- |
| `none` | No tools. The answer is a function of stdin and the prompt, nothing else. |
| `read` | Read tools. **No shell, no network.** |
| `write` | All tools approved. The harness's own network default is respected. |

`--tools none\|read\|write` is canonical; config key `tools`. Long aliases `--no-tools`,
`--read-only`, `--read-write`. Short single-letter flags are deliberately **not** allocated
here — `a`'s letter-space is a scarce shared resource and is allocated once, across the whole
surface, in [issue #23](https://github.com/gahjelle/wingit/issues/23).

The posture is settable in **both** directions by flag and by config, so a script can pin it
deterministically against any default.

## Decisions

1. **The default is `write`, on every invocation.** Piped, bare at a TTY, in a script, under
   CI — the same. An AI in the middle of a pipe is `a`'s selling point, and most of the value
   is the agent *performing* an operation the user didn't know how to write in bash or didn't
   have time to. Constraint is available, cheap to reach for, and opt-in.

2. **TTY governs presentation, never authority.** Issue #9 inferred the posture from
   `sys.stdin.isatty()` while flagging that as a knowing departure from convention. The
   departure is reverted. TTY detection survives only where it conventionally belongs — the
   progress indicator from [issue #14](https://github.com/gahjelle/wingit/issues/14).

3. **`read` is a tool grant, not a sandbox.** A genuinely read-only shell is an OS-level
   property that only Codex has. The alternatives were an allowlist of "shell commands that
   don't mutate" — a security judgement with no principled stopping point, in a setting where
   the model writes the command. So `read` drops shell entirely. Nothing in wingit's docs or
   output may call this "sandboxed."

4. **The rungs govern reach, not just the filesystem.** Network tools (`WebFetch`,
   `web_search`, `url(...)`, fetch) are off at `none` and `read`. A read-only agent that can
   still reach the network is an exfiltration path requiring no write and no shell — and the
   user who dropped a rung because they distrusted their input is exactly the user who should
   not have to ask for that separately.

5. **Safety gaps refuse; fidelity gaps degrade with a notice.** This refines ADR-0005 §4,
   whose refuse clause was written for an explicitly requested *safety* guarantee. `none` is a
   determinism-and-latency rung, not a safety rung, so a harness that cannot express it
   degrades rather than refusing. The notice is one line on stderr in `a`'s own voice, naming
   the canonical knob: `codex cannot run with tools=none; using tools=read`. ADR-0005 §4's
   refuse clause stands, with no live trigger in the MVP.

6. **Piped stdin is wrapped in an explicit delimited data block, labelled as data rather than
   instructions.** `a` builds the prompt, so this needs no capability from any harness.
   `codex exec` already draws this distinction itself (*"stdin is appended as a `<stdin>`
   block"*); passing stdin through undelimited would discard a distinction a harness bothered
   to make. This is a hint the model may ignore, **not** a boundary, and the documentation must
   say so — the honest answer for untrusted input is `--tools read` or `--tools none`.

## Per-harness mapping

| harness | `none` | `read` | `write` |
| --- | --- | --- | --- |
| Claude Code | `--disallowedTools` (all) | read tools only | `--permission-mode` auto-approve |
| Copilot | `--deny-tool` | read tools only | `--allow-all-tools` (required headless) |
| Opencode | `permission` map | read tools only | `--auto` |
| Pi | `-nt` | `-t read` | default (no approval concept) |
| Codex | **unavailable** → `read` | `-s read-only` | `-s workspace-write` |

Two survey expectations did not survive contact:

- **Pi is not the problem case.** Its tools are flat — `read`, `bash`, `edit`, `write` — so
  `-t read` is a *complete* expression of the `read` rung once that rung excludes shell. Pi is
  first-class at all three rungs and never triggers the degrade notice.
- **Codex is the constrained one.** `codex exec` has no tool allow/deny whatsoever, only
  `-s {read-only, workspace-write, danger-full-access}`. It collapses `none` into `read`.

Codex's kernel-enforced `read-only` sandbox is a strictly better implementation of the `read`
rung, and the adapter uses it — but it is not *required* of the rung, or four harnesses could
not offer it at all.

## Consequences

- **`a` writes by default in any script.** That is the intended shape, but it raises the stakes
  on the first-run experience — handed to
  [issue #16](https://github.com/gahjelle/wingit/issues/16).
- **Behaviour differs visibly by harness.** Codex silently keeps network off at `write` while
  the others follow their own defaults, and Codex degrades at `none`. Whether `a` surfaces
  capability differences proactively is still open.
- **Whether an explicit `--sandbox` axis belongs in the MVP** is left to
  [issue #18](https://github.com/gahjelle/wingit/issues/18). ADR-0005 §4's refuse clause is
  what would govern it.
- **A fourth rung above `write`** (Codex's `danger-full-access`, writable roots beyond the
  workspace) is deliberately not designed. Add it when someone asks.

## Considered Options

- **Three rungs, default `write`** (chosen) — matches what `a` is for; constraint is one flag away.
- **Two rungs (`read`/`write`), default inferred from TTY** — issue #9's position. Rejected:
  routes authority through a presentation signal, and makes the primary use case behave
  differently in a Makefile than by hand.
- **Three rungs, default `none` when piped** — rejected: deterministic and fast, but it
  forfeits the tool use that is most of the reason to put an agent in a pipe.
- **`read` includes a read-only shell** — rejected: honoured natively by one harness of five,
  and puts wingit permanently in the business of judging which shell commands mutate.
- **Refuse when a harness cannot express a rung** — rejected for `none`: applies a safety rule
  to a non-safety rung, costing a whole harness a rung for no safety gain.
