# CalVer `YYYY.MM.PATCH`, single-sourced and re-locked by a bumpver hook

wingit versions on CalVer `YYYY.MM.PATCH` with a non-padded month, advanced by
[`bumpver`](https://github.com/mbarkhau/bumpver) through `just release`. The version is
single-sourced in `pyproject.toml`, the `v`-prefix lives only in the tag, and `uv.lock` is
regenerated into the same commit that bumps the version.

Decided in [issue #26](https://github.com/gahjelle/wingit/issues/26).

## This is an adoption, not a derivation

The scheme and mechanism are [garuff](https://github.com/gahjelle/garuff)'s, recorded there
as its ADR-0019. As with [ADR-0009](0009-gated-tag-triggered-release-workflow.md), adopting
it is the decision made here; the reasoning is restated rather than linked so it cannot
drift out from under this repo.

## Decisions

1. **CalVer `YYYY.MM.PATCH`, month non-padded** — July is `7`, not `07`. Releases here are
   date-driven, not API-contract-driven. SemVer would promise a compatibility contract
   wingit does not reason about, and `a`'s surface is a CLI whose breaking changes are
   better described in a changelog than encoded in a major number. Within a month `PATCH`
   counts releases; when the month rolls over, bumpver resets it to `0`.
2. **Single-sourced in `pyproject.toml`.** `[project].version` is the one copy, read by the
   `uv_build` backend. `bumpver update` rewrites the static string; `just release` wraps
   it, and bumpver then commits, tags, and pushes.
3. **The `v`-prefix lives only in the tag.** [ADR-0009](0009-gated-tag-triggered-release-workflow.md)
   triggers on a `v`-prefixed tag, but `[project].version` must stay a bare PEP 440 string.
   bumpver ties tag name to version string, so the `v` is carried in its own
   `version_pattern` (`vYYYY.MM.PATCH`) and `current_version`, while the `pyproject.toml`
   file pattern uses the `{pep440_version}` token, which normalises the `v` away. One
   config, both forms, no drift.
4. **The lockfile rides in the bump commit.** bumpver's `pre_commit_hook` runs a two-line
   `/bin/sh` script doing `uv lock` and `git add uv.lock`, so **uv itself** recomputes the
   lockfile into the bump commit and `pyproject.toml` and `uv.lock` stay consistent by
   construction.
5. **Seed `current_version = "v2026.6.0"`.** The first `just release` then produces
   **2026.7.0** — the intended first published version — through the ordinary
   month-rollover path, with no special-casing and no hand-written first version. The
   placeholder `version = "0.1.0"` currently in `pyproject.toml` is never published.

## Consequences

- Releasing is one command, `just release`; the pushed tag is the only trigger.
- A published version is permanent, so the seed is a one-shot decision — it must be set
  before the first release, not after.
- Version numbers carry no compatibility signal. Anything a user needs to know about a
  breaking change has to be written down, not inferred from the number.

## Considered Options

- **CalVer `YYYY.MM.PATCH` via bumpver** (chosen).
- **SemVer.** Rejected: the release cadence is date-driven, and a `MAJOR.MINOR.PATCH`
  contract would over-promise against a CLI surface that is still being sliced.
- **VCS / dynamic versioning**, deriving the version from the tag at build time. Rejected:
  bumpver's model is rewriting a static string, and moving to a dynamic backend is a larger
  change than this needs.
- **bumpver string-patching `uv.lock` via `file_patterns`.** Rejected: `uv.lock` has a
  `version` line *per package*, so a naive string match risks rewriting the wrong entry,
  and the lock format is uv's to own rather than ours to pattern-match. Letting `uv lock`
  regenerate it is correct by construction.
