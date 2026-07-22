# One tag-triggered release workflow, gated by a reviewed PyPI Environment

wingit publishes to PyPI from GitHub Actions, from a single `release.yml` with three jobs —
`check → build → publish` — triggered only by a pushed version tag. Publishing uses PyPI
**trusted publishing**, so no long-lived credential exists anywhere. The human pause before
the irreversible upload is a GitHub Environment with a required reviewer, not an
in-workflow gate.

Decided in [issue #26](https://github.com/gahjelle/wingit/issues/26).

## This is an adoption, not a derivation

The shape above is [garuff](https://github.com/gahjelle/garuff)'s, recorded there as its
ADR-0018 and already in service. wingit adopts it wholesale, and *that adoption is the
decision this ADR records* — the alternatives below were weighed in garuff and are restated
here so a reader of this repo can see why `release.yml` looks the way it does without
cloning another project. wingit already shares garuff's `qa.yml`, so the two repos'
CI shapes stay recognisably one thing.

The rationale is repeated rather than linked deliberately. A cross-repo pointer is a
dangling dependency: garuff can revise its ADRs or move, and wingit's recorded reasoning
would silently change underneath it.

## Decisions

1. **The trigger is a pushed tag**, `push: tags: ['v[0-9]*']`. There is no
   `workflow_dispatch`: a release is always a version tag cut by `just release`
   (see [ADR-0010](0010-calver-via-bumpver.md)).
2. **The workflow re-verifies the tagged SHA.** A tag can sit on any commit, so the `check`
   job runs `just check` — the same gate every push runs — before anything is built.
   `build` `needs: check`; `publish` `needs: build`. CI cannot publish a commit the gates
   have not passed, even if someone tags an arbitrary one.
3. **The review pause is the `pypi` GitHub Environment.** The `publish` job declares
   `environment: pypi`, and that Environment carries a required-reviewer rule. GitHub
   blocks the job until the maintainer approves. The gate lives in repo settings, where
   there is nothing to maintain in the workflow file.
4. **Trusted publishing, no stored credential.** `pypa/gh-action-pypi-publish` with OIDC
   and its default PEP 740 attestations. Top-level `permissions: {}`; each job gets only
   what it needs, and `publish` gets only `id-token: write`. Every checkout sets
   `persist-credentials: false` and every `uses:` is SHA-pinned.
5. **No caching in the release path.** `setup-uv` runs with `enable-cache: false` so a
   cache poisoned by an untrusted run cannot influence a published artifact.

## The machinery lands early; the first publish lands last

[Issue #26](https://github.com/gahjelle/wingit/issues/26) split distribution along a risk
seam, and this ADR is the early half.

The workflow, the bumpver setup, and the two out-of-repo prerequisites are a **chore, not a
tracer bullet** — there is no user-visible behaviour here to slice. But they are not
deferred to the end either: the prerequisites are the part that can only be tested by
releasing, and discovering a trusted-publishing misconfiguration on the day you wanted to
ship is the failure this ordering avoids. Creating the PyPI **pending publisher** also
reserves the name `wingit`, which was unregistered when #26 was resolved, without
publishing anything.

The first `just release` is a separate matter and belongs at the **end** of the MVP:
nothing depends on it, and a half-built `a` should not be installable under its real name.

Two prerequisites therefore exist outside this repo, and until both exist no tag can
publish:

- a PyPI **pending publisher** for `wingit` — this repo, workflow `release.yml`,
  environment `pypi`;
- the GitHub **`pypi` Environment** with a required reviewer.

## Considered Options

- **One `release.yml`, three jobs, Environment-gated** (chosen).
- **Split build and publish into two workflows** chained by `workflow_run`, as the
  [source article](https://snarky.ca/how-to-publish-to-pypi-using-github-actions-securely/)
  offers as an option. Rejected: `workflow_run` runs the **default-branch** copy of the
  downstream workflow rather than the tagged one, artifact passing between workflows is
  manual, and the review gate still has to be a GitHub Environment either way. The split
  adds moving parts without removing the thing they would justify.
- **A long-lived PyPI API token in repo secrets.** Rejected: trusted publishing removes the
  credential entirely, and a token in a repo that runs agent-authored workflows is a
  standing liability.
- **Publishing on every push to `main`.** Rejected: it makes every merge irreversible on
  PyPI and leaves no human pause at all.
