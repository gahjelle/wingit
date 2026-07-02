# Runtime state lives in XDG user dirs; session pwd-scoping deferred

wingit's runtime state — the configaroo config file and the session registry (session
name → harness-native UUID) — lives in XDG user directories (`$XDG_CONFIG_HOME/wingit`,
`$XDG_STATE_HOME/wingit`), redirectable via a single `WINGIT_STATE_DIR` override so tests
point it at `tmp_path`. State is global to the user, not per-repo, which fits a pipeable
CLI you run from anywhere and avoids the parallel-worktree collision a per-repo directory
would cause.

## Open question

Whether sessions should be scoped to the working directory is **not yet decided**. A
harness's own sessions are keyed by project dir (e.g. Claude Code resumes are cwd-bound),
which may argue for pwd-scoping the registry too. Resolving this later may relocate or
restructure the registry. Recorded here so the current global layout is understood as
provisional, not final.

## Considered Options

- **XDG user dirs, env-overridable** (chosen) — global, no worktree collision, tests
  redirect via `WINGIT_STATE_DIR` to `tmp_path`.
- **Per-repo `.wingit/` directory** (gitignored) — mirrors a per-project data dir, but
  sessions wouldn't follow the user across directories and every clone starts empty.
  Rejected as the starting point; may be revisited if sessions become pwd-scoped.
