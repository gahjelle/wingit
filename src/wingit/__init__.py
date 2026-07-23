"""wingit: run your agent harness in headless mode behind a thin, pipeable CLI."""

import sys

from cyclopts import CycloptsError

from wingit.cli import app

__all__ = ["USAGE_EXIT", "main"]

# Usage errors get their own exit code, distinct from a harness failure (exit 1),
# per the 0/1/2 contract (D5). cyclopts itself exits 1 on a parse error, so main()
# remaps it: it lets cyclopts print the detail, then exits 2.
USAGE_EXIT = 2


def main() -> None:
    """Entry point for the `a` / `wingit` command: run the CLI and exit."""
    try:
        code = app(sys.argv[1:], exit_on_error=False)
    except CycloptsError:
        # cyclopts has already printed the error panel to stderr.
        sys.exit(USAGE_EXIT)
    sys.exit(code)
