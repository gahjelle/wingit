"""The `wingit` / `a` entry point, also runnable as `python -m wingit`."""

import sys
from typing import TYPE_CHECKING

from cyclopts import CycloptsError

from wingit.cli import app
from wingit.schemas import ExitCode

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for the `wingit` / `a` command: run the CLI and exit.

    `argv` defaults to `None`, which lets cyclopts read `sys.argv`; tests pass a
    token list directly. cyclopts only ever exits 1 on a parse error, so this
    catches it, lets cyclopts print the detail, and remaps to the usage code —
    the one place the 0/1/2 contract needs a distinct exit for a bad invocation.
    """
    try:
        code = app(argv, exit_on_error=False)
    except CycloptsError:
        sys.exit(ExitCode.USAGE)
    sys.exit(code)


if __name__ == "__main__":
    main()
