"""Unit tests for the Pi driver: argv, last-turn answer, thinking, silent failure."""

from typing import TYPE_CHECKING

from conftest import RecordedRunner, load_fixture_lines, load_fixture_stderr

from wingit import core
from wingit.harnesses.pi import PiDriver
from wingit.schemas import (
    Event,
    ExitCode,
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)

if TYPE_CHECKING:
    import pytest


def collect(scenario: str, *, exit_code: int = 0) -> list[Event]:
    """Run the real driver over a recorded pi fixture and collect events."""
    return core.collect_events(
        PiDriver(),
        lines=load_fixture_lines("pi", scenario=scenario),
        exit_code=exit_code,
    )


def test_argv_is_approve_json_invocation() -> None:
    """Test that argv builds `pi --print` in auto-approve JSON mode."""
    argv = PiDriver().argv(Run(prompt="hi"))

    assert argv == [
        "pi",
        "--print",
        "--mode",
        "json",
        "--approve",
        "hi",
    ]


def test_prose_answer_is_last_turn_text() -> None:
    """Test that a tool-free run yields the last turn's text."""
    assert collect("prose")[-1] == FinalAnswer(text="pineapple")


def test_tools_yields_reasoning_activity_and_answer() -> None:
    """Test that a tool run surfaces reasoning, tool activity, and the final answer."""
    events = collect("tools")

    assert any(isinstance(event, ReasoningChunk) for event in events)
    assert any(isinstance(event, ToolActivity) for event in events)
    assert events[-1] == FinalAnswer(text="3")


def test_failure_emits_nothing_in_band() -> None:
    """Test that a failed run yields no in-band answer or `Failed` event."""
    events = collect("fail", exit_code=1)

    assert not any(isinstance(event, (FinalAnswer, Failed)) for event in events)


def test_failure_surfaces_stderr_through_the_core(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that exit code plus stderr drive the failure the driver stays silent on."""
    runner = RecordedRunner(
        stdout_lines=load_fixture_lines("pi", scenario="fail"),
        stderr=load_fixture_stderr("pi", scenario="fail"),
        exit_code=1,
    )

    code = core.dispatch(Run(prompt="hi"), driver=PiDriver(), runner=runner)
    captured = capsys.readouterr()

    assert code == ExitCode.FAILURE
    assert captured.out == ""
    assert "no-such-model-xyz" in captured.err
