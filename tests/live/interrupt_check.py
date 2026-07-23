"""A faithful terminal Ctrl-C against a live `a` run, for `just live-check`.

This is the manual liveness half of the interrupt contract (ADR-0015): the fast
test injects a `KeyboardInterrupt` at the fake `ProcessRunner`, while this script
drives a *real* harness under a pseudo-terminal and sends a real Ctrl-C.

A scripted `kill -INT <pid>` does not reproduce a terminal Ctrl-C: a terminal
delivers SIGINT to the whole foreground process group via the tty line
discipline, not to one pid, and a plain `just` recipe runs with job control off,
so a single-pid `kill` races the harness and gives a misleading exit code. Here
`a` runs as the session leader of a real pty; writing the Ctrl-C control byte to
the master makes the line discipline raise SIGINT on `a`'s foreground group —
`a` and the harness child it did not isolate — exactly as a keypress would. The
script asserts `a` exits `130` and the harness child does not survive.

Run only via `just live-check`; it spawns a real, logged-in harness.
"""

import contextlib
import os
import pty
import subprocess
import sys
import time

PROMPT = (
    "Run this exact shell command and wait for it to finish, then reply done: sleep 30"
)
A_BINARY = ".venv/bin/a"
CTRL_C = b"\x03"
BUSY_SECONDS = 6
REAP_TIMEOUT = 20
INTERRUPTED = 130


def child_pids(pid: int) -> list[str]:
    """Return the direct child pids of `pid`, captured while it is still alive."""
    result = subprocess.run(
        ["pgrep", "-P", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.split()


def is_alive(pid: str) -> bool:
    """Return whether `pid` is still a living process."""
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def reap(pid: int, *, master_fd: int) -> int | None:
    """Drain the pty and reap `pid`, returning its exit code or None on timeout."""
    os.set_blocking(master_fd, False)
    deadline = time.time() + REAP_TIMEOUT
    while time.time() < deadline:
        # No output ready yet, or the slave has closed; either way keep reaping.
        with contextlib.suppress(OSError):
            os.read(master_fd, 4096)
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid:
            return os.waitstatus_to_exitcode(status)
        time.sleep(0.2)
    return None


def run_interrupt_check() -> int:
    """Drive a live `a` run, Ctrl-C it through a pty, and report the outcome."""
    pid, master_fd = pty.fork()
    if pid == 0:
        os.execvp(A_BINARY, [A_BINARY, PROMPT])

    time.sleep(BUSY_SECONDS)  # Let the harness get busy on the sleep tool call.
    kids = child_pids(pid)
    os.write(master_fd, CTRL_C)  # Terminal Ctrl-C: SIGINT to a's foreground group.

    code = reap(pid, master_fd=master_fd)
    survivors = [kid for kid in kids if is_alive(kid)]
    print(f"exit={code} (expect {INTERRUPTED})  children={kids}  survivors={survivors}")

    if code == INTERRUPTED and not survivors:
        print("  -> PASS: exit 130, no surviving child")
        return 0
    print("  !! FAIL: interrupt contract not met")
    return 1


if __name__ == "__main__":
    sys.exit(run_interrupt_check())
