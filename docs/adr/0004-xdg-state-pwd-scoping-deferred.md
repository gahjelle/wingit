# Runtime state lives in XDG user dirs; session pwd-scoping deferred

> **Status: superseded by [ADR-0007](0007-self-materializing-config-defaults-in-code.md)
> and [ADR-0008](0008-follow-up-not-named-sessions.md).**
> Kept for history. **Do not treat anything below as current, and do not inherit from it.**
> Every clause has been replaced: the config path is now `platformdirs.user_config_path`
> with a `WINGIT_CONFIG_FILE` override (ADR-0007), the session registry no longer exists
> (ADR-0008), and the single `WINGIT_STATE_DIR` override is **dead**. The pwd-scoping open
> question is **closed** — the pointer cache is keyed on (repo root, harness).
>
> One detail is **not** inherited from here: **where the pointer cache file lives** was
> never decided by either superseding ADR. It is owned by
> [T6](https://github.com/gahjelle/wingit/issues/41), narrowed to `user_cache_path` vs
> `user_state_path` — `platformdirs` itself is settled, so do not re-open it and do not
> hand-roll XDG.

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
