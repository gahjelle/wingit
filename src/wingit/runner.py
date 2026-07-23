"""The real `ProcessRunner`: spawns a harness and captures its output.

Spawn contract (ADR-0005 §5, ADR-0011 §5): `stdin` is `DEVNULL`, the child runs
in wingit's own cwd, and stdout/stderr are captured (never forwarded live). It
reads all output then returns; a future line-iterator can sit behind the same
`ProcessRunner` Protocol without changing callers.
"""

import subprocess
from pathlib import Path

from wingit.harnesses.base import RunResult
from wingit.schemas import ExitCode

__all__ = ["SubprocessRunner"]


class SubprocessRunner:
    """Runs a harness via `subprocess`, capturing stdout, stderr, and exit code."""

    def run(self, argv: list[str], *, cwd: Path) -> RunResult:
        """Spawn `argv` in `cwd`; return its captured output and exit code."""
        try:
            completed = subprocess.run(  # noqa: S603 - argv built by trusted driver
                argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                cwd=cwd,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            # A missing harness binary is an environmental failure, not a usage
            # error, so it maps to the failure exit rather than the usage one.
            return RunResult(
                stdout_lines=[],
                stderr=f"harness not found: {argv[0]!r} is not on PATH",
                exit_code=ExitCode.FAILURE,
            )
        return RunResult(
            stdout_lines=completed.stdout.splitlines(),
            stderr=completed.stderr,
            exit_code=completed.returncode,
        )
