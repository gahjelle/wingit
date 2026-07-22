# wingit

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues (`gahjelle/wingit`) via the `gh` CLI; external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Engineering

Each MVP tracer bullet runs one loop — **design (`/grill-with-docs`) → hand off (`/handoff`) → implement (`/implement`) → clean up** — in fresh context at each stage. Full procedure in `docs/agents/tracer-workflow.md`.

When implementing an issue: branch off `main` in a new worktree (`agent/<issue#>-<slug>`), work **test-first using the `tdd` skill** against a **fake harness** — never a real one (see [ADR-0003](docs/adr/0003-fake-harness-driver-test-seam.md)) — **tick the issue's checklist** as each item is done and verified, keep `just check` green, and open a PR that the maintainer squash-merges. Full procedure in `docs/agents/git-workflow.md`.

- **Tracer workflow (design → implement → clean up)** — `docs/agents/tracer-workflow.md`.
- **Git workflow & issue procedure** — `docs/agents/git-workflow.md`.
- **Code conventions** — `docs/agents/code-conventions.md`.
- **Quality gates** — `docs/agents/quality-gates.md`.
- **Testing** — `docs/agents/testing.md`.
