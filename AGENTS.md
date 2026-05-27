# AGENTS.md

Purpose: guidance for agentic edits in asteroidpy.

**Build / Lint / Test Commands**
- `pip install -e ".[dev]"` for runtime + dev tools (same set Jenkins uses for lint/test).
- `python -m build` to build artifacts.
- `pytest -q` to run the test suite.
- `pytest <path>::<test_name> -q` for a single test.
- `ruff check .` (or `flake8`) for linting; `mypy` for type checks; `black --check .`; `isort --check .`.
- HTML API docs: install Sphinx with `pip install -e ".[docs]"`, then `(cd docs && make html)`, output under `docs/build/html/`.

**CI / Release**
- Jenkins pipeline: [`Jenkinsfile`](Jenkinsfile) — lint, tests, build, wheel smoke test, PyPI publish on `vX.Y.Z` tags; archives `dist/*` and `coverage.xml`.
- Release scripts: `./release.sh` (version bump + tag + push), `./ghrelease.sh` (GitHub release from CHANGELOG).
- No GitHub Actions workflows; do not add `.github/workflows/` unless explicitly requested.

**Code Style**
- **Imports**: standard library first, then third‑party, then local; explicit imports only.
- **Formatting**: format with Black; sort imports with isort; auto‑format on save if available.
- **Types & Naming**: use type hints; snake_case for functions/vars; CamelCase for classes.
- **Errors**: avoid bare excepts; raise/propagate clear exceptions; validate inputs early.
- **Tests**: tests should be small, isolated; prefer parameterized tests when sensible.

**Cursor / Copilot Rules**
- Cursor rules: none found in this repo.
- Copilot instructions: none found in this repo.