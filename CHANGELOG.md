## Changelog

### [Unreleased]
- i18n: Load translations from `locales/` using config `General.lang`; reinitialize on change
- UI: Language menu lists installed locales with native names
- Locales: Added it, en, de, fr, es, pt and compiled `.mo`
- Weather: Handle unknown forecast codes gracefully (avoid KeyError)
- Weather: Narrow exception handling when formatting forecast time (catch only TypeError/ValueError to avoid masking bugs)
- Configuration: Avoid creating the user's home directory; write to `~/.asteroidpy` directly
- Configuration: Use `~/.asteroidpy` for config and correct defaults; align tests
- Configuration: Gracefully handle unreadable or invalid `~/.asteroidpy` by falling back to initialize
- tests: Add coverage for unreadable config file permissions scenario
- tests: Add coverage for corrupted/invalid config content fallback in `load_config` (closes #88)
- i18n: Clarify that checking only `base.po/.mo` may not guarantee translation availability
- Weather/UI: Improve default wind direction display (avoid ambiguous '?')
- Docs/Security: Add `SECURITY.md` policy
- Fix: Make `skycoord_format` robust to invalid strings and accept colon-separated input; return original string on invalid tokens (closes #90)
- Fix: Accept case-insensitive `coordid` in `skycoord_format` (allow 'RA'/'Dec')
 - Fix: Apply `min_altitude` filtering in `neocp_confirmation` and expose it via the menu (closes #86)
 - tests: Add positive-path test for NEOCP confirmation including a valid object passing all filters

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
