"""Unit tests for the Opencode driver: argv, buffered answer, reasoning, failure."""

from conftest import make_collector

from wingit.harnesses.opencode import OpencodeDriver
from wingit.schemas import Failed, FinalAnswer, ReasoningChunk, Run, ToolActivity

collect = make_collector(OpencodeDriver, harness="opencode")


def test_argv_is_auto_thinking_json_invocation() -> None:
    """Test that argv builds `opencode run` in auto-approve JSON mode with thinking."""
    argv = OpencodeDriver().argv(Run(prompt="hi"))

    assert argv == [
        "opencode",
        "run",
        "--format",
        "json",
        "--auto",
        "--thinking",
        "hi",
    ]


def test_prose_answer_is_last_step_text() -> None:
    """Test that a tool-free run reassembles the answer from the last step."""
    assert collect("prose") == [FinalAnswer(text="pineapple")]


def test_tools_yields_reasoning_activity_and_answer() -> None:
    """Test that a tool run surfaces reasoning, tool activity, and the final answer."""
    events = collect("tools")

    assert any(isinstance(event, ReasoningChunk) for event in events)
    assert ToolActivity(gist="glob") in events
    assert events[-1] == FinalAnswer(text="4")


def test_failure_error_event_yields_failed_and_no_answer() -> None:
    """Test that an `error` event yields `Failed` and suppresses the answer."""
    events = collect("fail", exit_code=1)

    assert any(isinstance(event, Failed) for event in events)
    assert not any(isinstance(event, FinalAnswer) for event in events)
