# T2 (#37) — Implementation plan: five harnesses behind the seam + Ctrl-C spawn contract

Handoff from the `/grill-with-docs` design session. This is the **implementation** plan for a
fresh session that has cleared the design context. Design rationale lives in the ADRs and the
issue — this document does not repeat it, it tells you what to build and in what order.

## Read these first (do not re-derive)

- **Issue:** https://github.com/gahjelle/wingit/issues/37 — checklist is the acceptance surface.
- **Design PR (docs only, ADRs):** https://github.com/gahjelle/wingit/pull/50
- **ADR-0005** `docs/adr/0005-capability-negotiating-harness-seam.md` — the seam, exit-code-primary, `stdin=DEVNULL`.
- **ADR-0006** `docs/adr/0006-tool-posture-ladder.md` — rung → per-harness flag mapping (only the `write` column matters for T2).
- **ADR-0011** `docs/adr/0011-project-environment-inherited-whole.md` — env inherited whole, cwd-on-child, Pi `--approve` (resolved).
- **ADR-0014** `docs/adr/0014-fake-the-io-boundary-not-the-driver.md` — fake `ProcessRunner`, real driver on recorded bytes.
- **ADR-0015** `docs/adr/0015-interrupt-is-a-hard-stop-through-shared-process-group.md` — the Ctrl-C contract.
- **ADR-0016** `docs/adr/0016-copilot-driven-through-its-undocumented-json-stream.md` — Copilot JSON path.
- **Reference implementations:** `git show prototype/adapter-seam:prototypes/adapter-seam/adapters.py` — the five throwaway adapters with every leak annotated. Copy the *parsing logic*, not the capability model (the prototype's capability enum is stale — see below).
- **Recorded fixtures (source):** `git show prototype/adapter-seam:prototypes/adapter-seam/recordings/` — `<harness>.<scenario>.{stdout,stderr,meta.json}` for all five × {prose, tools, fail} (plus `copilot-text`).
- **Working conventions:** `docs/agents/tracer-workflow.md`, `docs/agents/git-workflow.md`, `docs/agents/code-conventions.md`, `docs/agents/testing.md`, `docs/agents/quality-gates.md`.

## Ground rules for this slice

- **Test-first**, using the `tdd` skill, against **recorded harness bytes behind a fake `ProcessRunner`** — never a real harness in the fast tests (ADR-0014). Real binaries only in `just live-check`.
- Branch off `main` in a new worktree `agent/37-<slug>`; tick the issue checklist as each item lands and is verified; keep `just check` green; open a PR for squash-merge.
- **Prefer long-form flags** in every harness argv (`--print` not `-p`, `--approve` not `-a`). This applies to the argv wingit *emits*, not to `a`'s own CLI short flags.
- No `--tools`, no stdin/transform, no streaming/spinner/timeout, no config-driven default — all out of scope (deferred to T3/T7).

## The capability grid (settled, verified live)

Shape: **`dict[Capability, bool]`** per driver (NOT a `frozenset` — decided so a new enum member
forces a conscious yes/no in every driver, caught by a totality test). The four axes are the
existing `Capability` members in `src/wingit/schemas/__init__.py`.

| capability | Claude | Copilot | Codex | Opencode | Pi |
|---|---|---|---|---|---|
| `STREAMS` | False | True | False | False | True |
| `SHOWS_REASONING` | True | False | True | True | True |
| `SUPPORTS_TOOLS_NONE` | True | True | False | True | True |
| `RUNS_WITHOUT_STORING_SESSION` | True | False | True | False | True |

- Opencode `SHOWS_REASONING = True` was confirmed live: `opencode run --thinking --format json`
  emits `type: reasoning` events carrying real text separate from the answer.
- The prototype's `adapters.py` capability sets are **stale** (they use `SEPARABLE_REASONING`,
  `RELIABLE_FAILURE`, `SESSIONS`, `OS_SANDBOX`, `STREAMING_ANSWER` — a different model). Ignore
  them; use the grid above against the real `Capability` enum.

