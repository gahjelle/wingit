# The project environment is inherited whole

`a` runs the harness in the user's own environment, in the user's own working directory, with
the project's configuration fully in effect — instruction files, MCP servers, skills, custom
agents, and hooks alike. There is no hermetic mode, no suppression flag, and no wingit-owned
trust layer. The child process environment is passed through untouched, with one narrow
exception: variables that would silently override a tool rung `a` set explicitly.

Decided in [issue #20](https://github.com/gahjelle/wingit/issues/20). Narrows the scope of
[ADR-0006](0006-tool-posture-ladder.md) — see [What the ladder does not
cover](#what-the-ladder-does-not-cover).

## Decisions

1. **Inheritance is the feature, not the compromise.** `a` runs in the context of the current
   project. A repo that has taught its harness how to be useful — conventions in `AGENTS.md`,
   an MCP server that knows the deployment, a skill that knows the schema — teaches `a` the
   same things for free. The cost is that `a` behaves differently in every directory, and that
   cost is accepted deliberately.

2. **No hermetic mode.** Not as a default, not as a flag, not as a config key. Three
   independent reasons, any one sufficient:

   - **It cannot be delivered.** Opencode and Codex have no way to suppress `AGENTS.md`
     discovery at all. Verified: both answer a question whose only source is a planted
     `AGENTS.md`.
   - **It would cost the install story.** Claude Code's only suppression flag is `--bare`,
     which hard-requires `ANTHROPIC_API_KEY` and never reads OAuth or the keychain.
     `claude --bare -p` prints `Not logged in · Please run /login` for a subscription user —
     forfeiting the "your harness is already logged in" premise that
     [ADR-0001](0001-drive-harnesses-headless-not-model-apis.md) rests on.
   - **It would be a lie where it does work.** Suppression stops auto-*injection*, not
     *discovery*. At the default rung of `write` the agent simply reads the file itself.
     Verified on Pi: `-nt` (tools off, context on) answers from the planted file; `-nc -nt`
     answers `UNKNOWN`; `-nc` alone — context suppressed, tools live — answers from the file
     again, having read it through the front door. Hermeticity is only real at rung `none`.

3. **Executable project config is inherited too.** Hooks, skills, custom agents, and
   project-scoped MCP servers all run. Splitting the bundle into declarative knowledge and
   executable capability was considered and rejected: the line is not where the value is, and
   a project's MCP server is often the single most useful thing in the directory.

4. **No wingit trust layer.** `a` does not consult, maintain, or synthesise a record of which
   directories are trusted. Claude Code keeps one (`~/.claude.json`, `hasTrustDialogAccepted`
   per directory); wingit does not read it. Parsing one harness's private, undocumented schema
   — with no equivalent on the other four — is exactly the per-harness special-casing
   [ADR-0005](0005-capability-negotiating-harness-seam.md) exists to avoid, and it would break
   whenever that file is reshaped.

5. **The working directory is wingit's own, set on the child process.** Four of five harnesses
   offer a directory flag (`codex -C`, `copilot -C`, `opencode --dir`) and Pi offers none, so
   `a` uses none of them: it sets the child's `cwd` directly. Uniform across all five, no
   capability negotiation required. This joins `stdin=DEVNULL` (ADR-0005 §5) in the driver's
   process-spawn contract.

6. **Environment passthrough, minus rung-override variables.** The parent environment is passed
   through unmodified — API keys, proxies, provider settings, `PI_OFFLINE`. Deferring to
   ambient configuration is the same principle as deferring to project configuration.

   The exception is variables that would override a rung `a` set explicitly. Copilot documents
   `--allow-all-tools` as `(env: COPILOT_ALLOW_ALL)`, so a user with that exported in a shell
   profile could have `a --tools read` quietly run at `write`. That is not wingit deferring to
   the harness; it is ambient state voiding an instruction wingit just issued, and ADR-0006
   calls the ladder wingit's one real safety contract. Each driver strips the variables that
   contradict its own rung flags — **only** those, kept deliberately narrow.

   Not yet verified: whether Copilot's flag beats its environment variable. The denylist is
   correct either way, but the precedence should be established when the driver is built.

## What the ladder does not cover

ADR-0006 presents the tool posture ladder as wingit's safety contract, and rung `none` reads as
"the agent can do nothing." That promise is narrower than it appears, and this is the scope
correction.

**The ladder governs what the model may do. It does not govern what the project does unasked.**

Verified: a `UserPromptSubmit` hook in a project's `.claude/settings.json` executed arbitrary
shell under `claude -p "Say OK." --disallowed-tools=Bash` — with shell explicitly denied, with
the model never electing to run anything, and in a directory that had never been trusted.
Hooks are not tools, so no rung constrains them.

Claude Code's own `-p` help states why no prompt appeared:

> The workspace trust dialog is skipped when Claude is run in non-interactive mode (via `-p`,
> or when stdout is not a TTY, e.g. piped or redirected output). Only use this in directories
> you trust.

`a` is always `-p`. So **`a` is strictly more permissive than the harness it wraps**: running
`claude` by hand in a freshly cloned repo asks first, and `a` does not. Combined with decision
4, the mitigation is documentation, and the documentation must be blunt — `a` in an untrusted
clone can execute that clone's code before the model does anything at all, at every rung
including `none`.

This does not reverse any decision in ADR-0006. The ladder still means what it says about tool
use; it simply never covered this door.

## Consequences

- **`a` is not a sandbox and must never be described as one.** ADR-0006 already forbids calling
  rung `read` "sandboxed". This extends that: no rung makes `a` safe to point at code you do
  not trust.
- **The README carries a prominent trust warning.** The bypass is real, wingit-specific in its
  reach, and invisible unless stated.
- **Behaviour is directory-dependent by design.** Bug reports must therefore carry the project
  configuration in effect; "works on my machine" is the expected failure mode, and
  `show-config` ([ADR-0007](0007-self-materializing-config-defaults-in-code.md)) does not
  capture any of it.
- **Drivers own a small environment denylist** that will drift as harnesses add variables. The
  failure mode is missing one, not breaking a working setup.
- **Pi passes `--approve` (`-a`) for parity** on project-local extensions — `--approve` governs
  executable project-local files, not context files (`AGENTS.md` loads without it, verified).
  Settled when the Pi driver was built ([issue #37](https://github.com/gahjelle/wingit/issues/37),
  T2): the Pi driver passes `-a`, because *not* passing it would make Pi the one harness that
  silently suppresses part of the project environment — precisely the split this ADR rejects. It
  is the same choice as decision 3 (executable project config is inherited too) and the same
  cost: `a` on Pi trusts and runs project-local code, mitigated only by the trust warning above.

## Considered Options

- **Inherit everything** (chosen) — the only promise deliverable on all five harnesses, and the
  one the maintainer wants.
- **Hermetic by default** — rejected: undeliverable on two harnesses, breaks login on a third,
  and unenforceable at the default rung on the rest.
- **Split the bundle — inherit instruction files, suppress hooks and MCP** — rejected: discards
  the most valuable part of a configured project, and would force Opencode and Codex to refuse
  outright under ADR-0006 §5 since neither can suppress.
- **Honour the harness's own trust store** — rejected: one harness's private schema, no
  equivalent elsewhere, fragile against upstream change.
- **Warn on stderr in untrusted directories** — rejected: requires wingit's first mutable
  per-directory state, cutting against ADR-0007's "no cwd-sensitive layer", to buy a warning
  that is ignored after the second time.
- **Full environment passthrough with no exceptions** — rejected only for rung-override
  variables: a safety contract that ambient shell state can silently void is not a contract.
