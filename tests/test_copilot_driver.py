"""Unit tests for the Copilot driver: argv, final message, silent failure."""

from conftest import make_collector

from wingit.harnesses.copilot import CopilotDriver
from wingit.schemas import (
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)

collect = make_collector(CopilotDriver, harness="copilot")


def test_argv_is_allow_all_tools_json_invocation() -> None:
    """Test that argv builds `copilot --prompt` in auto-approve JSON mode."""
    argv = CopilotDriver().argv(Run(prompt="hi"))

    assert argv == [
        "copilot",
        "--prompt",
        "hi",
        "--output-format",
        "json",
        "--allow-all-tools",
        "--log-level",
        "none",
    ]


def test_prose_answer_is_final_message() -> None:
    """Test that a tool-free run yields the last non-empty assistant message."""
    assert collect("prose")[-1] == FinalAnswer(text="pineapple")


def test_tools_answer_skips_empty_tool_turn_message() -> None:
    """Test that the answer is the last non-empty message, not the tool turn's."""
    events = collect("tools")

    assert any(isinstance(event, ToolActivity) for event in events)
    assert not any(isinstance(event, ReasoningChunk) for event in events)
    assert events[-1] == FinalAnswer(text="3")


def test_failure_emits_nothing_in_band() -> None:
    """Test that a failed run yields no in-band answer or `Failed` event."""
    events = collect("fail", exit_code=1)

    assert not any(isinstance(event, (FinalAnswer, Failed)) for event in events)
