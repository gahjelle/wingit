"""Unit tests for `resolve_harness`: the pure harness-selection helper."""

from typing import TYPE_CHECKING

import pytest
from cyclopts import CycloptsError

from wingit.cli import resolve_harness
from wingit.schemas import Harness

if TYPE_CHECKING:
    from collections.abc import Callable


def test_default_is_claude() -> None:
    """Test that selecting nothing falls back to the default harness, Claude."""
    assert resolve_harness() == Harness.CLAUDE


@pytest.mark.parametrize(
    ("select", "expected"),
    [
        (lambda: resolve_harness(Harness.OPENCODE), Harness.OPENCODE),
        (lambda: resolve_harness(cl=True), Harness.CLAUDE),
        (lambda: resolve_harness(cp=True), Harness.COPILOT),
        (lambda: resolve_harness(cx=True), Harness.CODEX),
        (lambda: resolve_harness(oc=True), Harness.OPENCODE),
        (lambda: resolve_harness(pi=True), Harness.PI),
    ],
)
def test_single_selection_resolves(
    *, select: Callable[[], Harness], expected: Harness
) -> None:
    """Test that any single selector — long or short — resolves to its harness."""
    assert select() == expected


@pytest.mark.parametrize(
    "select",
    [
        lambda: resolve_harness(cl=True, cp=True),  # two shorts
        lambda: resolve_harness(Harness.CLAUDE, cl=True),  # long + short, agreeing
        lambda: resolve_harness(Harness.CLAUDE, cp=True),  # long + short, disagreeing
        lambda: resolve_harness(cl=True, cx=True, pi=True),  # three shorts
    ],
)
def test_selecting_more_than_once_is_a_usage_error(
    *, select: Callable[[], Harness]
) -> None:
    """Test that selecting a harness twice by any combination raises for usage."""
    with pytest.raises(CycloptsError):
        select()
