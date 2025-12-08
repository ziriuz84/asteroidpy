# AGENTS.md

Purpose: guidance for agentic edits in asteroidpy.

**Build / Lint / Test Commands**
- `python -m build` to build artifacts.
- `pytest -q` to run the test suite.
- `pytest <path>::<test_name> -q` for a single test.
- `ruff check .` (or `flake8`) for linting; `mypy` for type checks.

**Code Style**
- **Imports**: standard library first, then third‑party, then local; explicit imports only.
- **Formatting**: format with Black; sort imports with isort; auto‑format on save if available.
- **Types & Naming**: use type hints; snake_case for functions/vars; CamelCase for classes.
- **Errors**: avoid bare excepts; raise/propagate clear exceptions; validate inputs early.
- **Tests**: tests should be small, isolated; prefer parameterized tests when sensible.

**Cursor / Copilot Rules**
- Cursor rules: none found in this repo.
- Copilot instructions: none found in this repo.