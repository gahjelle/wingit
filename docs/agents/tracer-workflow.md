# Tracer workflow

How we take one tracer bullet from a sliced-but-unspecified issue to a merged PR, in a
consistent, repeatable way. The MVP is delivered as one chore plus ten tracers
([Epic #34](https://github.com/gahjelle/wingit/issues/34)); every tracer runs this same loop, in
**fresh context at each stage**.

Each tracer passes through three stages — **design**, **implement**, **clean up** — described
below. The guiding rule: *decisions become durable artifacts (issue comments, ADRs, `CONTEXT.md`),
and the plan that carries the work between sessions is disposable.*

## At a glance

1. **Design** — `/grill-with-docs <issue>` → a hand-off plan in `.scratch/`, decisions recorded on
   the issue, label flipped `needs-design` → `ready-for-agent`.
2. **Hand off** — `/handoff` to clear context between the (long) design session and the build.
3. **Implement** — `/implement` in a fresh session: worktree, test-first at the plan's seams,
   `/code-review`, an **active** (not draft) PR the maintainer squash-merges.
4. **Clean up** — after merge: remove the worktree and branch, refresh `main`, tick the epic, and
   move the plan to `.scratch/done/`.

---

## Stage 1 — Design (`/grill-with-docs`)

A tracer arrives sliced but not specified, carrying the `needs-design` label. The design session
turns it into something an implementer can build without re-deciding anything.

- **Run `/grill-with-docs <issue #>`.** It runs a `/grilling` session backed by `/domain-modeling`,
  walking the decision tree one question at a time.
- **The outcome is a plan in `.scratch/`** — `.scratch/<slug>-implementation-plan.md` — detailed
  enough to implement in a **separate session** with no further design work: every decision with
  its rationale, module-by-module specs, a test plan mapped to the issue checklist, and the
  explicitly-deferred list.
- **Record decisions on the issue.** Append a dated "Design session decisions" section to the
  issue body so the choices are visible on the tracker itself, not only in the (disposable) plan.
  The issue is the durable record; the plan is the working copy.

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

> This refines Epic #34's looser phrasing ("leaves ADRs as it goes"): the design session *decides*
> the ADR and drafts it; the implementation session *commits* it.

### Close the design session

- **Flip the label:** `needs-design` → `ready-for-agent` once the plan is complete. A tracer holds
  `needs-design` from creation until exactly this moment (see
  [triage-labels.md](./triage-labels.md)).

---

## Stage 2 — Hand off (`/handoff`)

Design sessions run long. **Run `/handoff` to clear context between design and build**, so the
implementation session starts fresh with the plan and the issue as its inputs, not a crowded
transcript.

---

## Stage 3 — Implement (`/implement`)

A fresh session picks up the `ready-for-agent` issue and its `.scratch/` plan.

- **Run `/implement`.** It works test-first (`/tdd`) at the **seams the plan already agreed**
  (`/tdd` requires the seams settled before a test is written — the design session settled them),
  and runs `/code-review` before the PR goes ready.
- **Work in a separate worktree.** Branch off `main` as `agent/<issue#>-<slug>` in its own worktree
  so several tracers can proceed in parallel. Runtime state (config, session cache) lives outside
  the repo in XDG dirs, redirectable via `WINGIT_STATE_DIR`
  ([ADR-0004](../adr/0004-xdg-state-pwd-scoping-deferred.md)), so worktrees never collide and
  nothing runtime is committed.
- **Commit the drafted ADRs / `CONTEXT.md` edits** from the plan on this branch, alongside the
  code, so everything is in the one PR.
- **Tick the issue checklist** as each item is done *and verified* (its test passes and
  `just check` is green) — never ahead of working code.
- **`just check` green is the definition of done** (see [quality-gates.md](./quality-gates.md)).
- **Open the PR active, not draft**, once the gate is green. Use a
  [Conventional Commit](https://www.conventionalcommits.org/) title (it becomes the squashed
  history entry) and include `Closes #<issue>`. Full procedure in
  [git-workflow.md](./git-workflow.md).
- **The maintainer squash-merges.** Agents never merge.

---

## Stage 4 — Clean up (after the squash-merge)

Once the PR is squashed and merged:

- **Remove the worktree and delete the local branch** (`git worktree remove …`, then delete
  `agent/<issue#>-<slug>`).
- **Refresh `main`** (`git checkout main && git pull`) so the merged work — including the ADR and
  glossary updates — is local.
- **Tick the tracer's box on [Epic #34](https://github.com/gahjelle/wingit/issues/34).**
- **Archive the plan:** move `.scratch/<slug>-implementation-plan.md` →
  `.scratch/done/<slug>-implementation-plan.md`. The plan is disposable — the decisions it drove
  already live on the issue and in the merged ADRs — so archiving it is bookkeeping, not
  preservation.

---

## Why it's shaped this way

- **Three fresh contexts.** Design, implement, and (implicitly) review each start clean, so no
  stage inherits the noise of the last.
- **The issue is the durable record; the plan is scratch.** Decisions are visible on the tracker
  and in ADRs; the `.scratch/` plan exists only to carry work between two sessions and is archived
  when spent.
- **One PR per tracer.** Because the design session commits nothing, the ADR, the glossary change,
  and the code arrive together and merge as a single squashed commit.
