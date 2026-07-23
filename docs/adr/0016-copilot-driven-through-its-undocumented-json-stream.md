# Copilot is driven through its undocumented JSON stream, not its documented text path

Copilot CLI offers two headless output shapes: a documented plain-text path (`-s`) and an
**undocumented** JSONL event stream (`--output-format json`). The Copilot driver uses the JSON
stream, accepting the risk of depending on an unspecified format because it is the only path that
carries the token deltas the harness's declared `STREAMS` capability rests on.

Decided in [issue #37](https://github.com/gahjelle/wingit/issues/37) (T2), when all five drivers
first declare their capabilities ([ADR-0005](0005-capability-negotiating-harness-seam.md)).
Copilot and Pi are the only two harnesses that stream a trustworthy answer, and for Copilot the
deltas exist only on the JSON path.

## Decisions

1. **Parse the JSONL event stream.** `assistant.message_delta` events carry token-level deltas;
   the last non-empty `assistant.message` carries the complete answer. T2 buffers to the final
   answer (it does not yet stream), but the stream is what makes `STREAMS = true` honest for
   Copilot and what T7 will render live. Choosing the text path would contradict the capability
   grid and force a driver-and-fixture rewrite at T7.

2. **The undocumented-format risk is retired live, not on faith.** `just live-check` exercises the
   real Copilot binary; if the event shape drifts, the recorded fixtures
   ([ADR-0014](0014-fake-the-io-boundary-not-the-driver.md)) are the contract and the failure is
   loud. This is the same posture every driver takes toward its harness's output.

3. **Copilot declares no separable reasoning.** Its `assistant.reasoning` events carry empty
   content — the reasoning is an opaque encrypted blob — so `SHOWS_REASONING = false`. This is a
   real absence, not a parsing gap; the JSON path does not change it.

4. **Failure detection stays exit-code-primary.** A failed Copilot run emits *nothing* on the JSON
   stream — no result event, no error event (ADR-0005 §3). The driver therefore yields no in-band
   `Failed`; the core fails on the non-zero exit code and takes the reason from captured stderr.

## Consequences

- The Copilot fixtures must track the JSON stream, and that stream may change without notice. The
  failure mode is a loud fixture/live-check mismatch, not silent corruption.
- The narrow win of the documented text path — stability of a specified format — is deliberately
  forgone. If the JSON path is ever withdrawn upstream, the fallback is the text path at the cost
  of the `STREAMS` capability, and this ADR would be revisited.

## Considered Options

- **Undocumented JSON stream** (chosen) — the only path with token deltas; keeps the `STREAMS`
  capability real and T7 cheap.
- **Documented text path (`-s`)** — rejected: stable but delta-free and reasoning-free, it makes
  `STREAMS = true` a lie and defers a rewrite to T7.
