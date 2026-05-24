# AsteroidPy

[![GitHub](https://img.shields.io/github/license/ziriuz84/asteroidpy)](https://github.com/ziriuz84/asteroidpy)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/ziriuz84/asteroidpy/issues)

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

---

## Installation

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

On first launch, AsteroidPy creates a config directory at `~/.asteroidpy` with default settings. Use the **Configuration** menu to set:

- **Observatory**: coordinates, altitude, MPC code
- **Virtual horizon**: minimum altitude per cardinal direction
- **General**: interface language

---

## Configuration

Configuration is stored in `~/.asteroidpy`. Use the in-app **Configuration → General** menu to change:

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
Check that all dependencies are installed (`pip install .`), that `~/.asteroidpy` is writable, and that you have internet access (required for weather and ephemeris queries). If the config file is corrupted, you can remove `~/.asteroidpy` and let the app recreate it on next run.

**Which languages are supported?**  
English (default), Italiano, Deutsch, Français, Español, Português. Change the language in **Configuration → General** → **Language**. Only locales with compiled `.mo` files are listed as selectable; if a folder under `locales/` has only a `base.po`, the UI may show a notice when opening the language screen—compile with `msgfmt` so the locale appears as a proper option.

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
   pip install pytest ruff mypy black isort
   ```

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
└── locales/          # gettext translations (en, it, de, fr, es, pt)
```

- **`interface`** — Main entry for the interactive UI (Textual screens). Loads config, sets up gettext, and delegates to `scheduling` for ephemeris/weather/NEOcp and to `configuration` for settings.
- **`scheduling`** — Astronomy logic: MPC queries, 7Timer weather, twilight, Sun/Moon ephemeris. Uses `configuration.load_config()` to read observatory data.
- **`configuration`** — Persists and loads settings in `~/.asteroidpy`; handles observatory coordinates, virtual horizon, and language. Used by both `interface` and `scheduling`.

### How to add a translation

AsteroidPy uses [GNU gettext](https://www.gnu.org/software/gettext/) with a single catalog `base`. Translations live under `locales/<lang>/LC_MESSAGES/`.

1. Create a new locale directory:
   ```bash
   mkdir -p locales/nl/LC_MESSAGES
   ```

2. Copy and adapt an existing `.po` file, or create one from the template:
   ```bash
   cp locales/it/LC_MESSAGES/base.po locales/nl/LC_MESSAGES/base.po
   ```
   Edit `locales/nl/LC_MESSAGES/base.po`, set `Language: nl`, and translate all `msgstr` entries.

3. Compile the `.po` file into a `.mo` file (required for the language to appear in the menu):
   ```bash
   msgfmt -o locales/nl/LC_MESSAGES/base.mo locales/nl/LC_MESSAGES/base.po
   ```
   The `msgfmt` command comes with the gettext package (`gettext` on most Linux distros).
   Until the `.mo` exists, text from that `.po` is not used by gettext; the interactive UI may notify you once per incomplete locale under **General** → **Language**.

4. The new language will appear in **Configuration → General** after restart.

To add or update translatable strings for all locales, update `locales/base.pot` (e.g. with `xgettext` or `pybabel`), then merge into each `.po` with `msgmerge`, translate, and recompile with `msgfmt`.

### Release process

1. Update `asteroidpy/version.py` (`__version__`, used by setuptools and the UI); keep `setup.py` in sync if you still rely on it.
2. Add the corresponding entry to `CHANGELOG.md` under a new `[X.Y.Z]` heading with date and link to the tag.
3. Run tests and build:
   ```bash
   pytest -q
   python -m build
   ```
4. Commit the version bump and changelog, then create and push a tag:
   ```bash
   git tag vX.Y.Z -m "Release vX.Y.Z"
   git push origin main --tags
   ```
   (Use `git tag -s` for a signed tag if you have GPG configured.)
5. Create a release on GitHub from the new tag and attach the built artifacts (e.g. from `dist/`).

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
