# PROTOTYPE — adapter seam (throwaway)

Answers [issue #13](https://github.com/gahjelle/wingit/issues/13): **does one adapter
seam actually fit five harnesses, or does uniformity cost more than it buys?**

## The question, precisely

Given the output contract settled in [#12](https://github.com/gahjelle/wingit/issues/12)
— stdout is the answer, streamed; stderr is best-effort reasoning; exit codes are
wingit's own 0/1/2 — can a single `HarnessDriver` interface express four maximally
different harnesses without accreting per-harness special cases until it is "a union
type wearing a trenchcoat"?

The four, chosen for maximum divergence:

| Harness | Why it is here |
| --- | --- |
| **Claude Code** | Clean terminal `result` event holding the whole answer. The easy case. |
| **Opencode** | *No* terminal result event and no consolidated answer field — the answer must be reassembled from `text` parts across multiple steps. |
| **Copilot CLI** | JSONL schema entirely undocumented; the documented path to a clean answer is `-s` on **plain text**, so structured parsing may not be the primary path at all. |
| **Codex** | Inverts the safety axis: a real OS sandbox with `read-only` as the `exec` default and network off, and **no** `--ask-for-approval` flag at all. |

Pi was left out deliberately: its content-block shape is close to Claude Code's, so it
adds cost without adding an axis.

## Shape: record once, replay forever

Real harness runs cost 20–60s each and at least two of the five are known to hang
silently. So `record.py` runs the real binaries **once** and freezes their raw
stdout/stderr/exit-code into `recordings/`; `tui.py` then replays those bytes through
the adapters instantly and deterministically.

The recordings are real output from real harnesses — the fidelity that makes the finding
trustworthy — but driving the prototype never touches a network.

## Layout

- `seam.py` — the **candidate interface** under test. The portable bit; everything else
  is scaffolding.
- `adapters.py` — four throwaway adapters implementing it.
- `record.py` — runs the real harnesses, writes `recordings/`.
- `tui.py` — replay TUI: pick harness × scenario, watch what the seam yields.
- `workspace/` — fixed cwd for the tool-using scenario, so the recordings are comparable.

## Run it

```
just prototype-seam          # the replay TUI
just prototype-seam-record   # re-record from the real harnesses (slow, networked)
```
