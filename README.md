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

## Configuration

Configuration is stored in a single INI file named `.asteroidpy`, in the application config directory returned by [platformdirs](https://github.com/platformdirs/platformdirs) (for example `~/.config/asteroidpy/` on Linux, `~/Library/Application Support/asteroidpy/` on macOS, and `%LOCALAPPDATA%\asteroidpy\` on Windows). Legacy installs may still have a copy at `~/.asteroidpy`, which is migrated automatically on first run.

Use the in-app **Configuration** menu to change:

| Option | Description |
|--------|-------------|
| **Observatory** | Latitude, longitude, altitude, site and observer names, MPC observatory code |
| **Virtual horizon** | Minimum altitude (in degrees) per cardinal direction for visibility |
| **Language** | Interface language (English, Italiano, Deutsch, Français, Español, Português) |

The same values can be edited by hand in the INI file. It has three sections:

| Section | Options |
|---------|---------|
| `[General]` | `lang` — interface language |
| `[Planner]` | `max_nights` — how many nights the best-night planner ranks; `w_cloud`, `w_seeing`, `w_transparency`, `w_moon` — relative weights, normalized to sum to 1 |
| `[Observatory]` | `place`, `latitude`, `longitude`, `altitude`, `obs_name`, `observer_name`, `mpc_code`, `nord_altitude`, `east_altitude`, `south_altitude`, `west_altitude` |

Missing options are filled from the built-in defaults on every load, so a partial or older file stays usable. The `[Planner]` weights are read from the file only — there is no in-app screen for them yet; they control the **Best upcoming night** score, whose only inputs are cloud cover, seeing, transparency and Moon illumination. Nights with any precipitation are discarded outright.

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

Le feature mancanti, raggruppate per area. Ogni voce ha un prompt pronto
all'esecuzione in [`PROMPTS.md`](PROMPTS.md), con contesto, criteri di accettazione
e comandi di verifica.

### Dati e output

- [ ] **A1** Cache persistente delle risposte di rete con TTL, con cache del token del form MPC e hit/miss/failover distinti
- [ ] **A2** Export CSV/JSON/testo su file da tutte le schermate tabellari, con percorso esplicito e copia negli appunti
- [ ] **A3** Modalità offline: fallback su cache, banner di stato e distinzione tra dato fresco, dato in cache ed errore

### Interfaccia a riga di comando

- [ ] **B1** Subcommand `argparse` (`weather`, `neocp`, `ephemeris`, `targets`, `twilight`, `best-night`), `--version`, `--json`, `python -m asteroidpy`

### Watchlist e registro osservazioni

- [ ] **C1** Watchlist oggetti persistente, con aggiunta da ogni tabella dei risultati
- [ ] **C2** Piani di sessione salvati e ripresi, con collegamento al punteggio meteo della notte
- [ ] **C3** Registro delle osservazioni ed export nel formato accettato dal MPC

### Grafici

- [ ] **D1** Curva di altitudine nel tempo, sky plot della notte con orizzonte virtuale, barre del punteggio delle notti candidate

### Alert

- [ ] **E1** Alert programmati e persistenti: notifica interna, email SMTP, webhook, con deduplica

### Debito tecnico

- [x] **F1** Schermata Osservatorio: coordinate mostrate in chiaro via `observatory_summary_lines`, etichette di `print_obs_config` passate da gettext e presenti in tutti i cataloghi
- [ ] **F2** Rimozione del frontend legacy orfano (`_config_menus.py`, `_schedule_menus.py`, `_input.py`), irraggiungibile e già divergente dalla TUI
- [ ] **F3** Test della TUI: oggi le 19 schermate non hanno nessun test
- [ ] **F4** Deduplicazione di `test_configuration.py` e `test_configuration_unittest.py`
- [ ] **F5** Stage docs e matrix Python 3.11–3.14 nel `Jenkinsfile`
- [ ] **F6** Rimozione del token CSRF fallback hardcodato in `scheduling.py` e segnalazione esplicita del fallimento
- [ ] **F7** Parametri mancanti: numero di punti di efemeride, numero di notti, prefill dell'orizzonte virtuale
- [ ] **F8** Retry con backoff e gestione tipizzata degli errori di rete
- [ ] **F9** Editor in-app dei pesi del planner: `[Planner] w_cloud`, `w_seeing`, `w_transparency`, `w_moon` e `max_nights` sono oggi modificabili solo editando l'INI a mano

Ordine di esecuzione suggerito:

```
F1 → F9 → F7 → F2 → F6 → A1 → A2 → A3 → B1 → D1 → C1 → C2 → C3 → E1 → F3 → F4 → F5 → F8
```

---

## License

AsteroidPy is licensed under the [GPL-3.0](LICENSE) license.
