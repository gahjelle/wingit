"""The output contract: Answer to stdout, Reasoning and errors to stderr.

The stdout/stderr split is wingit's core promise (`CONTEXT.md`): stdout carries
only the Answer, as plain text with exactly one trailing newline for clean pipe
citizenship, and never Rich markup (#12). Everything else — Reasoning, failure
detail — goes to stderr.
"""

import sys

__all__ = ["write_answer", "write_error", "write_reasoning"]


def write_answer(text: str) -> None:
    """Write the Answer to stdout with exactly one trailing newline (D3)."""
    # rstrip("\n") collapses any run of trailing newlines to exactly one, so a
    # `.result` ending in "\n\n" still yields a single-newline, pipe-clean line.
    sys.stdout.write(text.rstrip("\n") + "\n")


def write_reasoning(text: str) -> None:
    """Write Reasoning to stderr as plain text."""
    sys.stderr.write(text.removesuffix("\n") + "\n")


def write_error(message: str) -> None:
    """Write a failure message to stderr as plain text."""
    sys.stderr.write(message.removesuffix("\n") + "\n")
