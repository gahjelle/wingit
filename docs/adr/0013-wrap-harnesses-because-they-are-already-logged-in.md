# Wrap harnesses because they are already logged in

wingit dispatches prompts by shelling out to an agent harness's own headless mode
(`claude -p`, `copilot -p`, `opencode run`, `pi -p`, `codex exec`) rather than calling
model APIs directly.

Supersedes [ADR-0001](0001-drive-harnesses-headless-not-model-apis.md). The **decision is
unchanged**; the **argument is not**. ADR-0001 justified wrapping on the grounds that it
gives wingit the harness's agentic capability — tools, file edits, model access — for
free. That is true, and it is no longer the load-bearing reason. Reconfirmed in
[issue #9](https://github.com/gahjelle/wingit/issues/9) during the
[replan](https://github.com/gahjelle/wingit/issues/8), on install-story grounds.

## Why the reasoning changed

ADR-0001 was written for a personal tool. The replan settled a different audience in
[issue #9](https://github.com/gahjelle/wingit/issues/9): **a real public tool**, designed
from the start to run on other people's machines. Against that audience the decisive
property of wrapping is not capability but **credentials**.

wingit's users are people who **already run a harness interactively**. Their harness is
already installed, already authenticated, already pointed at whatever subscription or
quota they pay for. So wingit can detect a harness on `PATH` and **never touch auth** —
no API key to obtain, no key to store, no key to leak, no second bill.

A direct model-API path would forfeit exactly that. It would make the front door
"first, get an API key," which is a materially worse install story than
`uv tool install wingit` plus a harness the user already has
([issue #26](https://github.com/gahjelle/wingit/issues/26)).

## The premise is load-bearing, and it has been tested

This is not a theoretical argument. [Issue #20](https://github.com/gahjelle/wingit/issues/20)
went looking for a hermetic mode and found that Claude Code's only suppression flag is
`--bare`, which **hard-requires `ANTHROPIC_API_KEY`**: `claude --bare -p` prints
`Not logged in`. A wingit feature built on that flag would have silently demanded the very
credential this ADR exists to avoid. Hermetic mode was rejected, and one of the three
reasons was that it **costs the install story** — that is this ADR's premise doing work.

## Decisions

1. **Shell out to harnesses' headless modes.** Never call a model API directly.
2. **Detect on `PATH`. Never touch auth** — no key acquisition, storage, prompting, or
   pass-through of harness credentials. Each harness has its own login flow and there is
   no shared credential across the five
   ([issue #11](https://github.com/gahjelle/wingit/issues/11)).
3. **A missing harness is a hard failure**, not a fallback to an API path. Config writes
   no file when no harness is present
   ([ADR-0007](0007-self-materializing-config-defaults-in-code.md)).
4. **The five-peer acceptance gate is manual, never CI.** Putting harness credentials in
   CI would contradict decision 2 ([issue #18](https://github.com/gahjelle/wingit/issues/18)).

## Consequences

- wingit gives up fine control over output format, and reclaims it by driving harnesses in
  structured mode internally — but only as far as each harness allows, which is why the
  seam negotiates capabilities rather than promising uniformity
  ([ADR-0005](0005-capability-negotiating-harness-seam.md)).
- wingit inherits the harness's whole project environment, including hooks, and cannot
  meaningfully opt out ([ADR-0011](0011-project-environment-inherited-whole.md)).
- wingit's latency is the harness's latency. Harness choice is the only real latency lever
  wingit has ([issue #14](https://github.com/gahjelle/wingit/issues/14)).

## Considered Options

- **Shell out to harnesses' headless modes** (chosen) — the user's harness is already
  authenticated, so wingit ships with no credential surface at all.
- **Call model APIs directly** — rejected. It makes wingit a raw-LLM CLI, forces
  reimplementation of agent loops the harnesses already provide (losing tool use for
  prompts like `a "count the words in the current diff"`), and replaces a zero-credential
  install story with an API-key one.
- **Wrap harnesses, with an API path as a fallback** — rejected in
  [issue #9](https://github.com/gahjelle/wingit/issues/9): a fallback that needs a key
  reintroduces the whole credential surface for the sake of a path that, by construction,
  the audience does not need. Preserved instead as a possible *future harness* — a minimal
  built-in agent behind the same adapter seam — rather than a special case in the core.
