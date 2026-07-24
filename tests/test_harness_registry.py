"""Registry-level tests: the `Harness` enum, the driver registry, and totality.

These assert the *grid* is complete and correct without touching harness bytes:
every `Harness` maps to a driver, every driver declares every `Capability`
explicitly, and the declared values match the settled capability grid.
"""

import pytest

from wingit.cli import SHORT_FLAGS
from wingit.harnesses import DRIVERS
from wingit.schemas import Capability, Harness

# The settled capability grid: one row per harness, verified live.
EXPECTED_CAPABILITIES = {
    Harness.CLAUDE: {
        Capability.STREAMS: False,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: True,
    },
    Harness.PI: {
        Capability.STREAMS: True,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: True,
    },
    Harness.OPENCODE: {
        Capability.STREAMS: False,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: False,
    },
    Harness.COPILOT: {
        Capability.STREAMS: True,
        Capability.SHOWS_REASONING: False,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: False,
    },
    Harness.CODEX: {
        Capability.STREAMS: False,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: False,
        Capability.RUNS_WITHOUT_STORING_SESSION: True,
    },
}


def test_registry_covers_every_harness() -> None:
    """Test that the registry maps exactly the `Harness` enum members."""
    assert set(DRIVERS) == set(Harness)


def test_every_harness_has_a_short_flag() -> None:
    """Test that the short-flag map stays in sync with the `Harness` enum.

    Adding a harness must add its `-xx` short; this fails if `SHORT_FLAGS` and
    the enum drift apart (the one CLI sync a new harness still needs by hand).
    """
    assert set(SHORT_FLAGS.values()) == set(Harness)


def test_harness_members_are_detection_ranked() -> None:
    """Test that the enum is ordered by CONTEXT.md detection rank."""
    assert list(Harness) == [
        Harness.CLAUDE,
        Harness.PI,
        Harness.OPENCODE,
        Harness.COPILOT,
        Harness.CODEX,
    ]


@pytest.mark.parametrize("harness", list(Harness))
def test_driver_declares_every_capability(harness: Harness) -> None:
    """Test that each driver assigns a bool to every `Capability` (totality)."""
    driver = DRIVERS[harness]()

    assert driver.capabilities.keys() == set(Capability)


@pytest.mark.parametrize("harness", list(Harness))
def test_capability_grid_matches_settled_values(harness: Harness) -> None:
    """Test that each driver's declared capabilities match the settled grid."""
    driver = DRIVERS[harness]()

    assert driver.capabilities == EXPECTED_CAPABILITIES[harness]
