# Testing

## Approach

Work test-first: defer to the `tdd` skill for the red → green → refactor loop. Write a failing test before any implementation, then make it pass with the minimum code needed.

## What to test

- Assert **external behavior via the CLI** — invoke `main()` or test CLI commands end-to-end.
- Do not test internal implementation details; test observable outcomes.
- The output contract is behavior worth asserting directly: the **Answer** lands on stdout as plain text, **Reasoning** on stderr (see `CONTEXT.md`).

## The fake ProcessRunner

wingit drives real harness CLIs in headless mode ([ADR-0013](../adr/0013-wrap-harnesses-because-they-are-already-logged-in.md)), so tests **never invoke a real harness** — they are slow, non-deterministic, and need the harness CLI plus API keys installed. Instead, tests inject a **fake `ProcessRunner`** (`RecordedRunner`, in `tests/conftest.py`) that replays **recorded harness bytes**, and run the **real** `HarnessDriver` and core on top, asserting behavior through `core.dispatch` / `main()`. See [ADR-0014](../adr/0014-fake-the-io-boundary-not-the-driver.md).

- Recorded stdout/stderr + exit codes live in `tests/fixtures/<harness>/`, copied from `prototypes/adapter-seam/recordings/`; they are the contract for what real output looks like. Edge cases the recordings don't cover (an empty answer, a `thinking` block) are crafted as a few realistic JSONL lines fed to the real parser — never hand-faked events.
- Never shell out to a real harness in tests. The fake seam is the `ProcessRunner`, not the driver: substitute the I/O boundary, not wingit's own parsing.

## Boundaries

- `tmp_path` (pytest's built-in fixture) is the only real filesystem boundary allowed in tests.
- No network calls in tests — use the fake `ProcessRunner` on recorded bytes.
- No mocking of the filesystem — use `tmp_path` for real file I/O.
- Config lives in the user config dir (`platformdirs.user_config_path`), overridable via `WINGIT_CONFIG_FILE` ([ADR-0007](../adr/0007-self-materializing-config-defaults-in-code.md)); point it inside `tmp_path` so tests read and write real files in isolation without touching the developer's real config.

## Test layout

Tests live in `tests/`. Pytest is configured with `testpaths = ["tests"]` and the src layout (`src/` on the path via uv). Test files follow the `test_<module>.py` convention.
