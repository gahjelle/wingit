# Tests run against a fake HarnessDriver, never a real harness

> **Status: active.** Re-ratified during the
> [replan](https://github.com/gahjelle/wingit/issues/8) by
> [The MVP boundary](https://github.com/gahjelle/wingit/issues/18), whose *contract gate*
> — the fake driver, on every `just check` — chose this seam again for the same reasons.
> This is the **only** pre-0005 ADR that carries authority. Its reasoning was not replaced,
> so there is no superseding ADR; it is cited by number in `AGENTS.md`.

wingit drives real harness CLIs in headless mode (ADR-0001), but tests inject an
in-process fake `HarnessDriver` (`harnesses/fake.py`, implementing the
`harnesses/base.py` Protocol) that returns canned stdout/stderr, and assert behavior by
driving `main()` end-to-end. Real harnesses are never invoked in tests.

## Considered Options

- **In-process fake HarnessDriver** (chosen) — fast, hermetic, deterministic, and needs
  no harness CLI or API keys installed.
- **A fake executable on PATH** — a real stub script wingit shells out to. Rejected for
  now: it exercises the actual subprocess/argv path but is slower and shell-dependent,
  and the fidelity it buys can be covered by a small number of targeted tests later if
  needed.

## Consequences

- The subprocess/argv-building layer of the real drivers is not exercised by the default
  test suite — it must be kept thin and covered separately if it grows logic.
- Never mock the subprocess layer as a substitute for the fake driver; inject the fake.