## Work items (each is a red→green→refactor cycle)

### 1. Capability declaration shape + totality test
- Change `HarnessDriver.capabilities` from `frozenset[Capability]` to `dict[Capability, bool]`
  (`src/wingit/harnesses/base.py`). Update the `ClaudeDriver` accordingly.
- Add a test asserting **every** driver's `capabilities.keys() == set(Capability)` (totality),
  parametrized over the registry.
- Fix `ClaudeDriver`: it currently omits `RUNS_WITHOUT_STORING_SESSION`; per the grid it is
  `True`. Also switch its argv `-p` → `--print`.

### 2. `Harness` enum + driver registry + lifecycle
- Add `Harness(StrEnum)` to `schemas` with members ordered by CONTEXT.md detection rank:
  `claude, pi, opencode, copilot, codex`. (Values are the canonical lowercase names.)
- Registry `Harness → driver class` in `src/wingit/harnesses/__init__.py` (the prototype's
  `DRIVERS` dict is the template).
- **Lifecycle:** `dispatch` must construct a **fresh driver instance per run** — Opencode,
  Copilot, and Pi are stateful (they buffer text across lines and pick the answer at `finish`).
  Add one line to the `HarnessDriver` Protocol docstring: *one instance per run; `feed`/`finish`
  may accumulate state.*

### 3. The four new drivers (`src/wingit/harnesses/{opencode,codex,copilot,pi}.py`)
Port parsing from `prototype/adapter-seam:prototypes/adapter-seam/adapters.py`. Argv (long-form,
`write` rung, context inherited, session stored — do **not** pass ephemeral flags):

| harness | argv (prompt last) |
|---|---|
| Opencode | `opencode run --format json --auto --thinking <prompt>` |
| Codex | `codex exec --json --skip-git-repo-check --sandbox workspace-write <prompt>` |
| Copilot | `copilot --prompt <prompt> --output-format json --allow-all-tools --log-level none` |
| Pi | `pi --print --mode json --approve <prompt>` |

Parsing notes (from the prototype; verify against fixtures):
- **Opencode:** no terminal answer event — buffer `text` parts per `step_start`, answer = last
  step's joined text at `finish`. Map `type: reasoning` → `ReasoningChunk` (new vs prototype).
  `error` event → `Failed`.
- **Codex:** `item.completed` → `agent_message` = `FinalAnswer`, `reasoning` = `ReasoningChunk`,
  `command_execution` = `ToolActivity`; `turn.failed` / item `error` → `Failed`.
- **Copilot:** `assistant.message_delta` (deltas, buffered), last non-empty `assistant.message`
  = final answer. `assistant.reasoning` content is always empty → emit nothing. **No synthetic
  `Failed`** — a failed run emits nothing in-band; let the core use exit code + stderr.
- **Pi:** `message_update.assistantMessageEvent` `text_delta`/`thinking_delta`; `turn_end` last
  non-empty text = final. **No synthetic `Failed`** (same as Copilot).
- **In-band `Failed` only where real:** Claude (`is_error` under `subtype:"success"`), Opencode
  (`error`), Codex (`turn.failed`). Copilot & Pi: silent. The prototype's synthetic
  `Failed("harness failed (detail only on stderr)")` for Copilot/Pi is a **bug** — it would
  suppress the real stderr the core prefers. Do not port it.

### 4. Fixtures
- Copy recordings from `prototype/adapter-seam` into `tests/fixtures/<harness>/<scenario>.stdout`
  (+ `.stderr` where a driver needs it), matching the existing `tests/fixtures/claude/` layout.
- **Re-record Opencode with `--thinking`** so its fixtures contain the `reasoning` events the real
  driver now parses (the existing recordings were made without it). Use the prototype's `record.py`
  approach or capture manually; the fixture is the contract (ADR-0014).
