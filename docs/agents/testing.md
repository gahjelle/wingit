# Testing

## Approach

Work test-first: defer to the `tdd` skill for the red → green → refactor loop. Write a failing test before any implementation, then make it pass with the minimum code needed.

## What to test

- Assert **external behavior via the CLI** — invoke `main()` or test CLI commands end-to-end.
- Do not test internal implementation details; test observable outcomes.
- The output contract is behavior worth asserting directly: the **Answer** lands on stdout as plain text, **Reasoning** on stderr (see `CONTEXT.md`).

## The fake harness

wingit drives real harness CLIs in headless mode ([ADR-0001](../adr/0001-drive-harnesses-headless-not-model-apis.md)), so tests **never invoke a real harness** — they are slow, non-deterministic, and need the harness CLI plus API keys installed. Instead, tests inject a **fake `HarnessDriver`** (`harnesses/fake.py`) that returns canned stdout/stderr, and drive `main()` end-to-end against it. See [ADR-0003](../adr/0003-fake-harness-driver-test-seam.md).

- Never shell out to a real harness in tests, and never mock the subprocess layer instead of using the fake driver.

## Boundaries

- `tmp_path` (pytest's built-in fixture) is the only real filesystem boundary allowed in tests.
- No network calls in tests — use the fake harness.
- No mocking of the filesystem — use `tmp_path` for real file I/O.
- Runtime state (config + session registry) lives in XDG dirs, redirected via `WINGIT_STATE_DIR` ([ADR-0004](../adr/0004-xdg-state-pwd-scoping-deferred.md)); point it at `tmp_path` so tests read and write real files in isolation without touching the developer's real state.

## Open question

Whether sessions are scoped to the working directory (`pwd`) is undecided — the harness's own sessions are keyed by project dir, which may argue for it. Resolving this may relocate the registry and change what tests set up. Until then, tests treat the registry as a single store under `WINGIT_STATE_DIR`.

## Test layout

Tests live in `tests/`. Pytest is configured with `testpaths = ["tests"]` and the src layout (`src/` on the path via uv). Test files follow the `test_<module>.py` convention.
