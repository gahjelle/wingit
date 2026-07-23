"""The thin cyclopts CLI: one positional prompt, dispatched to the core.

No domain logic lives here (code-conventions.md): the command builds a `Run`
and hands it to `core.dispatch`. cyclopts owns `--help`; usage errors become
exit 2 via the remap in `wingit.main` (D5).
"""

from cyclopts import App

from wingit import core
from wingit.harnesses.claude import ClaudeDriver
from wingit.runner import SubprocessRunner
from wingit.schemas import Run

__all__ = ["app"]

app = App(
    name="a",
    help="Ask your agent harness a question; the answer prints to stdout.",
)


@app.default
def ask(prompt: str) -> int:
    """Run `prompt` through the harness and print the answer; return the exit code."""
    run = Run(prompt=prompt)
    return core.dispatch(run, driver=ClaudeDriver(), runner=SubprocessRunner())
