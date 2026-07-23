# Tests fake the I/O boundary, running the real driver on recorded bytes

> Supersedes [ADR-0003](0003-fake-harness-driver-test-seam.md). ADR-0003's principle — tests never
> spawn a real harness — stands. Its *mechanism* — an in-process fake `HarnessDriver` — is
> replaced: tests inject a fake `ProcessRunner` and run the **real** driver against **recorded
> harness bytes**.

wingit drives real harness CLIs headless (ADR-0001), and tests must stay fast, deterministic, and
free of installed harnesses or API keys. ADR-0003 achieved that with a fake `HarnessDriver`
returning canned output. This ADR keeps the "no real harness in tests" guarantee but moves the seam
one layer down: the substitution point is a narrow `ProcessRunner`, and the **real** driver
(`argv`/`feed`/`finish`) plus the **real** core run on recorded fixtures captured from the actual
binaries (`prototypes/adapter-seam/recordings/`).

## Why the seam moved

A fake `HarnessDriver` speaks the core's normalized `Event` currency directly, so the end-to-end
happy path never runs the real parser — and the parser is where the bugs live: Claude's
`.result`-vs-`assistant`-preamble divergence and the `is_error`-under-`subtype:"success"` trap
(ADR-0005). Covering those needs a second parser-test tier anyway, and a hand-authored fake can
drift from real output, so the fake-driver path asserts an idealized world.

Faking the I/O boundary instead runs the whole real pipeline — `argv` → real JSON parse →
`is_error` trap → `.result` extraction → reduction → stdout/stderr split → exit code — against
ground-truth bytes, in one seam. Edge cases the fixtures don't cover (empty answer, a `thinking`
block) are crafted as a few realistic JSONL lines fed to the *real* parser. It scales to the
five-harness world of T2: each driver is tested against its own recorded fixtures, which already
exist.

## Decisions

1. **The test seam is a `ProcessRunner`, injected.** Real `HarnessDriver` + real core run above it.
2. **Recorded harness bytes are the corpus.** The `prototypes/adapter-seam` recordings are copied
   into `tests/fixtures/<harness>/`; they are the contract for what real output looks like.
3. **The runner Protocol is line-iterator + stderr + exit**, so streaming (T7) swaps a live
   iterator behind the same seam.
4. **Crafted JSONL is allowed for edges**, fed to the real parser — never hand-faked events.
5. **The OS-level spawn is not covered by fast tests** (true of any fast approach) — `stdin=DEVNULL`,
   `cwd`, env handling are validated by the manual five-peer `live-check` from T2.

## Consequences

- The most bug-prone layer (real parsing of messy harness JSON) is now on the default test path.
- Fixtures must be maintained as harnesses churn — a feature: the fixture is the contract.
- No `harnesses/fake.py`; the double lives in `tests/` and is test-only, never shipped.

## Considered Options

- **Fake the I/O boundary** (chosen) — real driver + core on real bytes; one honest, fast seam.
- **Fake `HarnessDriver`** (ADR-0003, superseded) — decoupled but idealized; splits coverage.
- **Fake executable on `PATH`** — real spawn, but slow and shell-dependent; this is `live-check`.
