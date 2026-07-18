default: check

# Run all quality gates in order, stopping on the first failure.
check: fmt-check lint conventions typecheck test

# Auto-format the codebase with ruff.
fmt:
    uv run ruff format -q

# Check formatting without writing changes.
fmt-check:
    uv run ruff format --check -q

# Lint the codebase with ruff.
lint:
    uv run ruff check -q

# Type-check src/ and tests/ with ty.
typecheck:
    uv run ty check -q

# Enforce repo-specific conventions ruff/ty can't express.
conventions *args:
    uv run garuff check -q src tests {{args}}

# Run the test suite quietly.
test *args:
    uv run pytest -q {{args}}

# PROTOTYPE (issue #13) — replay recorded harness output through the candidate seam.
prototype-seam:
    uv run python prototypes/adapter-seam/tui.py

# PROTOTYPE (issue #13) — re-record from the real harnesses. Slow and networked.
prototype-seam-record *args:
    uv run python prototypes/adapter-seam/record.py {{args}}

# Auto-fix lint issues then reformat.
fix:
    uv run ruff check --fix -q
    uv run garuff check --fix
    uv run ruff format -q
