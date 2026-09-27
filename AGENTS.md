# AGENTS.md

Purpose: guidance for agentic edits in asteroidpy. The human-facing contributor
guide (setup narrative, architecture, translations, release process) lives in
[`CONTRIBUTING.md`](CONTRIBUTING.md); this file is the terse, agent-facing
summary. Keep the two consistent when the build/test commands change.

**Build / Lint / Test Commands**
- `pip install -e ".[dev]"` for runtime + dev tools (same set Jenkins uses for lint/test).
- `python -m build` to build artifacts.
- `pytest -q` to run the test suite.
- `pytest <path>::<test_name> -q` for a single test.
- Lint and types — these mirror the Jenkins `Lint` stage exactly, so run them before pushing:
  - `ruff check asteroidpy/ tests/`
  - `mypy asteroidpy/`
  - `isort --check asteroidpy/ tests/`
  - `black --check asteroidpy/ tests/`
  - The repo-wide forms (`ruff check .`, `isort --check .`, `black --check .`) also pass, but the gate is the narrower set above. `docs/` is excluded from Black (Sphinx config) and isort is told to respect `.gitignore`, so a venv at `env/` is not scanned.
  - `ruff` has no rule set pinned in `pyproject.toml` by accident: `lint.select` is explicit (`E,F,W,B,C4`, `E501` ignored because Black owns formatting). Do not add rules to it without fixing the whole codebase first — ruff's *implicit* default widened once already and broke CI.
- HTML API docs: install Sphinx with `pip install -e ".[docs]"`, then `(cd docs && make html)`, output under `docs/build/html/`. `conf.py` sets `nitpicky = True`, so a broken cross-reference is a build warning — treat any warning as a failure. The Jenkinsfile has **no** docs stage, so this is not covered by CI.

**Documentation**
- User-facing docs live in two places that must agree: `README.md` and `docs/source/*.rst`. When adding or renaming a feature, a config option, a language, or a public function, update both.
- The feature list in `README.md` and `docs/source/index.rst` mirrors the screens in `asteroidpy/interface/_tui_screens.py`; the `[Planner]` weights are the one documented setting with no in-app screen (INI only).
- `docs/source/asteroidpy.rst` lists "Key Functions" per module — keep it in sync with the public API, and prefer a real `autodoc` cross-reference (`:func:`…``) over prose so `nitpicky` catches drift.
- Every new public function needs a docstring; modules that are autodoc'd need a module docstring.

**CI / Release**
- Jenkins pipeline: [`Jenkinsfile`](Jenkinsfile) — lint, tests, SonarQube analysis (`https://sq.casapomininegri.it`), build, wheel smoke test, PyPI publish on `vX.Y.Z` tags; archives `dist/*` and `coverage.xml`.
- SonarQube config: [`sonar-project.properties`](sonar-project.properties) — keep `sonar.projectKey` aligned with the SonarQube project; Jenkins credential ID `SONAR_TOKEN`.
- Release scripts: `./release.sh` (version bump + tag + push), `./ghrelease.sh` (GitHub release from CHANGELOG; thin wrapper over `./release.sh --github-release`, so both share one preflight + release-branch enforcement). Both must run from `main` with a clean working tree and abort otherwise — see [`CONTRIBUTING.md`](CONTRIBUTING.md#release-process).
- `release.sh` keeps `RELEASE_BRANCH="main"` as the single source of truth for the help text, the branch validation and the push. Do not reintroduce a hardcoded `main` literal elsewhere, and do not loosen `validate_branch()` to a y/N prompt.
- `preflight_base()` must stay the first statement in `main()`: argument parsing shells out to `grep`, so a tool check placed later would report a missing dependency as an unrelated failure. Blocking tools (git/sed/grep/awk/cat/head/date/tr, plus `gh` in GitHub mode) call `error`; `msgfmt` is optional and only warns.
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