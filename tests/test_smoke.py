"""Smoke test: the package imports cleanly."""

import wingit
from wingit.__main__ import main


def test_smoke() -> None:
    """Test that wingit exposes its entry point."""
    assert wingit.__doc__ is not None
    assert callable(main)