- Per-driver tests run the **real** driver over these bytes and assert the Answer / Reasoning /
  exit-code reduction (prose, tools, fail scenarios each).

### 5. CLI: harness selection
- `--harness {claude,copilot,codex,opencode,pi}` (long-only) + two-letter shorts
  `-cl -cp -cx -oc -pi` (cyclopts accepts these as boolean `Parameter(name=["-cl"])`).
- A pure helper `resolve_harness(harness, cl, cp, cx, oc, pi) -> Harness` (keep `cli.py` thin).
  Selecting a harness **more than once by any combination** (two shorts, or short+long, even if
  they agree) → raise so it maps to `ExitCode.USAGE`. cyclopts does **not** auto-mutex; enforce it
  (a cyclopts group validator, or raise a `CycloptsError` from the resolver).
- Default (none given) → `Harness.claude` (hardcoded; T3 makes it config-driven).
- Unit-test `resolve_harness` directly (all singles, the default, every conflict shape).

### 6. Ctrl-C / interrupt contract (ADR-0015)
- Add `ExitCode.INTERRUPTED = 130` to the enum.
- `main()` catches `KeyboardInterrupt` → `sys.exit(ExitCode.INTERRUPTED)` (before/around the
  existing `CycloptsError` handling in `src/wingit/__main__.py`).
- **Do not** add a signal handler and **do not** set `start_new_session=True` on the subprocess —
  the shared process group + `subprocess.run`'s SIGKILL backstop is the contract.
- Test: fake `ProcessRunner.run` raises `KeyboardInterrupt`; assert `main()` exits `130` and
  **stdout is empty** (no partial answer).

### 7. `just live-check` (manual, never CI)
Runs the built `a` against live binaries. 7 runs:
- **5 × ask-cwd**, one per harness (`a -cl "..."` … `a -pi "..."`), prompt e.g. *"how many
  markdown files are in the current directory? Answer with just the number."* — proves seam +
  `stdin=DEVNULL` (no Pi/Codex hang) + cwd-on-child + tools-at-write, live.
- **1 × pipe smoke:** `a "reply with exactly one word: pineapple" | cat` — stdout carries the
  Answer verbatim, one trailing newline, no Rich markup.
- **1 × scripted SIGINT:** start `a` in the background on a slow prompt, `sleep 2`,
  `kill -INT <pid>`, then assert `$?` is `130` and `pgrep -P <pid>` shows no surviving child.
  (Scripted, not a human keypress — real signal, repeatable, still never CI.)
- Recipe requires all five harnesses installed + logged in; keep it out of `just check`.

### 8. Housekeeping
- `just check` green throughout (fake driver only).
- Tick the issue checklist as items land. Reword the env line when you get there: T2 does **env
  passthrough only** — the `COPILOT_ALLOW_ALL` denylist is **deferred to the `--tools` slice**
  (it has no live trigger while the rung is fixed at `write`).
- Add the long-form-flag convention to `docs/agents/code-conventions.md`.

## Known live-check risks to watch (findings, not redesigns)
- **Copilot without `--allow-all-paths`:** headless writes *might* hit an unanswerable
  path-verification prompt. Keep `--allow-all-tools` (ADR-0006: network at harness default); if
  writes block, that's a live-check finding to record, not a T2 redesign.
- **Copilot JSON is undocumented** (ADR-0016): if the event shape drifted since the prototype
  recordings, the fixture/live-check mismatch will be loud — update fixtures to match.

## Suggested skills for the implementation session
- **`tdd`** — this slice is mandated test-first (red→green→refactor) against recorded bytes.
- **`domain-modeling`** — if a new term or ADR-worthy decision surfaces mid-build (e.g. the
  Copilot path-prompt finding forces a real choice). Don't invent ADRs otherwise.
- **`run`** — to drive the built `a` for `just live-check` verification against real harnesses.
- **`code-review`** / **`simplify`** — before opening the PR, review the branch against the
  issue spec and the repo's standards.
