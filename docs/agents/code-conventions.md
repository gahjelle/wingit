# Code conventions

## Environment

- Python 3.14, managed by **uv**.
- Install deps: `uv sync`. Run tools: `uv run <tool>`.
- Source layout: `src/wingit/` for application code, `src/tools/` for repo dev tooling (e.g. the convention linter), `tests/` for tests.

## Package layout

wingit follows a thin-CLI split (mirroring the structure that worked well upstream):

- `cli/` — thin layer: argument parsing and dispatch only, no domain logic.
- `harnesses/` — one driver per harness. `harnesses/base.py` defines the `HarnessDriver` Protocol; real drivers (e.g. `harnesses/claude.py`) build the argv and run the subprocess; `harnesses/fake.py` is the injected test seam (see [testing.md](./testing.md) and [ADR-0003](../adr/0003-fake-harness-driver-test-seam.md)).
- `schemas/` — typed domain models on the project's `FrozenModel`/`StrictModel` bases (see WNG002).
- `console.py` — the output contract: the **Answer** goes to stdout, **Reasoning** to stderr (see `CONTEXT.md`).
- `sessions.py` — the session registry mapping session name → harness-native UUID.
- `config/` — configuration via **configaroo**.

These modules are created test-first as real work lands; this describes the intended shape, not a scaffold to fill in upfront.

## Linting and formatting

- **ruff** with `select = ["ALL"]` and ignores `COM812`, `D203`, `D213`, `PLR0913` (the last superseded by WNG009).
- Per-file test ignores: `S101`, `PLR2004`, `SLF001`, `INP001`.
- Every public module, class, and function **must have a docstring** (ruff `D` rules enforce this). Functions and methods go further — *every* one needs at least a one-line docstring, including `_`-prefixed and nested functions that ruff's `D` rules leave alone (enforced by WNG013 below).
- Full **type annotations** are required on all public APIs (ruff `ANN` rules enforce this).
- Never blanket-ignore the linter with `# noqa` — fix the issue or use a targeted `# noqa: CODE` with a comment explaining why.
- For intentional Unicode characters that trigger RUF001 (ambiguous characters), use `\N{name}` escapes (e.g., `\N{EN DASH}`) instead of the literal character or `\u` escapes. This is self-documenting and avoids the noqa entirely.

## Repo conventions (`repolint`)

Some conventions can't be expressed in ruff or ty, so they live in a small
in-repo linter, `src/tools/repolint.py` (the `tools` package sits beside
`wingit` under `src/` so it imports without any path juggling), wired into
`just check` (the `conventions` gate). It runs over `src/` and `tests/` and
reports `WNG` codes. Run it directly with `uv run python -m tools.repolint
[paths...]`; `--fix` applies the safe textual fixes (WNG001 and WNG004). Each
rule and how to satisfy it:

- **WNG001 — no `from __future__ import annotations`.** Python 3.14 evaluates
  annotations lazily (PEP 649), so the import is dead weight. Delete it; quote
  any annotation that genuinely needs deferring, or guard the import under
  `if TYPE_CHECKING:`.
- **WNG002 — Pydantic models inherit `FrozenModel`/`StrictModel`, never `BaseModel` directly.**
  These are thin project bases (`wingit.schemas`) — `BaseModel` subclasses that
  forbid extra fields — and are the only classes allowed to subclass `BaseModel`.
  Inherit `FrozenModel` for immutable models, `StrictModel` for mutable ones.
- **WNG003 — `Protocol` methods omit the `...` body.** The docstring is body
  enough; drop the trailing `...`.
- **WNG004 — docstrings use single backticks, never double.** Write `` `code` ``,
  not double-backtick code (the linter's `--fix` collapses these automatically).
- **WNG005 — homogeneous sequences use `list[T]`, not `tuple[T, ...]`.**
- **WNG006 — return `Self`, never a string forward-ref to the enclosing class.**
  Import `Self` from `typing` and annotate `-> Self` instead of `-> "Thing"`.
- **WNG007 — no possessive `my` prefix in code or docs.** An identifier or token
  beginning with `my` followed by `_` or `-`, or `My` followed by an uppercase
  letter, models bad naming and leaks into examples shown to users. Pick a name
  that describes the thing instead. Checked as text across `.py` and `.md` files.
- **WNG008 — ruff-exempt modules stay at runtime, not in `TYPE_CHECKING`.**
  `pathlib`, `datetime`, `typing`, and `wingit.cli` are listed in
  `[tool.ruff.lint.flake8-type-checking] exempt-modules` in `pyproject.toml`, so
  ruff will never move them into a `TYPE_CHECKING` block. Keep their imports at
  module top level; do not nest them under `if TYPE_CHECKING:`.
- **WNG009 — at most 1 positional parameter.** Functions with many positional
  args are hard to call correctly. Beyond 1, make parameters keyword-only
  (after a bare `*` separator). `self`/`cls` in methods don't count toward
  the limit.
- **WNG010 — no duplicate numeric prefixes in `docs/adr/`.** Two ADR files must
  not share the same `NNNN-` prefix. Parallel branches each adding "the next"
  ADR collide on a number; this catches it at `just check` time, before merge.
  Renumber one of the colliders so every ADR prefix is unique.
- **WNG011 — ADR numbers are consecutive from `0001`.** The prefixes in
  `docs/adr/` must form `0001, 0002, …, N` with no gaps and no zero. A gap
  suggests a deleted or missing ADR; a non-1-based start suggests a truncation.
  Both are drift from the sequential convention in [domain.md](./domain.md).
  Unlike the other rules, WNG010/WNG011 scan the `docs/adr/` directory rather
  than the files passed on the command line.
- **WNG012 — `@dataclass` must pass `kw_only=True`.** Stdlib dataclasses
  otherwise accept fields positionally, so a multi-field value object gets
  built as `Thing(a, b, c, …)` — the same hard-to-read positional soup WNG009
  guards against at the definition. Making the dataclass `kw_only` forces every
  call site to name its fields, and `ty` flags any positional construction for
  free. (Pydantic `FrozenModel`/`StrictModel` already reject positional args,
  so WNG002's models need nothing extra; this rule covers the stdlib
  `@dataclass` that WNG002 doesn't.)
- **WNG013 — every function/method has a docstring.** At least a one-line
  docstring on *every* `def`/`async def`, including `_`-prefixed helpers and
  nested functions. ruff's pydocstyle `D` rules only require docstrings on
  *public* names, so private and nested functions slip through; WNG013 closes
  that gap. The name plus a behavioral one-liner keeps even tiny helpers
  self-explanatory.

## Style

- Prefer `pathlib` over `os.path` for filesystem operations.
- Thin `cli/` layer — application logic lives in domain modules, not in CLI handlers.
- Harness drivers live in `harnesses/` and follow the `HarnessDriver` Protocol in `harnesses/base.py`.
- Avoid underscore-prefixed names for "private" symbols — the visual noise outweighs the benefit. Control the public API with `__all__` when a module needs to distinguish exported names from internal helpers.

## Domain vocabulary

Vocabulary comes from `CONTEXT.md`. Do not invent synonyms. If you introduce a genuinely new domain term, update `CONTEXT.md` first.
