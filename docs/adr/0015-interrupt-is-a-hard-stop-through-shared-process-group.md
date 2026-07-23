# Ctrl-C is a hard stop delivered through the shared process group

When the user interrupts `a`, the harness child must die, `a` must exit `130`, and no partial
answer must reach stdout. `a` achieves this by installing **no** signal handler and **no** new
process group: the child is spawned in `a`'s own foreground process group, so a terminal SIGINT
reaches it directly, and `subprocess.run`'s existing `SIGKILL` backstop guarantees it cannot
orphan. `main()` catches `KeyboardInterrupt` and exits `130`.

Decided in [issue #37](https://github.com/gahjelle/wingit/issues/37) (T2), the first slice that
spawns real harness processes. It joins `stdin=DEVNULL` ([ADR-0005](0005-capability-negotiating-harness-seam.md) §5)
and cwd-on-child ([ADR-0011](0011-project-environment-inherited-whole.md) §5) in the driver's
process-spawn contract. From the moment `a` spawns a live agent, a Ctrl-C that orphans it is a
**defect**, not a missing feature — which is why this is contract, not presentation, and lands
here rather than with the spinner in T7.

## Decisions

1. **No new process group, no `start_new_session`.** The child stays in `a`'s foreground process
   group, so the terminal delivers SIGINT to the child the natural way — it dies on its own
   signal. Isolating the child into its own group would *remove* it from the foreground group and
   force `a` to catch and hand-forward the signal itself, adding code whose only effect is to
   re-create the default behaviour.

2. **`subprocess.run` is the anti-orphan backstop.** Its bare `except:` clause `kill()`s the child
   with `SIGKILL` (unignorable) and `wait()`s it before re-raising. So even a harness that traps
   SIGINT cannot survive or orphan: the terminal SIGINT tries first, `SIGKILL` closes the door.
   No bespoke reaping code is needed or wanted.

3. **`main()` catches `KeyboardInterrupt` and exits `ExitCode.INTERRUPTED` (130).** Left uncaught,
   CPython prints a `KeyboardInterrupt` traceback (noise for a pipe tool) before exiting via a
   re-raised SIGINT. Catching it gives a clean exit at the code a shell already reports for SIGINT.
   `130` is a code `a` promises, so it lives in the `ExitCode` enum alongside `0`/`1`/`2`.

4. **"No partial flush" is structural in T2 and a live requirement later.** T2 captures all output
   and writes the Answer to stdout only *after* the run returns, so an interrupt raises before any
   write — stdout stays empty for free. When streaming lands (T7) this becomes an active
   obligation: a partial answer already emitted must not be completed or "finished" on interrupt.

5. **The signal path is proven live, not by fast tests.** The fake `ProcessRunner`
   ([ADR-0014](0014-fake-the-io-boundary-not-the-driver.md)) raises `KeyboardInterrupt` to assert
   `main()` exits `130` with empty stdout — deterministic, no real process. The real
   signal → child-death → no-orphan behaviour is verified by `just live-check`, which sends a real
   `SIGINT` to a real harness run and asserts exit `130` and no surviving child.

## Consequences

- `a` must **not** grow a signal handler or `start_new_session=True` without revisiting this ADR —
  either one silently breaks the "child dies on terminal SIGINT" path.
- The guarantee is "the child is dead and reaped," not "the child shut down gracefully." A harness
  mid-write is cut off. That is the intended meaning of *hard stop*.

## Considered Options

- **Shared process group + `SIGKILL` backstop** (chosen) — least code, and the OS already does the
  hard part.
- **New process group + explicit SIGINT forwarding** — rejected: more code, more failure modes, to
  reproduce the default behaviour.
- **A `KeyboardInterrupt` handler that flushes before exiting** — rejected: flushing a partial
  answer to stdout is the exact thing decision 4 forbids.
