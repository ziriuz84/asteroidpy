## Changelog

### [Unreleased]
- i18n: Load translations from `locales/` using config `General.lang`; reinitialize on change
- UI: Language menu lists installed locales with native names
- Locales: Added it, en, de, fr, es, pt and compiled `.mo`
- Weather: Handle unknown forecast codes gracefully (avoid KeyError)

### 2025-08-11
- types: Add and refine type hints across package and configure mypy
- chore(mypy): Extend type checking to tests and docs config
- tests: Add isolated test suite for configuration and scheduling
- docs: Better formatting in setup.py

### 2022-05 to 2022-10 (historical)
- docs: Documentation added and finalized for multiple modules
- feature: Object ephemeris, twilight times, sun/moon ephemeris
- feature: Virtual horizon configuration and visibility checks
- refactor: Observing target list and menus; convert to QTable
- chore: Dependency updates and various maintenance commits
