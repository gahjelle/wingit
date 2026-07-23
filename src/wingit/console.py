"""The output contract: Answer to stdout, Reasoning and errors to stderr.

The stdout/stderr split is wingit's core promise (`CONTEXT.md`): stdout carries
only the Answer, as plain text with exactly one trailing newline for clean pipe
citizenship, and never Rich markup (#12). Everything else — Reasoning, failure
detail — goes to stderr.
"""

import sys
from typing import TextIO

__all__ = ["write_answer", "write_error", "write_reasoning"]


def _write_line(stream: TextIO, *, text: str) -> None:
    """Write `text` to `stream` as exactly one line ending in a single newline.

    Stripping trailing newlines before appending one collapses any run of them
    to a single newline, so text that already ends in one — or several — still
    yields a clean, single-newline line.
    """
    stream.write(text.rstrip("\n") + "\n")


def write_answer(text: str) -> None:
    """Write the Answer to stdout with exactly one trailing newline."""
    _write_line(sys.stdout, text=text)


def write_reasoning(text: str) -> None:
    """Write Reasoning to stderr as plain text."""
    _write_line(sys.stderr, text=text)


def write_error(message: str) -> None:
    """Write a failure message to stderr as plain text."""
    _write_line(sys.stderr, text=message)
