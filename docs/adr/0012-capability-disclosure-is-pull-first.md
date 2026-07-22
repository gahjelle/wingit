# Capability differences are disclosed on request, not announced

`a` behaves differently depending on which harness is behind it, and it does **not** tell
you about that on every run. Static harness shape is reference material, published by a
`show-capabilities` command. The only thing `a` says unasked is when something *you asked
for on this run* could not be delivered.

Decided in [issue #27](https://github.com/gahjelle/wingit/issues/27). Refines
[ADR-0005](0005-capability-negotiating-harness-seam.md) — the declared capability set grows
to carry the tool rungs — and gives
[ADR-0006](0006-tool-posture-ladder.md)'s "whether `a` surfaces capability differences
proactively is still open" its answer.

## Why pull, not push

Capabilities are **static per harness**. Copilot streams on every run, forever; Codex has
no `--tools none` today and will not acquire one between two invocations. A proactive
channel would therefore repeat an unchanging fact on every run of a tool that lives in
pipes — the definition of noise, charged against the reflexivity budget
[issue #14](https://github.com/gahjelle/wingit/issues/14) exists to defend.

The user learns the shape of their harness by using it, and has one place to look when
that shape surprises them.

## The axes

Four declared binaries, all of which diverge across the five harnesses:

| | Claude Code | Pi | Opencode | Copilot | Codex |
| --- | --- | --- | --- | --- | --- |
| streams the answer | ✗ | ✓ | ✗ | ✓ | ✗ |
| shows reasoning while it works | ✓ | ✓ | ✗ | ✗ | ✓ |
| supports `--tools none` | ✓ | ✓ | ✓ | ✓ | ✗ |
| can run without storing a session | ✓ | ✓ | ✗ | ✗ | ✓ |

Two candidate axes were **excluded**:

- **Latency.** Issue #14 measured a ~5× swing and handed on the finding that harness choice
  is the only real latency lever `a` has, which argues for surfacing it at first run. It is
  excluded anyway: latency is a harness **×** model product, so it is not a per-harness fact
  and cannot be declared by a driver at all. A shipped "Copilot: slow" would also be five
  prompts measured on one machine, frozen into a table that rots.
- **OS-enforced read-only sandbox** (Codex alone). ADR-0006 §3 forbids wingit's output ever
  calling the `read` rung "sandboxed"; a row where four of five harnesses show ✗ states
  exactly that inference in table form.

Neither [ADR-0008](0008-follow-up-not-named-sessions.md) nor
[ADR-0011](0011-project-environment-inherited-whole.md) adds a fifth: resume-by-id is
uniformly available, and the inherited environment needs no capability negotiation.

## Decisions

1. **`show-capabilities` is a third command**, alongside `show-config` and `repair-config`.
   It takes an optional list of harnesses and **defaults to all five**, including harnesses
   that are not installed — marking each as installed or not, and marking which one is
   configured. "What would I gain by installing something else?" is the only actionable
   question a capability table raises, and it cannot be answered by a table of what you
   already have. It also makes ADR-0007 §7's preference ranking visible, which today is
   invisible to the user who just gets whatever won.

2. **`show-config` does not carry capabilities.** ADR-0007 §9 defines it as rendering the
   validated model, which is why nothing in it can go stale. Capabilities are declared by
   the driver, not configured, so including them would put unconfigured facts in a
   configuration view and require printing outside the model render.

3. **First run calls `show-capabilities` with the detected harnesses.** It is the same
   renderer at a second call site, not a bespoke message. First run's only privileges are
   the setup it cannot avoid — detect, write the file, report what it wrote and where
   (ADR-0007 §1).

4. **First run applies no presentation rule of its own.** No TTY gate, no suppression in a
   pipe: suppressing *is* special treatment. Any terminal-versus-log difference belongs to
   the renderer and applies uniformly. The accepted cost is one short table in a CI log,
   once per install.

5. **A notice fires only when the user asked for something on this run that wingit could
   not deliver.** Static harness shape never fires. This is what keeps ADR-0006 §5's
   `codex cannot run with tools=none; using tools=read` in, and keeps out a notice on every
   Codex run about network being off at `write` — a divergence nobody asked about.
   **Config counts as asking**: a pinned `tools = "none"` against Codex notices on every
   run, because silently ignoring a written-down choice is worse than repeating yourself.

6. **The table is derived from the driver declarations, never hand-maintained.** A display
   table is a second copy of the truth that goes stale exactly when a harness changes — the
   failure ADR-0007 designed the rendered view to avoid. **Consequence: the tool rungs move
   out of ADR-0006's per-harness prose table and become declared capabilities.**

7. **Declarations are static and class-level**, known without executing anything.
   `show-capabilities` reports on harnesses that are not installed, and ADR-0005 §2 already
   requires streaming to be decided before the run — neither is compatible with probing.

8. **Documentation describes the axes, never the grid.** The README explains what the four
   axes mean and points at `a show-capabilities`; the pre-install audience gets prose about
   the ranking rather than a matrix. A grid in the README is the hand-maintained second copy
   ruled out above, with nothing in `just check` to catch it drifting.

## Consequences

- **Same renderer, different stream per call site.** First run writes to **stderr**
  (ADR-0007 §1); `a show-capabilities` writes to **stdout**, because the table is that
  command's answer and [issue #12](https://github.com/gahjelle/wingit/issues/12) reserves
  stdout for answers.
- **The rule in §5 governs notices, not refusals.** Refusals are ADR-0005 §4 and ADR-0006
  §5, and are untouched — a refusal is the command failing, not a line on stderr. ADR-0008's
  `store_sessions` toggle is the MVP's live refuse trigger.
- **The fourth axis is the one with teeth.** The first three degrade quietly; running
  without storing a session *refuses* on Opencode and Copilot. Publishing it is what lets
  a user find that out before hitting the refusal.
- **Capability declarations must stay honest**, as ADR-0005 already warned — Copilot's
  `assistant.reasoning` events exist in the schema and carry nothing. They are now
  user-visible, so a wrong declaration is a wrong statement to the user, not just a wrong
  internal branch.
- **Whether the landing page needs a build-time-generated grid** is left to
  [issue #26](https://github.com/gahjelle/wingit/issues/26), which owns the pre-install
  audience.

## Considered Options

- **Pull-first, with a first-run table and run-specific notices** (chosen).
- **Proactive disclosure on every run** — rejected: repeats unchanging facts in a tool built
  to feel reflexive.
- **Total silence, learn by use** — rejected: leaves no way to answer "why did this harness
  behave differently?", and no way to compare before installing.
- **Fold capabilities into `show-config`** — rejected: mixes declared facts into a render of
  configured ones, and costs `show-config` the property that makes it trustworthy.
- **Include latency** — rejected: not a per-harness fact, and a measurement that rots.
