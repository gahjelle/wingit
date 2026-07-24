"""Silent-failure harnesses: exit code plus stderr drive the failure, not in-band bytes.

Copilot and Pi emit nothing in-band on a failed run — no result, no error event —
so their drivers raise no synthetic `Failed`. This one parametrized test proves
the core still fails the run from the exit code and surfaces the child's stderr,
for every driver that stays silent.
"""

from typing import TYPE_CHECKING

import pytest
from conftest import RecordedRunner, load_fixture_lines, load_fixture_stderr

from wingit import core
from wingit.harnesses.copilot import CopilotDriver
from wingit.harnesses.pi import PiDriver
from wingit.schemas import ExitCode, Run

if TYPE_CHECKING:
    from wingit.harnesses.base import HarnessDriver


@pytest.mark.parametrize(
    ("driver_cls", "harness"),
    [
        (CopilotDriver, "copilot"),
        (PiDriver, "pi"),
    ],
)
def test_failure_surfaces_stderr_through_the_core(
    *,
    driver_cls: type[HarnessDriver],
    harness: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that exit code plus stderr drive the failure the driver stays silent on."""
    runner = RecordedRunner(
        stdout_lines=load_fixture_lines(harness, scenario="fail"),
        stderr=load_fixture_stderr(harness, scenario="fail"),
        exit_code=1,
    )

    code = core.dispatch(Run(prompt="hi"), driver=driver_cls(), runner=runner)
    captured = capsys.readouterr()

    assert code == ExitCode.FAILURE
    assert captured.out == ""
    assert "no-such-model-xyz" in captured.err
