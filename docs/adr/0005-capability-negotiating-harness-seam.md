# The harness seam negotiates capabilities; it does not promise uniformity

wingit drives every harness through one `HarnessDriver` interface — build the argv,
consume stdout line by line, finish — but the interface does **not** promise that every
harness behaves the same. Each driver additionally *declares* what its harness can do,
and wingit adapts to the declaration rather than reducing every harness to the lowest
common denominator.

Validated against all five harnesses (Claude Code, Opencode, Copilot CLI, Codex, Pi) with
a throwaway prototype driven by recorded output from the real binaries — branch
`prototype/adapter-seam`, [issue #13](https://github.com/gahjelle/wingit/issues/13). The
three-method interface absorbed all five with **no per-harness special cases in the
core**: every divergence stayed inside its adapter.

## Why uniformity was not available

The prototype set out to test whether one interface fits five harnesses. It does — but
the *output contract* those harnesses can honour differs irreconcilably:

- **Streaming is not universal.** Copilot and Pi emit token-level deltas; Claude Code
  emits whole messages; **Opencode and Codex cannot stream a final answer at all** — the
  answer is only knowable at EOF (Opencode has no terminal answer event and must be
  reassembled from the last step's text parts; Codex's `agent_message` arrives complete
  at the end).
- **Streaming and "final prose only" are mutually exclusive.** On a tool-using prompt,
  Claude Code's streamed text was `"I'll look at the current directory.3"` while its
  own `.result` was `"3"`. The preamble is real model prose emitted before a tool call,
  and nothing can identify it as preamble until the run ends.

So [issue #12](https://github.com/gahjelle/wingit/issues/12)'s "the answer is final
prose, streamed always" cannot hold. **Streamed-always is superseded**: streaming is a
declared capability, not a promise.

## Decisions

1. **The interface is `argv` / `feed` / `finish`, plus a declared capability set.**
2. **Streaming is static per harness, chosen conservatively.** A harness streams only if
   its stream is known to equal its final answer. Copilot and Pi stream; Claude Code does
   **not** (it might diverge, and emitted bytes cannot be recalled); Opencode and Codex
   cannot. The condition is per-*run*, not per-harness — Claude Code agreed on a
   tool-free prompt and diverged on a tool-using one — and the decision must be made
   before the run, so the conservative static answer is the only sound one.
3. **Exit code is the primary failure signal**, uniformly for all five; non-zero means
   failure. In-band signals *enrich* the message where they exist (Claude Code's
   `is_error`, Opencode's `error` event, Codex's `turn.failed`); harness stderr is the
   fallback. Copilot and Pi emit **nothing** in-band on failure, so no in-band-primary
   rule could have worked.
4. **Missing capabilities degrade silently for output, and refuse for safety.**
   Output-shaped gaps (streaming, separable reasoning) degrade quietly — the worst case
   is a less pleasant answer. Safety-shaped gaps do not: if the user asks to be
   sandboxed and the harness cannot, `a` errors rather than running unsandboxed. Pi has
   no sandbox whatsoever (its own docs say project trust "is not a sandbox", with bash
   on by default), so silent degradation there would run a tool-wielding agent unguarded.
5. **Closing stdin is part of the driver contract.** Spawned with an inherited stdin, Pi
   blocks forever — zero bytes on both streams, no exit. Codex announces
   `Reading additional input from stdin...` for the same reason. This reproduced as a
   180s timeout across all three Pi scenarios and vanished with `stdin=DEVNULL`. A
   silent, infinite, zero-output hang is the worst failure mode a wrapper can have, so
   this is contract, not incidental subprocess hygiene.

## Consequences

- The lowest common denominator — a final answer on stdout plus a trustworthy exit code —
  is what every harness delivers, and it is enough for both jobs in
  [issue #9](https://github.com/gahjelle/wingit/issues/9) (transform and ask).
- Capability declarations must be kept honest as harnesses churn. Copilot's `assistant.reasoning`
  events, for instance, carry empty content (the reasoning is an opaque blob) — a
  capability present in the schema and absent in reality.
- The `is_error` trap is load-bearing: Claude Code reports `"subtype":"success"` on a
  failed run. Exit-code-primary sidesteps it, but any adapter reading the stream must
  not key off `subtype`.
- Test the seam against the fake driver ([ADR-0003](0003-fake-harness-driver-test-seam.md));
  the recorded fixtures on `prototype/adapter-seam` are the reference for what real
  harness output looks like.

## Considered Options

- **One interface plus declared capabilities** (chosen) — fits all five, keeps divergence
  in the adapters, lets wingit use a harness's strengths.
- **Uniform interface, lowest common denominator** — rejected: would forfeit streaming
  everywhere because two harnesses cannot stream, and forfeit Codex's real OS sandbox
  because three harnesses lack one.
- **Bespoke per-harness code paths, no shared seam** — rejected: the prototype showed the
  shared interface holding across all five with the core untouched, so the seam earns its
  place.
