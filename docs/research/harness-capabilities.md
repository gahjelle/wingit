# Harness capabilities: headless invocation across five agent CLIs

Research for [issue #10](https://github.com/gahjelle/wingit/issues/10). Establishes the fact base
for the `wingit` adapter seam ([ADR-0003](../adr/0003-fake-harness-driver-test-seam.md)).

**Date of research:** 2026-07-18. Every fact below is a snapshot; all five tools ship weekly or
faster. Re-verify before hardcoding anything.

## Verification status

This is the most important caveat in the document. Claims are only as good as their provenance.

| Harness | Installed locally? | Version | Evidence quality |
|---|---|---|---|
| **Claude Code** | Yes (`/home/gahjelle/.local/bin/claude`) | 2.1.214 | **Hands-on.** Real `--help`, real runs, observed event streams and exit codes. |
| **Opencode** | Yes (`/home/gahjelle/.opencode/bin/opencode`) | 1.17.18 | **Hands-on.** Real `--help`, real runs, observed event streams and exit codes. |
| **Codex** | No | docs/source at `rust-v0.144.5` (2026-07-16) | Docs + **Rust source**. Not executed. |
| **GitHub Copilot CLI** | No | docs current to 1.0.71 (2026-07-16) | Official docs + changelog only. Not executed. |
| **Pi** | No | npm `@earendil-works/pi-coding-agent` 0.80.10 | Official repo docs only. Not executed. |

For Codex, Copilot CLI, and Pi, **nothing below has been confirmed by running the binary.** Where
a claim rests on reading source rather than a documented contract, it is marked as such.

---

## Comparison table

| Dimension | Claude Code | Copilot CLI | Opencode | Pi | Codex |
|---|---|---|---|---|---|
| **Headless entry** | `claude -p "…"` | `copilot -p "…"` | `opencode run "…"` | `pi -p "…"` | `codex exec "…"` |
| **Stdin as prompt** | Yes (piped, 10 MB cap) | Yes — but **ignored if `-p` given** | Via args | Yes | Yes (`-` or appended as `<stdin>`) |
| **Structured format** | `--output-format json\|stream-json` | `--output-format json` (JSONL) | `--format json` (JSONL) | `--mode json` (JSONL) | `--json` (JSONL) |
| **Terminal result event** | **Yes** — `result` msg with `.result` | **Undocumented** | **No** | `agent_end` / `message_end` | `turn.completed` (+ `item.completed`) |
| **Answer cleanly separable** | **Yes** (`.result` field) | **Only via `-s` plain text** | **No — must reassemble** | Yes (block type) | **Yes** (`item.type=="agent_message"`) |
| **Answer to a file** | — | — | — | — | **`-o/--output-last-message FILE`** |
| **Schema-constrained output** | **`--json-schema`** | No | No | No | **`--output-schema FILE`** |
| **Session id format** | **UUID** | **UUID** | `ses_<base62>` | UUID (partial match ok) | UUID or thread name |
| **Pre-assign session id** | **Yes** (`--session-id <uuid>`) | **Yes** (`--session-id`, if valid UUID) | **No** | No (but `--session-dir`) | No |
| **Resume** | `-r/--resume`, `-c/--continue` | `-r/--resume`, `--continue` | `-s/--session`, `-c/--continue` | `-c/--continue`, `--session <path\|id>` | `codex exec resume [id\|--last]` |
| **Fork on resume** | `--fork-session` | — | `--fork` | `--fork` | — |
| **cwd-scoped sessions** | Yes | Yes | **Yes (verified)** | Yes (dir-organised) | Yes (`--all` disables) |
| **Model flag** | `--model` | `--model` | `-m provider/model` | `--model [provider/]id` | `-m/--model` |
| **Model namespace** | Anthropic only, aliases + full names | Flat multi-vendor slugs | **`provider/model`** | **`provider/id`** | OpenAI slugs (+ `--oss`) |
| **Reasoning effort** | `--effort low…max` | `--effort low…max` | `--variant` | `--thinking off…max` | `-c model_reasoning_effort=` |
| **Tool allow/deny** | `--allowedTools` / `--disallowedTools` / `--tools` | `--allow-tool` / `--deny-tool` / `--available-tools` | config `permission` map | `-t` / `-xt` / `-nt` (static only) | — (no tool-level flags) |
| **Headless auto-approve** | `--permission-mode` (6 values) | **`--allow-all-tools` (required)** | `--auto` | n/a — nothing to approve | approvals **unavailable** in `exec` |
| **OS sandbox** | No (external) | `--sandbox` (experimental) | No | **None at all** | **Yes — first-class 3-mode** |
| **Network control** | No | Toggle (host rules unreliable) | No | No | **Yes — off by default** |
| **Exit code on failure** | 1 (verified); 143 on SIGTERM | Undocumented, retrofitted | 1 (verified) | **Undocumented** | 1 (from source only) |

---

## The divergences that matter

These are the things an adapter seam has to absorb. Ordered by how much they cost.

### 1. "What is the answer?" is answered five different ways

This is the deepest split, and it is not a formatting difference — it is a difference in whether
the concept exists in the protocol at all.

- **Codex** is the cleanest. `item.completed` with `item.type == "agent_message"` gives you
  `item.text`. Reasoning is a *separate* item type (`reasoning`), tool activity is separate again
  (`command_execution`, `file_change`, `mcp_tool_call`). Nothing to disentangle. It additionally
  offers `--output-last-message FILE`, which writes just the answer — no stream parsing at all.
- **Claude Code** is nearly as clean but differently shaped: one terminal `result` message carries
  the whole answer in a `.result` string. Verified:
  `claude -p "Reply with exactly: OK" --output-format json | jq -r .result` → `OK`.
- **Pi** separates by *content block type* within a message (`text` vs `thinking` vs `toolCall`)
  and emits `agent_end` / `message_end` terminal events.
- **Opencode has no terminal result event and no consolidated answer field.** Verified: a run
  emits only `step_start` / `text` / `tool_use` / `step_finish` events. The answer must be
  reassembled by collecting `type == "text"` parts — and with tool use there are multiple steps,
  so a naive "first text part" is wrong. Observed on a tool-using run:

  ```
  step_start | tool_use (bash) | step_finish | step_start | text | step_finish
  ```

  The adapter must take text parts from the final step, or concatenate text parts emitted after
  the last `tool_use`. **This is real, load-bearing adapter work that the other four don't need.**
- **Copilot CLI is the worst case: the JSONL event schema is not documented at all.**
  `--output-format=json` exists ([added v0.0.422, 2026-03-05](https://github.com/github/copilot-cli/blob/main/changelog.md))
  and is described only as "outputs JSONL: one JSON object per line" — no event-type table, no
  designated final-answer event. It is not even mentioned on the
  [programmatic reference page](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference).
  The *documented* way to get a clean answer is `-s`/`--silent` on **plain text** output:
  `result=$(copilot -p '…' -s)`. So for Copilot the answer is untyped stdout text, not a field.

**Implication:** the seam cannot assume "parse JSON, read the answer field." It needs a
per-harness extraction strategy, and for Copilot the text path may be the *primary* path rather
than a fallback. Codex's `--output-last-message` is a genuinely different (file-based) mechanism
worth exploiting rather than normalising away.

### 2. Sandboxing ranges from first-class to entirely absent

The spread here is enormous, and it is the capability most likely to force a design decision.

- **Codex** has a real OS-level sandbox as a core concept: `-s/--sandbox` with exactly three
  values — `read-only` (the **default for `codex exec`**), `workspace-write`, `danger-full-access`.
  Enforced by Seatbelt on macOS, `bwrap` + `seccomp` on Linux, native sandbox on Windows.
  **Network is off by default** and must be explicitly enabled via
  `[sandbox_workspace_write] network_access = true`. ([agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security))
- **Copilot CLI** has `--sandbox` / `--no-sandbox`, but **only in experimental mode**
  (`--experimental`), added v1.0.70 (2026-07-09), public preview. Critically, GitHub's own docs
  warn that per-host network filtering is unreliable: *"Do not rely on host rules to enforce
  network isolation"* — macOS `allowedHosts` silently degrades to unrestricted outbound.
  ([local sandbox settings](https://docs.github.com/en/copilot/how-tos/cloud-and-local-sandboxes/configuring-local-sandbox-settings))
- **Claude Code** and **Opencode** have permission systems but **no OS sandbox and no network
  control**. They gate *which tool calls happen*, not what a spawned process can then do.
- **Pi has neither.** Its [security docs](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/security.md)
  say so explicitly: it runs "with the permissions of the user account that starts it", there is
  "no built-in sandbox", and project trust "is not a sandbox and it does not restrict what the
  model can ask tools to do." The only lever is static tool allowlisting (`-t`, `-xt`, `-nt`) —
  and `bash` is on by default, so the default posture is full user-level system access.

**Implication:** a uniform "sandboxed / not sandboxed" knob across all five is **not achievable**.
Codex can honour it natively; Pi can only honour it by not having the `bash` tool at all, or by
being containerised externally. If `wingit` wants to offer sandboxing as a cross-harness promise,
the honest options are (a) expose it as a per-harness capability flag that some adapters report as
unsupported, or (b) do the isolation itself (container/namespace) above the seam. Silently
degrading it would be dangerous.

### 3. The approval model inverts between harnesses

Not just different flags — different *defaults*, which is worse for a wrapper.

- **Copilot CLI** requires opt-in to work at all headlessly: `--allow-all-tools` is documented as
  *"Required when using the CLI programmatically."* It also needs `--no-ask-user` to stop the
  agent stalling on its `ask_user` tool — a failure mode unique to it. Its permission grammar is
  the most expressive of the five (`shell(git:*)`, `write(src/*.ts)`, `url(https://*.github.com)`)
  with **deny always beating allow, even under `--allow-all`.**
- **Codex** inverts it: `--ask-for-approval` **does not exist on `codex exec`**. The source
  comment reads *"Default to never ask for approvals in headless mode"*, and there is a hard error
  path, `"permissions approval is not supported in exec mode"`. Safety comes from the sandbox, not
  from approvals. So the adapter's "auto-approve" knob has **no Codex equivalent** — passing one
  would be an error.
- **Claude Code** has the richest mode vocabulary: `--permission-mode` accepts
  `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`. `dontAsk` is the
  documented CI-lockdown mode (denies anything not explicitly allowed).
- **Opencode** has one boolean, `--auto` ("auto-approve permissions that are not explicitly
  denied (dangerous!)"), plus a config-file `permission` map (`allow`/`ask`/`deny` per tool, with
  glob patterns like `"git *": "allow"`).
- **Pi** has no approval concept to configure. Note the trap: its `-a`/`--approve` flag governs
  only whether project-local settings/extensions load — **not** tool execution.

**Implication:** "auto-approve everything" maps to five distinct things: a required flag
(Copilot), a mode enum value (Claude Code), a boolean (Opencode), a no-op (Pi), and an *error*
(Codex).

### 4. Session identity is not uniform, and pre-assignment is a minority feature

- **Claude Code and Copilot CLI let you pre-assign the session ID** (`--session-id <uuid>`). For
  an orchestrator this is the clean handle: you mint the UUID, you already know it before the
  process starts, no output parsing needed. Copilot's docs note it creates a new session from your
  ID *"only when the value is a valid UUID."*
- **Opencode, Pi, and Codex do not.** You must read the ID back out of the event stream
  (Opencode: `sessionID` on every event; Codex: `thread.started.thread_id`; Pi: the `session`
  header event). For Opencode this is doubly awkward given there's no terminal event.
- **Opencode's IDs are not UUIDs.** Verified format: `ses_08b1ff42fffereb3p34ME1Csoi` — a `ses_`
  prefix over base62. Message and part IDs use `msg_` / `prt_`. Any adapter typing session IDs as
  UUID will break on Opencode.
- **Codex accepts a UUID *or* a human thread name** in the same positional argument, resolving
  UUIDs first if the string parses as one.
- **cwd-scoping is near-universal but stated differently.** Verified empirically for Opencode:
  `opencode session list` in the scratchpad showed three sessions; the same command in the repo
  directory showed **zero**. Claude Code's docs state session lookup "is scoped to the current
  project directory and its git worktrees". Copilot's `--continue` resumes "the most recent
  session in the current working directory, falling back to the globally most recent" — note the
  fallback, which the others don't have. Codex filters by cwd unless `--all`.

**Implication:** the adapter must treat the session ID as an opaque string, and must support both
"caller supplies the ID" and "harness reports the ID" acquisition patterns. Working directory is
part of a session's identity, not incidental.

### 5. Exit codes are the weakest contract across the board

Only two of five have a verified, reliable exit-code story, and none has a rich one.

- **Claude Code — verified hands-on.** Success → 0. Invalid model → 1. Unknown flag → 1.
  Documented: SIGTERM → **143**, and stdin over the 10 MB cap → non-zero.
  **Gotcha found by testing:** on an API failure the JSON envelope still says
  `"subtype":"success"` while `"is_error":true` and `"api_error_status":404`. Observed:

  ```json
  {"type":"result","subtype":"success","is_error":true,"api_error_status":404,
   "result":"There's an issue with the selected model (no-such-model-xyz)…"}
  ```

  **An adapter keying success off `subtype` will silently treat failures as successes.** Key off
  `is_error` (and the exit code).
- **Opencode — verified hands-on.** Success → 0. Invalid model → **1**, with a typed
  `{"type":"error","error":{"name":"UnknownError",…}}` event. So there is an error event type even
  though there is no success/result event type.
- **Codex** — no documented exit-code table anywhere in the docs corpus. From source
  ([`exec/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/exec/src/lib.rs)):
  0 on success, `std::process::exit(1)` on a fatal server-reported error, with an explicit source
  comment about "automation-friendly signaling". Binary 0/1, **but derived from source, not a
  stability guarantee.**
- **Copilot CLI — undocumented, and retrofitted piecemeal.** No exit-code table exists on
  docs.github.com. The changelog shows non-zero-on-failure being added case by case over nine
  months: v0.0.354 (2025-11-03) "Exit with nonzero code when `-p` mode fails due to LLM backend
  errors"; v1.0.71 (2026-07-16) non-zero when `--share` export fails; v1.0.71 non-zero "when a
  prompt is blocked before responding." **The pattern is itself the finding** — you cannot assume
  any given failure mode exits non-zero on your version. Notably, "agent gave up mid-task" appears
  nowhere as a failure condition.
- **Pi — undocumented.** Errors are designed to be read **in-band** (`stopReason: "error"` plus
  `errorMessage` on the message). Worse, there is a known headless hang:
  [issue #4303](https://github.com/earendil-works/pi/issues/4303) reports
  `pi -p --mode json "say hi" < /dev/null` emitting all events including `agent_end` and then
  **never exiting** (killed by `timeout` with 124); piping a real stdin (`echo "" | pi …`) exits 0.
  The issue is closed with labels `closed-because-bigrefactor` / `closed-because-weekend` — i.e.
  administratively, not by a verified fix. **UNVERIFIED whether this is fixed in 0.80.10.**

**Implication:** exit codes are necessary but nowhere near sufficient. The seam should derive
success primarily from the event stream and treat the exit code as corroboration. It should also
**always impose its own timeout**, because at least one harness has a documented non-terminating
headless path — and, independently, Opencode hung for 240s in this session (see below).

### 6. Capabilities some harnesses simply lack

| Capability | Present | Absent |
|---|---|---|
| Terminal result event | Claude Code, Codex, Pi | **Opencode**; Copilot (undocumented) |
| Documented event schema | Claude Code, Codex, Pi, Opencode (observed) | **Copilot CLI** |
| Pre-assigned session ID | Claude Code, Copilot | **Opencode, Pi, Codex** |
| OS-level sandbox | Codex, Copilot (experimental) | **Claude Code, Opencode, Pi** |
| Network egress control | Codex | **Claude Code, Opencode, Pi**; Copilot (unreliable) |
| Any permission system | Claude Code, Copilot, Opencode, Codex(sandbox) | **Pi** |
| Schema-constrained output | Claude Code (`--json-schema`), Codex (`--output-schema`) | **Copilot, Opencode, Pi** |
| Multi-provider models | Opencode, Pi | **Claude Code** (Anthropic only), Codex (OpenAI), Copilot (curated set) |
| Documented exit codes | Claude Code (partial) | **All four others** |

---

## Per-harness detail

### Claude Code — v2.1.214 (verified hands-on)

**Invocation.** `claude -p "<prompt>"` (`--print`). Reads stdin when piped (capped at 10 MB since
v2.1.128; over the cap it exits non-zero with a clear error). `--bare` skips hooks, LSP, plugin
sync, auto-memory, and CLAUDE.md discovery — the docs recommend it for scripted/SDK calls and note
it "will become the default for `-p` in a future release." **This matters for `wingit`:** without
`--bare`, a `-p` run inherits whatever is configured in the working directory and `~/.claude`, so
results are not reproducible across machines.

**Structured output.** `--output-format text|json|stream-json` (all `-p`-only).

- `json` returns one object; the answer is the `result` string. Verified full envelope includes
  `session_id`, `total_cost_usd`, `usage`, `modelUsage`, `num_turns`, `stop_reason`,
  `permission_denials`, `terminal_reason`.
- `stream-json` requires `--verbose`. Verified event types on a tool-using run:
  `system/init`, `system/thinking_tokens`, `rate_limit_event`, `assistant` (content blocks of
  type `thinking`, `tool_use`, `text`), `user` (with `tool_result`), and a terminal `result`.
  Docs add `system/api_retry` (with an `error` category enum), `system/plugin_install`, and hook
  lifecycle events under `--include-hook-events`.
- Subagent messages carry `parent_tool_use_id`; main-conversation messages carry `null`.
- `--json-schema` constrains the answer, delivered in a `structured_output` field.
- `--include-partial-messages` gives token-level `stream_event` deltas.

**Sessions.** `--session-id <uuid>` pre-assigns (must be a valid UUID). `-r/--resume [id]`,
`-c/--continue`, `--fork-session` (new ID when resuming), `-n/--name` for a display name,
`--no-session-persistence` for ephemeral runs. Lookup is scoped to the project directory and its
git worktrees.

**Model.** `--model` takes an alias (`opus`, `sonnet`, `haiku`, `fable`) or a full name
(`claude-fable-5`). Anthropic models only; third-party access is via Bedrock/Vertex/Foundry
credentials, not a provider-prefixed namespace. `--effort low|medium|high|xhigh|max`.
`--fallback-model` (comma-separated, `-p` only) retries on overload.

**Permissions.** `--permission-mode acceptEdits|auto|bypassPermissions|manual|dontAsk|plan`;
`--allowedTools` / `--disallowedTools` with rule syntax (`Bash(git diff *)` — the space before `*`
is significant); `--tools` restricts the built-in set entirely; `--dangerously-skip-permissions`.
`dontAsk` is the documented locked-down CI mode. No OS sandbox, no network control.
Note: `-p` **skips the workspace trust dialog**, so only run it in trusted directories.

**Exit codes.** Verified: 0 success, 1 on invalid model and on unknown flag. Documented: 143 on
SIGTERM (aborts the turn, kills the Bash process tree, runs `SessionEnd` hooks). See the
`subtype`/`is_error` gotcha in §5 above — it is the single most important trap for an adapter.

Sources: local `claude --help` (v2.1.214); [Run Claude Code programmatically](https://code.claude.com/docs/en/headless).

### Opencode — v1.17.18 (verified hands-on)

**Invocation.** `opencode run [message..]`. Also `opencode serve` (headless HTTP server) with
`opencode run --attach http://localhost:4096` to avoid per-call startup cost — worth noting, since
startup was slow in testing. `opencode acp` speaks Agent Client Protocol.

**Structured output.** `--format default|json`. JSONL. Verified event types:
`step_start`, `text`, `tool_use`, `step_finish`, `error`. Each event carries `sessionID`,
`timestamp`, and a `part` object (`part.type` is `step-start`, `text`, `tool`, `step-finish`).
`step_finish` carries `tokens` (with cache read/write breakdown) and `cost`.
**There is no terminal result event and no consolidated answer field** — see §1.

**Sessions.** `-s/--session <id>`, `-c/--continue`, `--fork`, `--title`.
`opencode session list|delete`, `opencode export [sessionID]` (JSON, with `--sanitize` to redact),
`opencode import`. IDs are `ses_`-prefixed base62, not UUIDs, and cannot be pre-assigned. Verified:
resume across invocations works and preserves context; `session list` is cwd-scoped.

**Model.** `-m/--model provider/model` — genuinely multi-provider. Verified locally: `mistral/…`,
`anthropic/…`, `opencode/…`, `openrouter/…` are all in `opencode models`. Credentials per provider
in `~/.local/share/opencode/auth.json`. `--variant` sets provider-specific reasoning effort
(`high`, `max`, `minimal`). `--agent` selects an agent profile.

**Permissions.** Config-driven `permission` map with `allow` / `ask` / `deny` per tool
(`read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`,
`websearch`, `external_directory`, `doom_loop`), glob patterns (`"git *": "allow"`,
`"rm *": "deny"`), and per-agent overrides. Most default to `allow`; `doom_loop` and
`external_directory` default to `ask`; reading `.env` defaults to `deny`. CLI knob is the single
`--auto` boolean. No OS sandbox, no network control.

**Exit codes.** Verified: 0 on success, 1 on invalid model (with a typed `error` event).

**⚠️ Reliability observation.** `opencode run --format json --model anthropic/claude-haiku-4-5
"Reply with exactly: OK"` **hung and was killed at 240s (exit 124) having produced zero bytes on
both stdout and stderr.** The same command against `opencode/big-pickle` returned in ~2s. Cause
not diagnosed — plausibly the OAuth-authenticated Anthropic provider path. Flagged because a
silent zero-output hang is the worst possible failure mode for a wrapper, and it argues strongly
for `wingit` imposing its own timeout on every harness.

Sources: local `opencode --help`, `opencode run --help`, `opencode session --help`, and observed
runs (v1.17.18); [CLI docs](https://opencode.ai/docs/cli/); [permissions docs](https://opencode.ai/docs/permissions/).

### Codex (OpenAI) — `rust-v0.144.5` (docs + source; NOT executed)

**Meta-finding:** the in-repo `docs/exec.md`, `docs/sandbox.md`, and `docs/config.md` are now
one-line stubs pointing at hosted docs; `developers.openai.com/codex/*` 308-redirects to
`learn.chatgpt.com`. The Rust source is the highest-trust artifact for flags and schemas.

**Invocation.** `codex exec [OPTIONS] [PROMPT]`, with exactly two subcommands (`resume`, `review`).
Three input modes: positional prompt; `codex exec -` (stdin *is* the prompt); or a prompt with
piped stdin, which is appended as a `<stdin>` block. Without `--json`, progress goes to **stderr**
and only the final agent message to **stdout** — so `codex exec "…" > out.md` already isolates the
answer. Other flags: `--ephemeral` (no session files), `--skip-git-repo-check`,
`--ignore-user-config`, `--output-schema FILE`, `-o/--output-last-message FILE`, `-C/--cd`,
`--add-dir`.

**⚠️ `--full-auto` is REMOVED.** It survives only as a hidden legacy trap emitting
"`--full-auto` is deprecated; use `--sandbox workspace-write` instead". Do not build on it.

**Structured output.** `--json` (alias `--experimental-json`; the alias-only status looks like
deprecation-in-progress). Schema is a closed Rust enum in
[`exec_events.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/exec/src/exec_events.rs):
`thread.started` (`{thread_id}`), `turn.started`, `turn.completed` (`{usage}`), `turn.failed`
(`{error:{message}}`), `item.started` / `item.updated` / `item.completed` (`{item}`), and a
top-level `error`. `ThreadItem` details are tagged `agent_message`, `reasoning`,
`command_execution`, `file_change`, `mcp_tool_call`, `collab_tool_call`, `web_search`, `todo_list`,
`error`. `agent_message` and `reasoning` are suppressed on `item.started` — emitted only on
completion.

**Sessions.** `codex exec resume <SESSION_ID|thread-name>` or `--last`; `--all` disables cwd
filtering (confirming cwd-scoped by default). Quirk: with `--last` and no explicit prompt, the
positional is reinterpreted as the prompt. Storage is **date-nested**, not flat:
`$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<conversation_id>.jsonl`.

**Model.** `-m/--model`; `-p/--profile`; `-c key=value` config overrides (value parsed as TOML,
dotted paths for nesting — e.g. `-c model_reasoning_effort="high"`); `--oss` with
`--local-provider lmstudio|ollama`. Namespace is plain OpenAI slugs, no vendor prefix.

**Permissions.** See §2 and §3 — three-mode OS sandbox, `read-only` default for `exec`, network
off by default, and **no approval flags in `exec` at all**. `--dangerously-bypass-approvals-and-sandbox`
(alias `--yolo`) for externally-sandboxed environments.

**Exit codes.** Undocumented; from source, binary 0/1. Distinguish failure *modes* from the
`--json` stream (`turn.failed.error.message`), not the exit code.

Sources: [openai/codex @ rust-v0.144.5](https://github.com/openai/codex) —
[`exec/src/cli.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/exec/src/cli.rs),
[`exec/src/exec_events.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/exec/src/exec_events.rs),
[`exec/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/exec/src/lib.rs),
[`utils/cli/src/shared_options.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/utils/cli/src/shared_options.rs),
[`rollout/src/recorder.rs`](https://github.com/openai/codex/blob/rust-v0.144.5/codex-rs/rollout/src/recorder.rs);
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
[agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security),
[config reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[models](https://learn.chatgpt.com/docs/models).

### GitHub Copilot CLI — docs current to v1.0.71 (docs only; NOT executed)

This is `copilot`, the agentic terminal tool — **not** `gh copilot` (the older suggest/explain
extension).

**Invocation.** `copilot -p PROMPT` / `--prompt=PROMPT` ("exits after completion"). Stdin piping
works (`echo "…" | copilot`) but **piped input is ignored if `-p` is also given** — a trap unique
to this harness. `-s/--silent` outputs only the agent response. `-C DIRECTORY` sets cwd.
`--autopilot` with `--max-autopilot-continues=COUNT` bounds self-continuation.
**Historic breaking change:** `--headless --stdio` (the old programmatic interface behind
`@github/copilot-sdk`) was removed without deprecation.
Auth precedence: `COPILOT_GITHUB_TOKEN` > `GH_TOKEN` > `GITHUB_TOKEN`; classic `ghp_` PATs are
**not** supported.

**Structured output.** `--output-format=text|json` (JSONL). **Schema undocumented** — see §1. Any
event names you see circulating (`assistant.message`, `result`, …) are **UNVERIFIED**; dump the
stream empirically before coding against them. `--share=PATH` / `--share-gist` export a Markdown
transcript post-hoc. `~/.copilot/session-state/` holds an `events.jsonl` whose schema is
explicitly not a public API ([open request to formalise it](https://github.com/github/copilot-cli/issues/3551)).
**Better-specified alternative:** `copilot --acp` starts an
[Agent Client Protocol server](https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server)
over stdio or TCP carrying NDJSON — a *specified external protocol* with a TS SDK. Public preview,
subject to change. Caveat: tool filtering and effort are fixed by whoever launches the server, not
negotiable per session.

**Sessions.** `-r/--resume[=VALUE]` accepts a session ID, **ID prefix, or session name** (exact,
case-insensitive). `--continue` resumes the most recent session in cwd, **falling back to the
globally most recent** — a fallback the other harnesses don't have, and a hazard for an
orchestrator. `--session-id ID` is exact-match and creates a new session from your value only if
it is a valid UUID. `-n/--name` names a session. `-w/--worktree` runs in an isolated git worktree
(experimental). Storage: `~/.copilot/session-state/` (or `$COPILOT_HOME`).

**Model.** `--model=MODEL`, `COPILOT_MODEL`, or `model` in `~/.copilot/settings.json`. Precedence:
custom agent → `--model` → env → settings → default. Namespace is **flat vendor-agnostic slugs**
with no provider prefix, drawn from a curated multi-vendor set — as documented at fetch time:
`claude-sonnet-4.6` (default), `gpt-5.4`, `claude-haiku-4.5`, `gpt-5.3-codex`,
`gemini-3.1-pro-preview`, `gemini-3.5-flash`, `mai-code-1-flash`, plus `--model=auto`.
⚠️ The [best-practices page](https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-best-practices)
is **stale** and lists an older set — trust the command reference, or `copilot help` at runtime.
Also `--effort low|medium|high|xhigh|max` and `--context default|long_context`.

**Permissions.** Two orthogonal axes. *Grants:* `--allow-all-tools` (**required for programmatic
use**), `--allow-all-paths`, `--allow-all-urls`, `--allow-all`/`--yolo`,
`--allow-tool`/`--deny-tool`, `--allow-url`/`--deny-url`, `--add-dir`, `--disallow-temp-dir`.
Pattern grammar is `Kind(argument)` with kinds `shell`, `write`, `read`, `url`, `memory`, and MCP
server names; `:*` matches command stem + space, so `shell(git:*)` matches `git push` but not
`gitea`. **Deny always beats allow, even under `--allow-all`.** Decisions persist to
`~/.copilot/permissions-config.json`, keyed by absolute path (git root for repos).
*Tool availability* (stronger — removes the tool from the model): `--available-tools`,
`--excluded-tools`. Headless hygiene: `--no-ask-user` disables the `ask_user` tool so the agent
can't stall. Enterprise lockdown via `permissions.disableBypassPermissionsMode` (settable by MDM
policy, unremovable) suppresses **all** allow-all flags — worth knowing, as it can make a
documented headless recipe fail on a managed machine. Sandbox: see §2.

Canonical documented headless recipe:
`copilot --autopilot --yolo --max-autopilot-continues 10 -p "PROMPT"`.

**Exit codes.** Undocumented — see §5.

Sources: [about Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli),
[run CLI programmatically](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically),
[command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference),
[programmatic reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference),
[config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference),
[autopilot](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/autopilot),
[changelog](https://github.com/github/copilot-cli/blob/main/changelog.md).

### Pi — `@earendil-works/pi-coding-agent` 0.80.10 (docs only; NOT executed)

**⚠️ Identity/ownership caveat.** The tool has been renamed and transferred:
`badlogic/pi-mono` → **`earendil-works/pi`**; npm `@mariozechner/pi-coding-agent` (0.73.1) →
**`@earendil-works/pi-coding-agent`** (0.80.10). Site pi.dev, "Earendil Inc. and Contributors",
MIT. Identified as the coding harness (ships `read`/`write`/`edit`/`bash` tools and a terminal
TUI) and distinguished from Inflection's Pi chatbot, which is not a CLI harness.
**UNVERIFIED:** whether the old npm scope is formally deprecated (npmjs.com returned 403).
Unrelated namesakes exist: `@vandeepunk/pi-coding-agent`, `Dicklesworthstone/pi_agent_rust`.
Version churn is rapid (0.73 → 0.80 in ~2 months) — **pin the version.**

**Invocation.** `pi -p/--print`; `--mode json` (JSONL events); `--mode rpc` (long-lived stdio RPC);
plus a TypeScript SDK. Stdin piping works. `@`-prefixed file args for multimodal
(`pi -p @screenshot.png "What's in this?"`). `--system-prompt` / `--append-system-prompt`;
`-nc/--no-context-files` disables AGENTS.md/CLAUDE.md pickup.

**Structured output.** Event types: `session` (header: version, id, timestamp, cwd),
`queue_update`, `agent_start`/`agent_end`, `turn_start`/`turn_end`,
`message_start`/`message_update`/`message_end`, `tool_execution_start`/`_update`/`_end`,
`compaction_start`/`_end`, `auto_retry_start`/`_end`. Answer separation is clean at two layers:
tool activity has dedicated events, and message `content[]` blocks are discriminated
(`text` / `thinking` / `toolCall`). Messages carry `stopReason`
(`stop`|`length`|`toolUse`|`error`|`aborted`), optional `errorMessage`, `usage`, `provider`,
`model`. Documented idiom: `pi --mode json "…" 2>/dev/null | jq -c 'select(.type=="message_end")'`
— note the docs discard stderr, i.e. treat it as noise.

**Sessions.** Unusually strong. `-c/--continue`, `-r/--resume` (interactive picker — avoid
headless), `--session <path|id>` (**accepts a partial UUID** or a file path), `--fork <path|id>`,
`--session-dir`, `--no-session`, `-n/--name`. Storage `~/.pi/agent/sessions/`, organised by
working directory, overridable via `PI_CODING_AGENT_SESSION_DIR`. Format is JSONL with
`id`/`parentId` forming a **branching tree** in one file, enabling fork/replay from any prior
point — the richest session model of the five. Docs advise passing an explicit session path/ID
rather than relying on `-c`/`-r` for orchestration.

**Model.** `--model <pattern>` supporting `provider/id` and an optional `:<thinking>` suffix;
`--provider`, `--api-key`, `--thinking off|minimal|low|medium|high|xhigh|max`, `--list-models`.
Anthropic, OpenAI, Google, DeepSeek, Mistral, Groq "and 20+ others"; catalogs auto-refresh.

**Permissions.** **None** — see §2. Only static tool allowlisting: `-t/--tools`,
`-xt/--exclude-tools`, `-nbt/--no-builtin-tools`, `-nt/--no-tools`. No per-call gating, no path
scoping on writes, no network policy. Isolation is delegated to external tooling (Gondolin Linux
micro-VM, plain Docker, OpenShell). **If `wingit` shells out to `pi` headless, it should be
containerised.**

**Exit codes.** Undocumented; plus the `< /dev/null` hang described in §5. Recommended handling:
always attach a real pipe to stdin (never `/dev/null`), always wrap in an external timeout, and
derive success from `stopReason` in the event stream.

**Doc maturity note:** better than expected for a young project (~30 doc files incl. json, rpc,
sdk, sessions, session-format, security, containerization). Specific gaps: exit codes, and whether
`-p` combined with `--mode json` is a formally supported pairing — issue #4303 shows people use
it, but `json.md` never documents the combination.

Sources: [earendil-works/pi](https://github.com/earendil-works/pi) —
[usage](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/usage.md),
[json](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/json.md),
[sessions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sessions.md),
[session-format](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/session-format.md),
[security](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/security.md),
[containerization](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/containerization.md);
[npm registry](https://registry.npmjs.org/@earendil-works/pi-coding-agent).

---

## Open questions for design

Not answered by this research; flagged because design decisions may rest on them.

1. **Does `wingit` promise sandboxing?** It cannot be delivered uniformly (§2). Either expose it
   as a capability that adapters may report unsupported, or implement isolation above the seam.
2. **Is Copilot CLI's JSONL usable at all?** Its schema is undocumented. Requires an empirical
   dump before an adapter can target it. Fallback is `-s` plain text; the principled alternative
   is ACP (`--acp`), which is a different integration shape entirely.
3. **Does the seam expose sessions, and with what identity type?** Opencode's non-UUID IDs and the
   three harnesses that can't pre-assign push toward "opaque string, harness-reported."
4. **Timeout ownership.** Given Pi's documented hang and the Opencode hang observed here, a
   `wingit`-level timeout looks non-optional.
5. **Reproducibility.** Claude Code's `--bare` (and Pi's `-nc`) exist because default headless runs
   inherit ambient local config. Should the seam force the hermetic variant by default?

## Facts to re-verify before relying on them

- All model name lists (all five churn fast; Copilot's own best-practices page is already stale).
- Codex `--experimental-json` alias status (looks like deprecation-in-progress).
- Codex exit codes (source-derived, not a documented contract).
- Copilot CLI exit codes and JSONL schema (undocumented; needs empirical testing).
- Pi issue #4303 hang (closed administratively, not by a verified fix).
- Opencode's hang with the Anthropic provider (observed once here; cause undiagnosed).
