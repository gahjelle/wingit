"""Smoke test: the package imports cleanly."""

import wingit


def test_smoke() -> None:
    """Test that wingit exposes its entry point."""
    assert callable(wingit.main)
