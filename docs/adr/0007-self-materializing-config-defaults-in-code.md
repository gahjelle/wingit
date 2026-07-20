# Config materializes itself on first run; defaults live in code, not in the file

wingit is configured by a single user-global TOML file that `a` **creates itself** the
first time it runs. There is no `wingit init` to run first and no state in which the tool
refuses to work until you have read a config reference.

Every magic value lives as a **pydantic field default** in wingit's own source. The TOML
file holds only *true choices*. Visibility into the full configuration comes from
rendering the validated model, not from the file's contents.

Decided in [issue #16](https://github.com/gahjelle/wingit/issues/16). Partially supersedes
[ADR-0004](0004-xdg-state-pwd-scoping-deferred.md).

## Why not "no built-in defaults"

The previous plan required every setting to be present and pydantic-validated as complete,
with a load-bearing `wingit init` to write a starter file. That is a personal-tool design.
Against the public audience settled in [issue #9](https://github.com/gahjelle/wingit/issues/9)
— people who already run a harness interactively — a first run that fails validation is a
bad front door, and most of what the file would have to declare is discoverable anyway.

The opposite extreme, a maximal file holding every magic value for visibility, was also
rejected. Freezing values the user never chose turns each one into a silent pin: wingit
changes an internal constant in a later release and every existing install keeps the old
value, having never made a decision about it. The failure looks like a wingit bug.

Defaults-in-code with a rendered view gets both properties at once — the user can see
every effective value, but seeing a value and pinning a value are no longer the same act.

## Decisions

1. **First run materializes the file.** `a` finds no config, creates one, and reports on
   stderr what it wrote and where. No gated init step.
2. **Defaults are pydantic field defaults**, and evolve with wingit releases: per-harness
   default models, the shipped model-alias table, the harness preference ranking, the
   `--tools` posture default from [ADR-0006](0006-tool-posture-ladder.md), and `timeout`
   (defaulting to `None` — [issue #14](https://github.com/gahjelle/wingit/issues/14)
   decided a timeout exists with no default).
3. **The TOML holds only true choices.** First run writes the detected harness and the
   default model for each detected harness. Nothing else. A written value is never
   revised by wingit; model identity is something users track themselves, so a pinned
   model stays pinned.
4. **Layering is defaults → TOML → env**, melted by configaroo into one parsed config.
   Application code sees exactly two inputs: **the parsed configuration and the runtime
   flags.**
5. **No cwd-sensitive layer.** Repo-local config is not in the MVP. `a` is pipeable and
   run from anywhere, so behaviour keyed on the working directory is surprising; and a
   config file that is *content from a cloned repo* is a trust surface belonging to
   [issue #20](https://github.com/gahjelle/wingit/issues/20), not to config layering.
6. **Path via `platformdirs`** — `user_config_path("wingit") / "config.toml"`, so macOS
   gets a native location rather than a transplanted XDG one. The `_path` variant returns
   a `Path` directly, keeping the whole config path `pathlib`-native.
   `WINGIT_CONFIG_FILE` overrides with a direct file path, which is what tests and
   throwaway runs want.
7. **Detection is ranked, never interactive.** Preference order is Claude Code, Pi,
   Opencode, Copilot, Codex; the highest-ranked harness on `PATH` wins. First run can
   happen inside a pipe, so wingit never prompts. With no harness present, **no file is
   written** and `a` fails naming the five harnesses it knows — a config recording no
   harness would just be a broken file.
8. **Detection is frozen, with an explicit repair path.** The written harness is always
   honoured; wingit does not re-detect behind the user's back, because a silent harness
   switch is a ~5× latency swing ([issue #14](https://github.com/gahjelle/wingit/issues/14))
   in a tool people put in pipes. When the configured harness is no longer on `PATH`, `a`
   fails naming the harness, the file, and `repair-config`.
9. **Two config commands**: `show-config` renders the validated model via
   `configaroo.print_configuration`, defaults included; `repair-config` re-runs detection
   and rewrites the harness and model keys while preserving every other user choice. It
   is never automatic. There is no `reset-config` — deleting the file and running `a`
   regenerates it.

## What this supersedes in ADR-0004

ADR-0004's **XDG choice stands**, now expressed through `platformdirs`. Its **single
`WINGIT_STATE_DIR` override covering both config and the session registry does not**: one
variable named "state" that silently relocates config is a misnomer, and it couples config
to a registry design that is not settled.

ADR-0004's open question — whether sessions are pwd-scoped — **remains open**, along with
whether wingit owns session state at all. Both belong to
[issue #17](https://github.com/gahjelle/wingit/issues/17). This ADR takes the config path
only.

## Considered Options

- **Defaults in pydantic, minimal TOML, rendered view** (chosen).
- **Maximal TOML copied from a shipped template** — every magic value visible in the file.
  Rejected: freezing unchosen values pins wingit's internals per install.
- **Maximal TOML with unset keys written commented-out** — visible without pinning.
  Rejected as strictly worse than the rendered view: it still leaves stale comments after
  an upgrade, and needs two syntactic classes of key in one file.
- **No built-in defaults, load-bearing `wingit init`** (the previous plan). Rejected: a
  validation error is a bad front door for a public tool.
