"""Unit tests for the Pi driver: argv, last-turn answer, thinking, silent failure."""

from conftest import make_collector

from wingit.harnesses.pi import PiDriver
from wingit.schemas import (
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)

collect = make_collector(PiDriver, harness="pi")


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
