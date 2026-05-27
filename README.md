# AsteroidPy

[![GitHub](https://img.shields.io/github/license/ziriuz84/asteroidpy)](https://github.com/ziriuz84/asteroidpy)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/ziriuz84/asteroidpy/issues)
[![Quality Gate](https://sq.casapomininegri.it/api/project_badges/measure?project=ziriuz84_asteroidpy_1d603420-1b43-4943-86f6-ab01cd7be87b&metric=alert_status)](https://sq.casapomininegri.it/dashboard?id=ziriuz84_asteroidpy_1d603420-1b43-4943-86f6-ab01cd7be87b)
[![Coverage](https://sq.casapomininegri.it/api/project_badges/measure?project=ziriuz84_asteroidpy_1d603420-1b43-4943-86f6-ab01cd7be87b&metric=coverage)](https://sq.casapomininegri.it/dashboard?id=ziriuz84_asteroidpy_1d603420-1b43-4943-86f6-ab01cd7be87b)

AsteroidPy is a command-line tool for astronomers to schedule and manage asteroid observations. It integrates with the Minor Planet Center and other astronomical data sources to provide ephemerides, NEO confirmation candidates, weather forecasts, and observing aids—all from an interactive terminal UI built with [Textual](https://textual.textualize.io/).

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [FAQ](#faq)
- [Data Sources](#data-sources)
- [For Contributors](#for-contributors)
  - [Project architecture](#project-architecture)
  - [How to add a translation](#how-to-add-a-translation)
  - [Continuous integration (Jenkins)](#continuous-integration-jenkins)
  - [Release process](#release-process)
- [Release History](#release-history)
- [License](#license)

---

## Features

| Feature | Description |
|--------|-------------|
| **Weather forecast** | Astronomical weather (cloud cover, seeing, transparency) up to 72 hours via 7Timer |
| **Observation scheduling** | Plan sessions with target lists and visibility windows |
| **NEOcp candidates** | List and filter Near-Earth Object candidates from the MPC Confirmation Page |
| **Object ephemeris** | Retrieve detailed ephemeris data for any minor body |
| **Twilight & Sun/Moon** | Civil, nautical, and astronomical twilight; rise/set times |
| **Virtual horizon** | Simulate horizon obstructions for visibility calculations |

---

## Requirements

- **Python** 3.9 or later
- **pip** (or another Python package manager)

AsteroidPy runs on **Linux**, **macOS**, and **Windows**.

On **Windows**, use [Windows Terminal](https://github.com/microsoft/terminal) (recommended) or another modern terminal for the Textual UI. The first `pip install` may take several minutes because scientific dependencies (`astropy`, `lxml`, and related packages) download platform-specific wheels. Python **3.10–3.12** from [python.org](https://www.python.org/downloads/) is the most reliable choice on Windows.

---

## Installation

### From PyPI

With Python 3.9+ and a virtual environment activated (recommended):

```bash
pip install asteroidpy
```

See the package on [PyPI](https://pypi.org/project/Asteroidpy/).

On Windows, after installation the `asteroidpy` command is available in your virtual environment's `Scripts` folder (for example `.venv\Scripts\asteroidpy.exe`).

### From source

1. Clone the repository:

   ```bash
   git clone https://github.com/ziriuz84/asteroidpy.git
   cd asteroidpy
   ```

2. *(Recommended)* Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. Install in editable mode:

   ```bash
   pip install -e .
   ```

   Or in normal mode:

   ```bash
   pip install .
   ```

---

## Quick Start

Run the application:

```bash
asteroidpy
```

On first launch, AsteroidPy creates a config file with default settings. Use the **Configuration** menu to set:

- **Observatory**: coordinates, altitude, MPC code
- **Virtual horizon**: minimum altitude per cardinal direction
- **General**: interface language

---

## Configuration

Configuration is stored in a single INI file named `.asteroidpy`, in the application config directory returned by [platformdirs](https://github.com/platformdirs/platformdirs) (for example `~/.config/asteroidpy/` on Linux, `~/Library/Application Support/asteroidpy/` on macOS, and `%LOCALAPPDATA%\asteroidpy\` on Windows). Legacy installs may still have a copy at `~/.asteroidpy`, which is migrated automatically on first run.

Use the in-app **Configuration → General** menu to change:

| Option | Description |
|--------|-------------|
| **Observatory** | Latitude, longitude, altitude, MPC observatory code |
| **Virtual horizon** | Minimum altitude (in degrees) per cardinal direction for visibility |
| **Language** | Interface language (English, Italiano, Deutsch, Français, Español, Português) |

---

## FAQ

**Where do I find my MPC observatory code?**  
The [Minor Planet Center](https://www.minorplanetcenter.net/iau/lists/ObsCodes.html) publishes the list of observatory codes. If your site is not listed, use `XXX` or another temporary code until you register it with the MPC.

**Why do ephemerides differ from Stellarium or other tools?**  
Small differences can arise from different orbital elements, epoch dates, or time handling. AsteroidPy uses MPC data directly; ensure your observatory coordinates and time (UTC vs local) match across tools.

**The application fails to start or shows errors.**  
Check that all dependencies are installed (`pip install asteroidpy` from PyPI, or `pip install .` from a source checkout), that the config directory is writable (see [Configuration](#configuration) for the platform-specific path), and that you have internet access (required for weather and ephemeris queries). If the config file is corrupted, remove `.asteroidpy` from that config directory and let the app recreate it on next run.

**Which languages are supported?**  
English (default), Italiano, Deutsch, Français, Español, Português. Change the language in **Configuration → General** → **Language**. PyPI wheels ship with compiled `.mo` catalogs for all supported languages. When working from a source checkout, only locales with compiled `.mo` files are listed as selectable; if a folder under `asteroidpy/locales/` has only a `base.po`, the UI may show a notice when opening the language screen—compile with `msgfmt` so the locale appears as a proper option.

---

## Data Sources

AsteroidPy relies on:

- **[7Timer](https://7timer.info)** — meteorological forecasts (cloud cover, seeing, transparency)
- **[Minor Planet Center (MPC)](https://www.minorplanetcenter.net/)** — ephemerides and NEO Confirmation Page data

---

## For Contributors

Thank you for considering contributing to AsteroidPy. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

### Types of contributions we welcome

- **Code**: bug fixes, new features, refactoring
- **QA**: bug reports with repro steps and environment details
- **Documentation**: improvements to this README, docstrings, or Sphinx docs
- **Community**: presenting the project, organizing local meetups

### Development setup

1. Clone the repository and install in editable mode (see [Installation](#installation)).

2. Install development dependencies (optional, for tests and linting):

   ```bash
   pip install -e ".[dev]"
   ```

   Or install tools individually: `pytest`, `ruff`, `mypy`, `black`, `isort`.

3. Run the test suite:

   ```bash
   pytest -q
   ```

   Run a single test:

   ```bash
   pytest tests/test_scheduling.py::test_name -q
   ```

4. Lint and type-check:

   ```bash
   ruff check .
   mypy .
   ```

5. Build the package:

   ```bash
   python -m build
   ```

   Before building a release wheel, compile locale catalogs if you changed `.po` files:

   ```bash
   msgfmt -o asteroidpy/locales/en/LC_MESSAGES/base.mo asteroidpy/locales/en/LC_MESSAGES/base.po
   # repeat for other locales, or use ./release.sh which compiles them automatically
   ```

### Continuous integration (Jenkins)

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

Successful builds archive `dist/*` (and `coverage.xml`) as Jenkins artifacts. GitHub Actions workflows are not used; Jenkins is the single CI/CD path for builds and PyPI publishing.

#### SonarQube setup (one-time)

Before the SonarQube stage can run on Jenkins:

1. Create or import the project on [sq.casapomininegri.it](https://sq.casapomininegri.it) and note its project key (currently `ziriuz84_asteroidpy_1d603420-1b43-4943-86f6-ab01cd7be87b`).
2. Confirm `sonar.projectKey` in [`sonar-project.properties`](sonar-project.properties) matches the SonarQube project.
3. Generate a token under *My Account → Security* and store it in Jenkins as a **Secret text** credential with ID `SONAR_TOKEN`.
4. Ensure the Jenkins agent can reach `https://sq.casapomininegri.it`, has a JRE (`java -version`), and `curl`/`unzip` if SonarScanner is not preinstalled.
5. For README badges: after the first analysis, verify badge URLs under *Project → Project Information → Get project badges*; if badges do not load publicly, allow project badge access in *Administration → Configuration → General Settings → Security*.

The pipeline downloads SonarScanner automatically when it is not installed on the agent. If the server uses a self-signed TLS certificate, install the CA on the Jenkins agent or configure `SONAR_SCANNER_OPTS` with a truststore.

SonarQube is **informational only**: findings on the server never block lint, test, build, or PyPI publish, and scanner errors (token, network, server down) mark the SonarQube stage as **unstable** while the overall build still succeeds. There is no Quality Gate stage in the Jenkinsfile.

### Code style

- **Imports**: standard library → third-party → local; explicit imports only
- **Formatting**: Black for style; isort for import order
- **Types**: type hints on public APIs; snake_case for functions/variables; CamelCase for classes
- **Errors**: avoid bare `except`; raise or propagate clear exceptions; validate inputs early
- **Tests**: small, isolated tests; prefer parameterized tests where sensible

### Getting involved

- Browse [open issues](https://github.com/ziriuz84/asteroidpy/issues) and comment or pick one to work on
- Open issues for bugs or feature ideas—the more detail, the better
- Pull requests are welcome; please ensure tests pass and style is consistent

### Project architecture

```
asteroidpy/
├── __init__.py       # Entry point; loads config, launches interface
├── interface/        # Textual TUI, gettext setup (legacy menu helpers retained)
├── scheduling.py     # Ephemerides, weather, NEOcp, twilight
├── configuration.py  # Observatory config, horizon, language
└── locales/          # gettext translations (en, it, de, fr, es, pt), shipped in PyPI wheels
```

- **`interface`** — Main entry for the interactive UI (Textual screens). Loads config, sets up gettext, and delegates to `scheduling` for ephemeris/weather/NEOcp and to `configuration` for settings.
- **`scheduling`** — Astronomy logic: MPC queries, 7Timer weather, twilight, Sun/Moon ephemeris. Uses `configuration.load_config()` to read observatory data.
- **`configuration`** — Persists and loads settings via platformdirs; handles observatory coordinates, virtual horizon, and language. Used by both `interface` and `scheduling`.

### How to add a translation

AsteroidPy uses [GNU gettext](https://www.gnu.org/software/gettext/) with a single catalog `base`. Translations live under `asteroidpy/locales/<lang>/LC_MESSAGES/`.

1. Create a new locale directory:
   ```bash
   mkdir -p asteroidpy/locales/nl/LC_MESSAGES
   ```

2. Copy and adapt an existing `.po` file, or create one from the template:
   ```bash
   cp asteroidpy/locales/it/LC_MESSAGES/base.po asteroidpy/locales/nl/LC_MESSAGES/base.po
   ```
   Edit `asteroidpy/locales/nl/LC_MESSAGES/base.po`, set `Language: nl`, and translate all `msgstr` entries.

3. Compile the `.po` file into a `.mo` file (required for the language to appear in the menu when running from source):
   ```bash
   msgfmt -o asteroidpy/locales/nl/LC_MESSAGES/base.mo asteroidpy/locales/nl/LC_MESSAGES/base.po
   ```
   The `msgfmt` command comes with the gettext package (`gettext` on most Linux distros; on Windows, install via [MSYS2](https://www.msys2.org/) or Chocolatey).
   Until the `.mo` exists, text from that `.po` is not used by gettext; the interactive UI may notify you once per incomplete locale under **General** → **Language**.

4. The new language will appear in **Configuration → General** after restart.

To add or update translatable strings for all locales, update `asteroidpy/locales/base.pot` (e.g. with `xgettext` or `pybabel`), then merge into each `.po` with `msgmerge`, translate, and recompile with `msgfmt`.

### Release process

Releases are automated with helper scripts and published by Jenkins when a version tag is pushed.

1. **Prepare the release** (bumps `asteroidpy/version.py`, compiles locale catalogs, prepends `CHANGELOG.md`, commits, tags, and pushes):

   ```bash
   ./release.sh --patch    # or --minor, --major, or an explicit X.Y.Z
   ```

   Preview without changes: `./release.sh --dry-run --patch`

2. **Jenkins** detects the new `vX.Y.Z` tag, runs tests, builds the wheel/sdist, validates the package, and publishes to [PyPI](https://pypi.org/project/Asteroidpy/).

3. **Create the GitHub release** (release notes taken from the top `CHANGELOG.md` entry):

   ```bash
   ./ghrelease.sh
   ```

Manual alternative (without the scripts): update `asteroidpy/version.py` and `CHANGELOG.md`, compile `.mo` files under `asteroidpy/locales/`, commit, tag (`git tag vX.Y.Z`), push the branch and tag, then run `./ghrelease.sh` after Jenkins finishes the PyPI upload.

---

## Release History

See [CHANGELOG.md](CHANGELOG.md).

---

## TODO

- [ ] NEOcp alert integration
- [ ] Observation registration

---

## License

AsteroidPy is licensed under the [GPL-3.0](LICENSE) license.
