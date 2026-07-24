"""The thin cyclopts CLI: one positional prompt, dispatched to the core.

No domain logic lives here (code-conventions.md): the command resolves the
harness, builds a `Run`, and hands it to `core.dispatch`. cyclopts owns
`--help`; usage errors — including a double harness selection — become the usage
exit code via the remap in `wingit.__main__.main`.
"""

from typing import Annotated

from cyclopts import App, CycloptsError, Parameter

from wingit import core
from wingit.harnesses import DRIVERS
from wingit.runner import SubprocessRunner
from wingit.schemas import Harness, Run

__all__ = ["app", "resolve_harness"]

# `wingit` is the canonical name; `a` is a short alias wired up as a second
# console script (see pyproject), so the two entry points share this one app.
app = App(
    name="wingit",
    help="Ask your agent harness a question; the answer prints to stdout.",
)

# Each two-letter short selects one harness. Two letters, not one: the set of
# harnesses grows, and a growing set gets two-letter shorts (issue #23).
SHORT_FLAGS: dict[str, Harness] = {
    "cl": Harness.CLAUDE,
    "cp": Harness.COPILOT,
    "cx": Harness.CODEX,
    "oc": Harness.OPENCODE,
    "pi": Harness.PI,
}


def resolve_harness(
    harness: Harness | None = None,
    *,
    cl: bool = False,
    cp: bool = False,
    cx: bool = False,
    oc: bool = False,
    pi: bool = False,
) -> Harness:
    """Resolve the selected harness from the long flag and the short flags.

    Selecting a harness more than once by any combination — two shorts, or a
    short plus the long flag, even when they agree — is a usage error, since
    cyclopts does not auto-mutex these flags. With nothing selected, the default
    is Claude; a later slice makes this default config-driven.
    """
    chosen_shorts = {"cl": cl, "cp": cp, "cx": cx, "oc": oc, "pi": pi}
    selected = [SHORT_FLAGS[name] for name, on in chosen_shorts.items() if on]
    if harness is not None:
        selected.append(harness)
    if len(selected) > 1:
        raise CycloptsError(msg="Select at most one harness.")
    return selected[0] if selected else Harness.CLAUDE


@app.default
def ask(
    prompt: str,
    *,
    harness: Annotated[Harness | None, Parameter(name=["--harness"])] = None,
    cl: Annotated[bool, Parameter(name=["-cl"])] = False,
    cp: Annotated[bool, Parameter(name=["-cp"])] = False,
    cx: Annotated[bool, Parameter(name=["-cx"])] = False,
    oc: Annotated[bool, Parameter(name=["-oc"])] = False,
    pi: Annotated[bool, Parameter(name=["-pi"])] = False,
) -> int:
    """Run `prompt` through the selected harness; print the answer, return the code."""
    selected = resolve_harness(harness, cl=cl, cp=cp, cx=cx, oc=oc, pi=pi)
    run = Run(prompt=prompt)
    return core.dispatch(run, driver=DRIVERS[selected](), runner=SubprocessRunner())
