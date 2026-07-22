# Tracer workflow

How we take one tracer bullet from a sliced-but-unspecified issue to a merged PR, in a
consistent, repeatable way. Work is delivered as epics, each sliced into tracer bullets; every
tracer runs this same loop.

Each tracer passes through three stages — **design**, **implement**, **clean up**. The guiding
rule: *decisions become durable artifacts (issue comments, ADRs, `CONTEXT.md`), and the plan that
carries the work between sessions is disposable.*

## At a glance

1. **Design** — `/grill-with-docs <issue>` to make the decisions, then `/handoff` to write the
   implementation plan into `.scratch/`. Decisions recorded on the issue; label flipped
   `needs-design` → `ready-for-agent`. The driver then clears context before implementation.
2. **Implement** — `/implement` in a fresh session: worktree, test-first at the plan's seams
   (it runs `/code-review` itself), an **active** (not draft) PR the maintainer squash-merges.
3. **Clean up** — after merge: remove the worktree and branch, refresh `main`, tick the epic, and
   move the plan to `.scratch/done/`.

---

## Stage 1 — Design (`/grill-with-docs`, then `/handoff`)

A tracer arrives sliced but not specified, carrying the `needs-design` label. The design session
turns it into something an implementer can build without re-deciding anything.

- **Run `/grill-with-docs <issue #>`.** It runs a `/grilling` session backed by `/domain-modeling`,
  walking the decision tree one question at a time.
- **Record decisions on the issue.** Append a dated "Design session decisions" section to the
  issue body so the choices are visible on the tracker itself, not only in the (disposable) plan.
  The issue is the durable record; the plan is the working copy.
- **Write the plan with `/handoff`.** When the grilling is complete, use `/handoff` to dump the
  session's decisions and context into an implementation plan at
  `.scratch/<date>-<slug>-implementation-plan.md`. `/handoff` **writes a file — it does not clear
  context.** The plan must be detailed enough to implement in a **separate session** with no
  further design work: every decision with its rationale, module-by-module specs, a test plan
  mapped to the issue checklist, and the explicitly-deferred list.

### The design session is repo-read-only except the plan

A design session **does not commit to the repository.** Its only write is the plan under
`.scratch/`, which is git-ignored. This means:

- **No worktree is needed for design** — nothing tracked is changed.
- **ADRs and `CONTEXT.md` changes are *drafted inside the plan*, not written to `docs/adr/` or
  `CONTEXT.md` directly.** The implementation session commits them on its branch, so the ADR, the
  glossary update, and the code all land in **one squash-merged PR** — nothing is stranded on
  `main`, and there is never a design-only commit to reconcile.
- The plan therefore carries: the full ADR draft text, the exact `CONTEXT.md` edits, and any
  citation updates (e.g. `AGENTS.md`) as tasks for the implementer.

> This refines the epic's looser phrasing ("leaves ADRs as it goes"): the design session *decides*
> the ADR and drafts it; the implementation session *commits* it.

### Close the design session

- **Flip the label:** `needs-design` → `ready-for-agent` once the plan is complete. A tracer holds
  `needs-design` from creation until exactly this moment (see
  [triage-labels.md](./triage-labels.md)).
- **The driver clears context before implementation.** Clearing context is the driver's (the
  human's) responsibility, not a skill invocation — `/handoff` wrote the plan, and a fresh session
  picks it up.

---

## Stage 2 — Implement (`/implement`)

A fresh session picks up the `ready-for-agent` issue and its `.scratch/` plan.

- **Run `/implement`.** It works test-first (`/tdd`) at the **seams the plan already agreed**
  (`/tdd` requires the seams settled before a test is written — the design session settled them),
  and it **invokes `/code-review` itself** — that is not a separate step to run by hand.
- **Work in a separate worktree.** Branch off `main` as `agent/<issue#>-<slug>` in its own worktree
  so several tracers can proceed in parallel. Runtime state (config, and the harness pointer cache)
  lives outside the repo in the user's platform config/state dirs
  ([ADR-0007](../adr/0007-self-materializing-config-defaults-in-code.md)), so worktrees never
  collide and nothing runtime is committed.
- **Commit the drafted ADRs / `CONTEXT.md` edits** from the plan on this branch, alongside the
  code, so everything is in the one PR.
- **Tick the issue checklist** as each item is done *and verified* (its test passes and
  `just check` is green) — never ahead of working code.
- **`just check` green is the definition of done** (see [quality-gates.md](./quality-gates.md)).
- **Open the PR active, not draft**, once the gate is green. Use a
  [Conventional Commit](https://www.conventionalcommits.org/) title (it becomes the squashed
  history entry) and include `Closes #<issue>`. The PR body and commits carry **no "Generated with
  Claude Code" footer and no session link** — AI collaboration is recorded solely by the commit
  `Co-Authored-By` trailer. Full procedure in [git-workflow.md](./git-workflow.md).
- **The maintainer squash-merges.** Agents never merge.

---

## Stage 3 — Clean up (after the squash-merge)

Once the PR is squashed and merged:

- **Remove the worktree and delete the local branch** (`git worktree remove …`, then delete
  `agent/<issue#>-<slug>`).
- **Refresh `main`** (`git checkout main && git pull`) so the merged work — including the ADR and
  glossary updates — is local.
- **Tick the tracer's box on its epic.**
- **Archive the plan:** move `.scratch/<date>-<slug>-implementation-plan.md` →
  `.scratch/done/<date>-<slug>-implementation-plan.md`. The plan is disposable — the decisions it
  drove already live on the issue and in the merged ADRs — so archiving it is bookkeeping, not
  preservation.

---

## Why it's shaped this way

- **Fresh context per session.** Design and implementation run as separate sessions; the driver
  clears context between them, so implementation never inherits the noise of a long design session.
- **The issue is the durable record; the plan is scratch.** Decisions are visible on the tracker
  and in ADRs; the `.scratch/` plan exists only to carry work between two sessions and is archived
  when spent.
- **One PR per tracer.** Because the design session commits nothing, the ADR, the glossary change,
  and the code arrive together and merge as a single squashed commit.
