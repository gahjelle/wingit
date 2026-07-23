# Code conventions

## Environment

- Python 3.14, managed by **uv**.
- Install deps: `uv sync`. Run tools: `uv run <tool>`.
- Source layout: `src/wingit/` for application code, `tests/` for tests. Repo-specific conventions are enforced by **garuff**, a PyPI dev dependency (no in-repo tooling package).

## Package layout

wingit follows a thin-CLI split (mirroring the structure that worked well upstream):

- `cli/` — thin layer: argument parsing and dispatch only, no domain logic.
- `harnesses/` — one driver per harness. `harnesses/base.py` defines the `HarnessDriver` and `ProcessRunner` Protocols; real drivers (e.g. `harnesses/claude.py`) build the argv and normalize output; `runner.py` holds the real `ProcessRunner`. The injected test seam is a fake `ProcessRunner` (not a fake driver) in `tests/`, running the real driver on recorded bytes (see [testing.md](./testing.md) and [ADR-0014](../adr/0014-fake-the-io-boundary-not-the-driver.md), superseding [ADR-0003](../adr/0003-fake-harness-driver-test-seam.md)).
- `schemas/` — typed domain models on the project's `FrozenModel`/`StrictModel` bases (see GAC002).
- `console.py` — the output contract: the **Answer** goes to stdout, **Reasoning** to stderr (see `CONTEXT.md`).
- `sessions.py` — the session registry mapping session name → harness-native UUID.
- `config/` — configuration via **configaroo**.

These modules are created test-first as real work lands; this describes the intended shape, not a scaffold to fill in upfront.

## Linting and formatting

- **ruff** with `select = ["ALL"]` and ignores `COM812`, `D203`, `D213`, `PLR0913` (the last superseded by GAC008).
- Per-file test ignores: `S101`, `PLR2004`, `SLF001`, `INP001`.
- Every public module, class, and function **must have a docstring** (ruff `D` rules enforce this). Functions and methods go further — *every* one needs at least a one-line docstring, including `_`-prefixed and nested functions that ruff's `D` rules leave alone (enforced by GAC010 below).
- Full **type annotations** are required on all public APIs (ruff `ANN` rules enforce this).
- Never blanket-ignore the linter with `# noqa` — fix the issue or use a targeted `# noqa: CODE` with a comment explaining why.
- For intentional Unicode characters that trigger RUF001 (ambiguous characters), use `\N{name}` escapes (e.g., `\N{EN DASH}`) instead of the literal character or `\u` escapes. This is self-documenting and avoids the noqa entirely.

## Repo conventions (`garuff`)

Some conventions can't be expressed in ruff or ty, so they're enforced by
[**garuff**](https://pypi.org/project/garuff/), a dev dependency wired into
`just check` (the `conventions` gate). It reports `GA` codes (`GAC*` for code
rules, `GAA*` for ADR rules). Run it directly with `uv run garuff check
[paths...]`; `--fix` applies garuff's available fixers and reports what remains.
Explain any rule with `uv run garuff rule <CODE>` (or `--all`). Configuration
lives under `[tool.garuff]` in `pyproject.toml`. Each rule and how to satisfy it:

- **GAC001 — no `from __future__ import annotations`.** Python 3.14 evaluates
  annotations lazily (PEP 649), so the import is dead weight. Delete it; quote
  any annotation that genuinely needs deferring, or guard the import under
  `if TYPE_CHECKING:`.
- **GAC002 — Pydantic models inherit `FrozenModel`/`StrictModel`, never `BaseModel` directly.**
  These are thin project bases (`wingit.schemas`) — `BaseModel` subclasses that
  forbid extra fields — and are the only classes allowed to subclass `BaseModel`.
  Inherit `FrozenModel` for immutable models, `StrictModel` for mutable ones.
- **GAC003 — `Protocol` methods omit the `...` body.** The docstring is body
  enough; drop the trailing `...`.
- **GAC004 — docstrings use single backticks, never double.** Write `` `code` ``,
  not double-backtick code.
- **GAC005 — homogeneous sequences use `list[T]`, not `tuple[T, ...]`.**
- **GAC006 — return `Self`, never a string forward-ref to the enclosing class.**
  Import `Self` from `typing` and annotate `-> Self` instead of `-> "Thing"`.
- **GAC007 — ruff-exempt modules stay at runtime, not in `TYPE_CHECKING`.**
  `pathlib`, `datetime`, `typing`, and `wingit.cli` are listed under
  `[tool.garuff.rules.GAC007] exempt-modules` in `pyproject.toml` (mirroring
  ruff's `[tool.ruff.lint.flake8-type-checking] exempt-modules`), so ruff will
  never move them into a `TYPE_CHECKING` block. Keep their imports at module top
  level; do not nest them under `if TYPE_CHECKING:`.
- **GAC008 — at most 1 positional parameter.** Functions with many positional
  args are hard to call correctly. Beyond 1, make parameters keyword-only
  (after a bare `*` separator). `self`/`cls` in methods don't count toward
  the limit.
- **GAC009 — `@dataclass` must pass `kw_only=True`.** Stdlib dataclasses
  otherwise accept fields positionally, so a multi-field value object gets
  built as `Thing(a, b, c, …)` — the same hard-to-read positional soup GAC008
  guards against at the definition. Making the dataclass `kw_only` forces every
  call site to name its fields, and `ty` flags any positional construction for
  free. (Pydantic `FrozenModel`/`StrictModel` already reject positional args,
  so GAC002's models need nothing extra; this rule covers the stdlib
  `@dataclass` that GAC002 doesn't.)
- **GAC010 — every function/method has a docstring.** At least a one-line
  docstring on *every* `def`/`async def`, including `_`-prefixed helpers and
  nested functions. ruff's pydocstyle `D` rules only require docstrings on
  *public* names, so private and nested functions slip through; GAC010 closes
  that gap. The name plus a behavioral one-liner keeps even tiny helpers
  self-explanatory.
- **GAC011 — no possessive `my` prefix in code or docs.** An identifier or token
  beginning with `my` followed by `_` or `-`, or `My` followed by an uppercase
  letter, models bad naming and leaks into examples shown to users. Pick a name
  that describes the thing instead.
- **GAA001 — no duplicate numeric prefixes in `docs/adr/`.** Two ADR files must
  not share the same `NNNN-` prefix. Parallel branches each adding "the next"
  ADR collide on a number; this catches it at `just check` time, before merge.
  Renumber one of the colliders so every ADR prefix is unique.
- **GAA002 — ADR numbers are consecutive from `0001`.** The prefixes in
  `docs/adr/` must form `0001, 0002, …, N` with no gaps and no zero. A gap
  suggests a deleted or missing ADR; a non-1-based start suggests a truncation.
  Both are drift from the sequential convention in [domain.md](./domain.md).
  Unlike the code rules, GAA001/GAA002 scan the `docs/adr/` directory as a whole.

## Style

- Prefer `pathlib` over `os.path` for filesystem operations.
- Thin `cli/` layer — application logic lives in domain modules, not in CLI handlers.
- Harness drivers live in `harnesses/` and follow the `HarnessDriver` Protocol in `harnesses/base.py`.
- Avoid underscore-prefixed names for "private" symbols — the visual noise outweighs the benefit. Control the public API with `__all__` when a module needs to distinguish exported names from internal helpers.

## Domain vocabulary

Vocabulary comes from `CONTEXT.md`. Do not invent synonyms. If you introduce a genuinely new domain term, update `CONTEXT.md` first.
