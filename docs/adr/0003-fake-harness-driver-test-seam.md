# Tests run against a fake HarnessDriver, never a real harness

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
