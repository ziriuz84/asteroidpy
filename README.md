# AsteroidPy

A simple tool to manage Asteroid observations and measurements

![GitHub](https://img.shields.io/github/license/ziriuz84/asteroidpy)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

## Description

AsteroidPy is a simple tool to help astronomers schedule and manage asteroidal observations and measurements. It uses the main sources in minor planets research to provide accurate predictions of ephemerides and NEOcp candidates.

## Features

- Weather forecast
- Observation scheduling
- NEOcp candidates listing
- Object ephemeris
- Twilight, Sun and Moon times
- Virtual horizon simulation

## Getting Started

### Requirements

- Python 3.8 or later
- pip

### Installation

#### From source

- Clone the repository:

  ```bash
  git clone https://github.com/ziriuz84/asteroidpy
  cd asteroidpy
  ```

- (Optional) Create and activate a virtual environment:

  ```bash
  python -m venv env
  source env/bin/activate  # On Windows: env\Scripts\activate
  ```

- Install AsteroidPy:
  ```bash
  pip install .
  ```

### Execution

Run the application:

```bash
asteroidpy
```

### Configuration

Configuration is stored in `~/.asteroidpy`. On first run, the application creates it with defaults. Use the configuration menu to set:

- Observatory location (coordinates, altitude, MPC code)
- Virtual horizon (minimum altitude per cardinal direction)
- Interface language

### Internationalization

AsteroidPy supports multiple languages. Change the language from Configuration → General in the main menu. Available locales include English, Italiano, Deutsch, Français, Español, and Português (depending on installed translation files).

## Dependencies

- requests
- beautifulsoup4
- astropy
- astroplan
- astroquery
- httpx
- lxml
- platformdirs

## Data sources

- [7Timer](https://7timer.info) — weather forecasts
- [Minor Planet Center](https://www.minorplanetcenter.net/) — ephemerides and NEOcp data

## Release history

See [CHANGELOG.md](CHANGELOG.md).

## Contributing

[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/ziriuz84/asteroidpy/issues)

Thank you for considering contributing to AsteroidPy!

Please first note we have a code of conduct; please follow it in all your interactions with the project.

We welcome any type of contribution, not only code. You can help with:

- **QA**: File bug reports; the more details you can give, the better (e.g. screenshots with the console open)
- **Community**: Presenting the project at meetups, organizing a dedicated meetup for the local community
- **Code**: Take a look at the [open issues](https://github.com/ziriuz84/asteroidpy/issues). Even if you can't write the code yourself, you can comment on them—showing that you care about a given issue helps us triage them.

## TODO

- NEOcp alert integration
- Observation registration
