# Contributing to AsteroidPy

Thank you for considering contributing. This guide covers the development
workflow; for the project itself see the [README](README.md).

- [Code of Conduct](CODE_OF_CONDUCT.md) — please read it before participating
- [Security Policy](SECURITY.md) — how to report a vulnerability (do **not** open a public issue)

## Ways to contribute

- **Code**: bug fixes, new features, refactoring
- **QA**: bug reports with repro steps and environment details
- **Documentation**: improvements to the README, docstrings, or Sphinx docs
- **Community**: presenting the project, organizing local meetups

## Reporting bugs and requesting features

Use the issue templates in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/)
([bug report](.github/ISSUE_TEMPLATE/bug_report.md),
[feature request](.github/ISSUE_TEMPLATE/feature_request.md)). Include your
Python version, operating system, and AsteroidPy version, plus the exact steps
to reproduce. Browse [open issues](https://github.com/ziriuz84/asteroidpy/issues)
to comment or pick one up before opening a new one.

## Development setup

Requires **Python 3.11+** (see [Requirements](README.md#requirements)) and a
virtual environment (recommended).

1. Clone and install in editable mode:

   ```bash
   git clone https://github.com/ziriuz84/asteroidpy.git
   cd asteroidpy
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

   The `dev` extra pulls in `pytest`, `ruff`, `mypy`, `black`, and `isort`. To
   install them individually, do `pip install pytest ruff mypy black isort`.

2. Run the test suite:

   ```bash
   pytest -q
   ```

   A single test:

   ```bash
   pytest tests/test_scheduling.py::test_name -q
   ```

3. Run the lint gate. These four commands mirror the Jenkins `Lint` stage
   exactly, so all four must pass before you push:

   ```bash
   ruff check asteroidpy/ tests/
   mypy asteroidpy/
   isort --check asteroidpy/ tests/
   black --check asteroidpy/ tests/
   ```

   The repo-wide forms (`ruff check .`, `isort --check .`, `black --check .`)
   also pass, but the gate is the narrower set above. `docs/` is excluded from
   Black, and isort is told to respect `.gitignore`.

   `ruff` rules are pinned explicitly in `pyproject.toml` (`lint.select`).
   Do not add rules without fixing the whole codebase first: ruff's *implicit*
   default widened once already and broke CI.

4. Build the package:

   ```bash
   python -m build
   ```

5. Build the HTML API docs. `docs/source/conf.py` sets `nitpicky = True`, so a
   broken cross-reference is a build warning — treat any warning as a failure:

   ```bash
   pip install -e ".[docs]"
   cd docs && make html      # output under docs/build/html/
   ```

6. If you changed `.po` files, compile the locale catalogs before building a
   release wheel:

   ```bash
   msgfmt -o asteroidpy/locales/en/LC_MESSAGES/base.mo asteroidpy/locales/en/LC_MESSAGES/base.po
   # repeat for other locales, or use ./release.sh which compiles them automatically
   ```

## Code style

- **Imports**: standard library → third-party → local; explicit imports only
- **Formatting**: Black for style; isort for import order
- **Types**: type hints on public APIs; snake_case for functions/variables; CamelCase for classes
- **Errors**: avoid bare `except`; raise or propagate clear exceptions; validate inputs early
- **Docstrings**: every public function needs one, and every autodoc'd module needs a module docstring
- **Tests**: small, isolated tests; prefer parameterized tests where sensible

## Project architecture

```
asteroidpy/
├── __init__.py       # Entry point; loads config, launches interface
├── interface/        # Textual TUI, gettext setup (legacy menu helpers retained)
├── scheduling.py     # Ephemerides, weather, NEOcp, twilight, best-night planner
├── configuration.py  # Observatory config, horizon, language, planner weights
└── locales/          # gettext translations (en, it, de, fr, es, pt), shipped in PyPI wheels
```

- **`interface`** — Main entry for the interactive UI (Textual screens). Loads config, sets up gettext, and delegates to `scheduling` for ephemeris/weather/NEOcp and to `configuration` for settings. The screens live in `interface/_tui_screens.py`.
- **`scheduling`** — Astronomy logic: MPC queries, 7Timer weather, twilight, Sun/Moon ephemeris, and the best-night planner. Uses `configuration.load_config()` to read observatory data.
- **`configuration`** — Persists and loads settings via platformdirs; handles observatory coordinates, virtual horizon, planner weights, and language. Used by both `interface` and `scheduling`.

## Documentation

User-facing documentation lives in two places that must agree: `README.md` and
`docs/source/*.rst`. When you add or rename a feature, a config option, a
language, or a public function, update both. `docs/source/asteroidpy.rst` lists
"Key Functions" per module — keep it in sync with the public API.

## How to add a translation

AsteroidPy uses [GNU gettext](https://www.gnu.org/software/gettext/) with a
single catalog `base`. Translations live under
`asteroidpy/locales/<lang>/LC_MESSAGES/`.

1. Create a new locale directory:

   ```bash
   mkdir -p asteroidpy/locales/nl/LC_MESSAGES
   ```

2. Copy and adapt an existing `.po` file, or create one from the template:

   ```bash
   cp asteroidpy/locales/it/LC_MESSAGES/base.po asteroidpy/locales/nl/LC_MESSAGES/base.po
   ```

   Edit `asteroidpy/locales/nl/LC_MESSAGES/base.po`, set `Language: nl`, and
   translate all `msgstr` entries.

3. Compile the `.po` file into a `.mo` file (required for the language to appear
   in the menu when running from source):

   ```bash
   msgfmt -o asteroidpy/locales/nl/LC_MESSAGES/base.mo asteroidpy/locales/nl/LC_MESSAGES/base.po
   ```

   The `msgfmt` command comes with the gettext package (`gettext` on most Linux
   distros; on Windows, install via [MSYS2](https://www.msys2.org/) or
   Chocolatey). Until the `.mo` exists, text from that `.po` is not used by
   gettext; the interactive UI may notify you once per incomplete locale under
   **General** → **Language**.

4. The new language will appear in **Configuration → General** after restart.

To add or update translatable strings for all locales, update
`asteroidpy/locales/base.pot` (e.g. with `xgettext` or `pybabel`), then merge
into each `.po` with `msgmerge`, translate, and recompile with `msgfmt`.

## Continuous integration (Jenkins)

CI runs on **Jenkins** via [`Jenkinsfile`](Jenkinsfile) (triggered on every push to GitHub). The pipeline:

| Stage | When | What it does |
|-------|------|--------------|
| Setup | always | venv, `pip install -e ".[dev]"`, installs `gettext`/`msgfmt` when missing |
| Lint | always (including releases) | `ruff`, `mypy`, `isort`, `black --check` |
| Test | always | `pytest` with coverage (`coverage.xml` archived) |
| SonarQube | always | uploads analysis to [sq.casapomininegri.it](https://sq.casapomininegri.it); non-blocking (stage may show unstable if upload fails) |
| Build | always | compiles `.mo` catalogs, then `python -m build` |
| Validate / install smoke test | always | `twine check`, install wheel, verify locale catalogs and `asteroidpy` entry point |
| Publish to PyPI | release tags only (`vX.Y.Z`) | uploads to PyPI when the tag matches `asteroidpy/version.py` |

Successful builds archive `dist/*` (and `coverage.xml`) as Jenkins artifacts. GitHub Actions workflows are not used; Jenkins is the single CI/CD path for builds and PyPI publishing. Note the pipeline has **no docs stage**, so the Sphinx build is not covered by CI — run step 5 above yourself when you touch `docs/` or docstrings.

### SonarQube setup (one-time)

Before the SonarQube stage can run on Jenkins:

1. Create or import the project on [sq.casapomininegri.it](https://sq.casapomininegri.it) and note its project key (currently `ziriuz84_asteroidpy_1d603420-1b43-4943-86f6-ab01cd7be87b`).
2. Confirm `sonar.projectKey` in [`sonar-project.properties`](sonar-project.properties) matches the SonarQube project.
3. Generate a token under *My Account → Security* and store it in Jenkins as a **Secret text** credential with ID `SONAR_TOKEN`.
4. Ensure the Jenkins agent can reach `https://sq.casapomininegri.it`, has a JRE (`java -version`), and `curl`/`unzip` if SonarScanner is not preinstalled.
5. For README badges: after the first analysis, verify badge URLs under *Project → Project Information → Get project badges*; if badges do not load publicly, allow project badge access in *Administration → Configuration → General Settings → Security*.

The pipeline downloads SonarScanner automatically when it is not installed on the agent. If the server uses a self-signed TLS certificate, install the CA on the Jenkins agent or configure `SONAR_SCANNER_OPTS` with a truststore.

SonarQube is **informational only**: findings on the server never block lint, test, build, or PyPI publish, and scanner errors (token, network, server down) mark the SonarQube stage as **unstable** while the overall build still succeeds. There is no Quality Gate stage in the Jenkinsfile.

## Release process

Releases are automated with helper scripts and published by Jenkins when a version tag is pushed.

> **Both release scripts must be run from `main` with a clean working tree, and
> both refuse to run otherwise.**
>
> `release.sh` pushes to `main` (via the `RELEASE_BRANCH` constant, the single
> source of truth shared by the help text, the validation and the push), while
> the release commit is created on whatever branch is checked out. From a feature
> branch the version bump and `CHANGELOG.md` entry would be committed there while
> `git push origin main` reported `Everything up-to-date` and pushed nothing — only
> the `vX.Y.Z` tag would reach the remote. Jenkins builds from the tag, so PyPI
> would get the release while `main` never received the bump, leaving the next
> release's `v<version>..HEAD` range incomplete.
>
> `ghrelease.sh` needs `main` for a different reason: the release notes are parsed
> from the *working tree* while the release is attached to a *tag*. A stale
> checkout would publish notes that exist in no commit and in no tag — and because
> `git rev-parse vX.Y.Z^{commit}` succeeds on any branch once tags are fetched, the
> branch check is the only thing standing between the two.
>
> `validate_branch()` aborts with a non-zero exit on any branch but `main`,
> including on the `--push-only` and `--github-release` paths. There is no
> `development` branch in this repository; `main` is the release branch.

1. **Prepare the release** (bumps `asteroidpy/version.py`, compiles locale catalogs, prepends `CHANGELOG.md`, commits, tags, and pushes):

   ```bash
   git checkout main
   git status --short   # must be empty
   ./release.sh --patch    # or --minor, --major, or an explicit X.Y.Z
   ```

   Preview without changes: `./release.sh --dry-run --patch`

2. **Jenkins** detects the new `vX.Y.Z` tag, runs tests, builds the wheel/sdist, validates the package, and publishes to [PyPI](https://pypi.org/project/Asteroidpy/).

3. **Create the GitHub release** (release notes taken from the top `CHANGELOG.md` entry), still on `main`, after Jenkins has finished:

   ```bash
   ./ghrelease.sh
   ```

   `./ghrelease.sh` is a thin wrapper around `./release.sh --github-release`, so
   both share one implementation of the preflight checks and the release-branch
   enforcement rather than keeping two drifting copies. Either entry point works,
   and `./release.sh --github-release --dry-run` previews it.

### Preflight checks

`preflight_base()` runs as the **first** statement of the script — before the banner and before argument parsing, which already shells out to `grep`. A missing tool is therefore always reported as a missing tool, never as a confusing failure later:

| | Behaviour when absent |
|------|----------------------|
| `git`, `sed`, `grep`, `awk`, `cat`, `head`, `date`, `tr` | **blocking** — aborts with the full list of what is missing and a hint per tool, before anything is modified |
| `msgfmt` (gettext) | **non-blocking** — warns, because the release stays valid and only the compiled `.mo` catalogs can go stale |
| `gh`, only for `--github-release` | **blocking** — aborts with the install URL |
| `gh auth login`, only for `--github-release` | **blocking** — presence is not enough; an unauthenticated `gh` would otherwise fail only after the notes were assembled |

All missing required tools are reported in one run, so a bare environment is not
fixed one package at a time.

Two further checks run after the preflight: the release branch
(`validate_branch()`) and the working tree, via
`git status --porcelain --untracked-files=no` rather than
`git diff-index --quiet HEAD --`. The latter reads the index stat cache and can
report a dirty tree that `git status` considers clean, blocking a legitimate
release. Untracked files stay excluded because `release.sh` stages an explicit
path list, so scratch files cannot affect the release.

### Recovery paths

- `./release.sh --push-only X.Y.Z` — re-push the branch and tag after a failed push. Still refuses to run off `main`.
- `./release.sh --github-release` — recreate the GitHub release if step 3 failed. It also asserts the tag is an ancestor of `main`, so a release cut from the wrong branch cannot be papered over by re-running it.

Manual alternative (without the scripts): update `asteroidpy/version.py` and `CHANGELOG.md`, compile `.mo` files under `asteroidpy/locales/`, commit, tag (`git tag vX.Y.Z`), push the branch and tag, then run `./ghrelease.sh` after Jenkins finishes the PyPI upload.

## Pull request checklist

- [ ] `pytest -q` passes
- [ ] `ruff check asteroidpy/ tests/` and `mypy asteroidpy/` are clean
- [ ] `isort --check asteroidpy/ tests/` and `black --check asteroidpy/ tests/` are clean
- [ ] `(cd docs && make html)` succeeds with no warnings, if you touched `docs/` or docstrings
- [ ] `README.md` and `docs/source/*.rst` updated together, if you changed a feature, config option, language, or public function
- [ ] Compiled `.mo` catalogs regenerated, if you changed `.po` files
- [ ] A `CHANGELOG.md` entry via a conventional commit, if the maintainers are cutting a release
