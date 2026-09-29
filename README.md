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
- [Keyboard Navigation](#keyboard-navigation)
- [Configuration](#configuration)
  - [Response cache](#response-cache)
- [FAQ](#faq)
- [Data Sources](#data-sources)
- [For Contributors](#for-contributors)
- [Release History](#release-history)
- [License](#license)

---

## Features

| Feature | Description |
|--------|-------------|
| **Weather forecast** | Astronomical weather (cloud cover, seeing, transparency) via 7Timer, over a horizon of 6–168 hours (72 by default) and in °C or °F |
| **Observation scheduling** | Plan sessions with target lists and visibility windows |
| **NEOcp candidates** | List and filter Near-Earth Object candidates from the MPC Confirmation Page |
| **Object ephemeris** | Retrieve detailed ephemeris data for any minor body, from 1 to 10000 points |
| **Twilight & Sun/Moon** | Civil, nautical, and astronomical twilight; rise/set times |
| **Best-upcoming-night planner** | Rank the upcoming astronomical nights by observing quality (cloud cover, seeing, transparency, Moon illumination) with configurable weights |
| **Virtual horizon** | Simulate horizon obstructions for visibility calculations (0–90° per cardinal direction) |
| **Response cache** | Keep recent MPC and 7Timer answers on disk with a per-source time-to-live, so a repeated run needs no network |

---

## Requirements

- **Python** 3.11 or later (supported: 3.11, 3.12, 3.13 and 3.14)
- **pip** (or another Python package manager)

AsteroidPy runs on **Linux**, **macOS**, and **Windows**.

The 3.11 floor comes from the dependency stack, not the application code: `astropy` 7 and later require Python 3.11 or newer, and `platformdirs` and `requests` require 3.10. Pinning the floor at 3.11 guarantees every supported interpreter resolves the same versions of the scientific stack, instead of silently falling back to a several-years-old `astropy` on older interpreters.

On **Windows**, use [Windows Terminal](https://github.com/microsoft/terminal) (recommended) or another modern terminal for the Textual UI. The first `pip install` may take several minutes because scientific dependencies (`astropy`, `lxml`, and related packages) download platform-specific wheels. A current [python.org](https://www.python.org/downloads/) build is the most reliable choice on Windows.

---

## Installation

### From PyPI

With Python 3.11+ and a virtual environment activated (recommended):

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

- **Observatory**: coordinates, altitude, site and observer names, MPC code
- **Virtual horizon**: minimum altitude per cardinal direction
- **General**: interface language

The **Observation scheduling** menu offers weather, MPC observing target list, NEOcp list, object ephemeris, twilight times, and best upcoming night.

---

## Keyboard Navigation

Every screen is fully drivable from the keyboard; the mouse is optional.

| Key | Action |
|-----|--------|
| `Up` / `Down` | Move the focus to the previous/next widget, exactly like `Shift+Tab` / `Tab` |
| `Tab` / `Shift+Tab` | Move the focus forward/backward |
| `0`–`9` | Activate the menu entry carrying that number in its label (e.g. `1 - Configuration`, `0 - Back to main menu`) |
| `Escape` | Go back to the previous screen |
| `Ctrl+Q` | Quit, from the main menu |

The numbers are always visible in the button labels, so the shortcut for a screen is readable without leaving it. A digit with no matching entry — or one whose entry is disabled while a background query runs — is simply ignored.

Arrow keys also work while filling in a form, and typing digits into a text field is never intercepted: input widgets consume printable characters before the shortcut is considered.

---

## Configuration

Configuration is stored in a single INI file named `.asteroidpy`, in the application config directory returned by [platformdirs](https://github.com/platformdirs/platformdirs) (for example `~/.config/asteroidpy/` on Linux, `~/Library/Application Support/asteroidpy/` on macOS, and `%LOCALAPPDATA%\asteroidpy\` on Windows). Legacy installs may still have a copy at `~/.asteroidpy`, which is migrated automatically on first run.

Use the in-app **Configuration** menu to change:

| Option | Description |
|--------|-------------|
| **Observatory** | Latitude, longitude, altitude, site and observer names, MPC observatory code |
| **Virtual horizon** | Minimum altitude (in degrees) per cardinal direction for visibility |
| **Planner** | Number of nights the best-night planner ranks, and the relative weights of cloud cover, seeing, transparency and Moon illumination |
| **Language** | Interface language (English, Italiano, Deutsch, Français, Español, Português) |
| **Clear cache** | Empties the on-disk response cache, so the next query really reaches the MPC and 7Timer |

The same values can be edited by hand in the INI file. It has three sections:

| Section | Options |
|---------|---------|
| `[General]` | `lang` — interface language |
| `[Planner]` | `max_nights` — how many nights the best-night planner ranks; `w_cloud`, `w_seeing`, `w_transparency`, `w_moon` — relative weights, normalized to sum to 1 |
| `[Observatory]` | `place`, `latitude`, `longitude`, `altitude`, `obs_name`, `observer_name`, `mpc_code`, `nord_altitude`, `east_altitude`, `south_altitude`, `west_altitude` |

Missing options are filled from the built-in defaults on every load, so a partial or older file stays usable. The `[Planner]` weights control the **Best upcoming night** score, whose only inputs are cloud cover, seeing, transparency and Moon illumination; nights with any precipitation are discarded outright. The **Configuration → Planner** screen edits `max_nights` and the four weights, shows the values that will really be applied (the weights divided by their sum) and previews the score of the next few nights without saving.

### Response cache

Every request that does not go through astroquery is cached on disk, so a repeated run is answered without touching the network and a temporary outage shows the last known answer instead of an empty table. The cache lives in the **user cache** directory, not next to the configuration file — for example `~/.cache/asteroidpy/http/` on Linux, `~/Library/Caches/asteroidpy/http/` on macOS, and `%LOCALAPPDATA%\asteroidpy\http\` on Windows.

Each source has its own time-to-live, because they do not go stale at the same rate:

| Source | Cache lifetime | Why |
|--------|----------------|-----|
| MPC What's Observable form token | 15 minutes | A Rails authenticity token is perishable |
| MPC NEOcp feed and confirm ephemerides | 15 minutes | A live feed: the point is what is new right now |
| MPC What's Observable target table | 15 minutes | Describes the sky at a single instant |
| 7Timer weather forecast | 3 hours | 7Timer `astro` itself refreshes twice a day |

Object ephemerides and MPC observatory codes are not cached here: astroquery already stores those responses for a week.

Delete the cache by hand, or from the app with **Configuration → General → Clear cache**. Setting `ASTEROIDPY_NO_CACHE=1` turns it off entirely, which is useful when comparing runs or filing a bug report.

---

## FAQ

**Where do I find my MPC observatory code?**  
The [Minor Planet Center](https://www.minorplanetcenter.net/iau/lists/ObsCodes.html) publishes the list of observatory codes. The default is `500` (Geocentric), which tells AsteroidPy to use your own latitude/longitude/altitude for the NEOcp ephemerides. If your site is not listed, keep `500` or use another temporary code until you register it with the MPC.

**Why do ephemerides differ from Stellarium or other tools?**  
Small differences can arise from different orbital elements, epoch dates, or time handling. AsteroidPy uses MPC data directly; ensure your observatory coordinates and time (UTC vs local) match across tools.

**The application fails to start or shows errors.**  
Check that all dependencies are installed (`pip install asteroidpy` from PyPI, or `pip install .` from a source checkout), that the config directory is writable (see [Configuration](#configuration) for the platform-specific path), and that you have internet access (required for weather and ephemeris queries). If the config file is corrupted, remove `.asteroidpy` from that config directory and let the app recreate it on next run.

**Which languages are supported?**  
English (default), Italiano, Deutsch, Français, Español, Português. Change the language in **Configuration → General** → **Language**. PyPI wheels ship with compiled `.mo` catalogs for all supported languages. When working from a source checkout, only locales with compiled `.mo` files are listed as selectable; if a folder under `asteroidpy/locales/` has only a `base.po`, the UI may show a notice when opening the language screen—compile with `msgfmt` so the locale appears as a proper option.

**A query returned stale data, or the network is down.**  
Every non-astroquery request is served from the [response cache](#response-cache) first, so a query repeated within its time-to-live makes no network call at all, and a failed request falls back to the last stored answer rather than to an empty table. If you need the data as of right now, use **Configuration → General → Clear cache**, or set `ASTEROIDPY_NO_CACHE=1` to bypass the cache entirely.

---

## Data Sources

AsteroidPy relies on:

- **[7Timer](https://7timer.info)** — meteorological forecasts (cloud cover, seeing, transparency)
- **[Minor Planet Center (MPC)](https://www.minorplanetcenter.net/)** — ephemerides and NEO Confirmation Page data

---

## For Contributors

Contributions are welcome — bug fixes, new features, documentation, and
translations all count. Please read the [Code of Conduct](CODE_OF_CONDUCT.md)
first.

The full contributor guide lives in **[CONTRIBUTING.md](CONTRIBUTING.md)**:

- [Development setup and the lint gate](CONTRIBUTING.md#development-setup)
- [Code style](CONTRIBUTING.md#code-style)
- [Project architecture](CONTRIBUTING.md#project-architecture)
- [How to add a translation](CONTRIBUTING.md#how-to-add-a-translation)
- [Continuous integration (Jenkins)](CONTRIBUTING.md#continuous-integration-jenkins)
- [Release process](CONTRIBUTING.md#release-process)

New to the project? Start with the [open issues](https://github.com/ziriuz84/asteroidpy/issues)
and the [bug report](.github/ISSUE_TEMPLATE/bug_report.md) /
[feature request](.github/ISSUE_TEMPLATE/feature_request.md) templates.

---

## Release History

See [CHANGELOG.md](CHANGELOG.md).

---

## TODO

The missing features, grouped by area. Every entry has a ready-to-run prompt in
[`PROMPTS.md`](PROMPTS.md), with context, acceptance criteria and verification
commands.

### Data and output

- [ ] **A1** Persistent cache of network responses with a TTL, with a dedicated cache for the MPC form token and distinct hit/miss/failover counters
- [ ] **A2** CSV/JSON/text export to file from every table screen, with an explicit path and a copy-to-clipboard
- [ ] **A3** Offline mode: cache fallback, status banner and a distinction between fresh data, cached data and errors

### Command-line interface

- [ ] **B1** `argparse` subcommands (`weather`, `neocp`, `ephemeris`, `targets`, `twilight`, `best-night`), `--version`, `--json`, `python -m asteroidpy`

### Watchlist and observation log

- [ ] **C1** Persistent object watchlist, with the ability to add entries from every results table
- [ ] **C2** Saved and resumable session plans, linked to the night's weather score
- [ ] **C3** Observation log and export in the format accepted by the MPC

### Charts

- [ ] **D1** Altitude curve over time, night sky plot with the virtual horizon, score bars for the candidate nights

### Alerts

- [ ] **E1** Scheduled, persistent alerts: in-app notification, SMTP email, webhook, with deduplication

### Technical debt

- [x] **F1** Observatory screen: coordinates shown in clear text via `observatory_summary_lines`, `print_obs_config` labels passed through gettext and present in every catalog
- [x] **F2** Removed the orphaned legacy frontend (`_config_menus.py`, `_schedule_menus.py`, `_input.py`) and `main_menu`, unreachable and already diverged from the TUI
- [ ] **F3** TUI tests: today none of the 19 screens has a test
- [ ] **F4** Deduplication of `test_configuration.py` and `test_configuration_unittest.py`
- [ ] **F5** Docs stage and Python 3.11–3.14 matrix in the `Jenkinsfile`
- [x] **F6** Removal of the hardcoded CSRF fallback token in `scheduling.py` and explicit reporting of the failure
- [x] **F7** Missing parameters: `object_ephemeris(number=…)` with validation, number of points and of nights in the screens, hours and temperature unit on the weather screen, prefill and 0–90° validation of the virtual horizon
- [ ] **F8** Retry with backoff and typed handling of network errors
- [x] **F9** In-app editor for the planner weights: **Configuration → Planner** screen with `max_nights` and the four weights, validation shared with the loader, normalized weights shown, and a score preview

Suggested execution order:

```
F1 → F9 → F7 → F2 → F6 → A1 → A2 → A3 → B1 → D1 → C1 → C2 → C3 → E1 → F3 → F4 → F5 → F8
```

---

## License

AsteroidPy is licensed under the [GPL-3.0](LICENSE) license.
