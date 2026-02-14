# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1](https://github.com/ziriuz84/asteroidpy/releases/tag/v1.0.1) (2026-02-14)

### Bug Fixes

- **scheduling:** replace blocking requests with async httpx in get_neocp_ephemeris ([16a174c](https://github.com/ziriuz84/asteroidpy/commit/16a174cbf48a5b24b8d583400b9fdbfb9d44c60e))

### Documentation

- fix README code block spacing and index hyphenation ([365dfc6](https://github.com/ziriuz84/asteroidpy/commit/365dfc6a6c78a971aa3198335a308148980448a2))
## [1.0.0](https://github.com/ziriuz84/asteroidpy/releases/tag/v1.0.0) (2026-02-14)

### Features

- **configuration:** implement get_observatory_coordinates ([4cbba90](https://github.com/ziriuz84/asteroidpy/commit/4cbba90d0b52f8c9b1085598bcdc03035b931eea))
- **scheduling:** add velocity and direction to NEO confirmation ([4e08187](https://github.com/ziriuz84/asteroidpy/commit/4e081871be4a2919b1a6641754f3758c3bf831cf))
- **i18n:** load translations from locales and add multi-language menu ([a75d4a4](https://github.com/ziriuz84/asteroidpy/commit/a75d4a44fae7c2b5c13541e66f2200f9f9f64956))
- **types:** add and refine type hints across package and configure mypy ([d2c2943](https://github.com/ziriuz84/asteroidpy/commit/d2c2943a2a405e6e8e07e1db30fc681882f679b8))

### Bug Fixes

- **scheduling:** remove debug print and translate Italian comments ([833be34](https://github.com/ziriuz84/asteroidpy/commit/833be3430ce8be2ed26d02ab97823bf100236d28))
- **interface:** replace eval with get_integer in config_menu ([272e293](https://github.com/ziriuz84/asteroidpy/commit/272e293d5a0f449d61c504cdc75fd977f66485aa))
- **pyproject.toml:** correct license syntax from colon to equals sign for proper TOML format ([22e186a](https://github.com/ziriuz84/asteroidpy/commit/22e186ab91365ae5a2bbaf310b1b54ef2594afdc))
- **pyproject.toml:** change license format from string to dictionary to comply with PEP 621 standards ([d55ab48](https://github.com/ziriuz84/asteroidpy/commit/d55ab488f42584b049836ceacbf094c703f228b7))
- **scheduling:** add robust error handling to httpx_get/post and tests for non-200 responses and exceptions ([9a70541](https://github.com/ziriuz84/asteroidpy/commit/9a70541061bd7071f7595c388eb06a216c8f8896))
- **scheduling:** make target list scraping robust to missing/malformed HTML tables and rows ([48da712](https://github.com/ziriuz84/asteroidpy/commit/48da712410ca69e174d07dfe4b6d1d7d8d2b81da))
- **scheduling:** apply altitude filter and add positive NEOCP test ([10275cc](https://github.com/ziriuz84/asteroidpy/commit/10275cc671934324885bd2dc224f64ab1bc630b4))
- **configuration:** handle unreadable or invalid config file in load_config ([0022a1d](https://github.com/ziriuz84/asteroidpy/commit/0022a1d03de6b6f6d6c038ffa3669dd200127425))
- **scheduling:** accept case-insensitive coordid in skycoord_format ([5188fb0](https://github.com/ziriuz84/asteroidpy/commit/5188fb0a885ba8a5b2f7533a6f88b82e941fa87d))
- **scheduling:** make skycoord_format robust to invalid strings and accept colon-separated input ([8fa3e3d](https://github.com/ziriuz84/asteroidpy/commit/8fa3e3da39fcae2bb800b6d8154b94d683dfac13))
- **configuration:** stop creating user's home directory ([889a718](https://github.com/ziriuz84/asteroidpy/commit/889a718b3dfd8fe64c7cc98ecbd63675a0894fc2))
- **configuration:** use ~/.asteroidpy for config and correct defaults; fix tests ([abb4e51](https://github.com/ziriuz84/asteroidpy/commit/abb4e51a7da9305ddaba915316a1dd6affc93b6c))
- **scheduling:** narrow exception handling in weather time formatting ([a59bb84](https://github.com/ziriuz84/asteroidpy/commit/a59bb84abcecea5ad28dfa640dc3d6a7f1815ee5))
- **scheduling:** The use of a try/except block in map_or_na may be unnecessary. ([8618439](https://github.com/ziriuz84/asteroidpy/commit/861843943cc90c99245b2362bc1ef1d9c454566e))

### Code Refactoring

- **tests:** inline simple conditional in fake_expanduser for clarity ([08df765](https://github.com/ziriuz84/asteroidpy/commit/08df765a118d3a3e55b0547ddea6a81ad8f29598))

### Documentation

- **README:** improve structure and content ([2796555](https://github.com/ziriuz84/asteroidpy/commit/2796555d15d55971f585981c32cd44961e94de49))
- **interface:** improve docstrings ([b423698](https://github.com/ziriuz84/asteroidpy/commit/b423698c6fd7ddef59eb049277d71d783c0e767f))
- improve code and user documentation ([b86a79c](https://github.com/ziriuz84/asteroidpy/commit/b86a79ca034138edf927b65f8684ca713f552501))
- **changelog:** document is_visible boundary fixes and new tests ([28673a4](https://github.com/ziriuz84/asteroidpy/commit/28673a4c215dfc014437d902f2a40d57fe9173f9))
- **changelog:** note robust httpx error handling and new tests (closes #84) ([ce7c8a4](https://github.com/ziriuz84/asteroidpy/commit/ce7c8a423dd968105924baff08b19d5584294138))
- **changelog:** document robust parsing for observing target list and new tests (closes #85) ([5284843](https://github.com/ziriuz84/asteroidpy/commit/528484336f609cec66c59c023010dddb5e5e5900))
- **changelog:** note min_altitude filter and new NEOCP test ([7c26619](https://github.com/ziriuz84/asteroidpy/commit/7c26619d42f415155ac2c928163fa1797c5fb1a2))
- **changelog:** note corrupted/invalid config test for load_config ([82a6482](https://github.com/ziriuz84/asteroidpy/commit/82a6482faa29b488f908b30bcec1f28177a3f1c1))
- **changelog:** note fallback on unreadable config and new tests ([6e35a65](https://github.com/ziriuz84/asteroidpy/commit/6e35a65bbf031f2bd532accaecc79fc570ea30e5))
- **changelog:** note case-insensitive coordid handling in skycoord_format ([fe6ec20](https://github.com/ziriuz84/asteroidpy/commit/fe6ec202b75c5b37476e8a559ac30db032aed76c))
- **changelog:** note skycoord_format robustness improvement and reference #90 ([abfd2cd](https://github.com/ziriuz84/asteroidpy/commit/abfd2cdf52911bbdb862c6ea18e19f5690cd1811))
- **changelog:** add missing entries for recent changes ([49bc446](https://github.com/ziriuz84/asteroidpy/commit/49bc446ae968a0c92d9f8001e0c097abacc9c649))
- **changelog:** note narrowed exception handling in weather() ([be03194](https://github.com/ziriuz84/asteroidpy/commit/be031947e35623fb1ecc6ee4cb32e98c39f73682))
- **changelog:** add CHANGELOG summarizing recent changes ([28fbfe0](https://github.com/ziriuz84/asteroidpy/commit/28fbfe046ba7bcd7fe3b89cae41596038ed91a3b))

### Tests

- **configuration:** add print_obs_config redaction tests ([fbe4187](https://github.com/ziriuz84/asteroidpy/commit/fbe41879cf3b376271cbdb273aa69276fd08cbcf))
- **configuration:** add coverage for corrupted/invalid config file ([694519b](https://github.com/ziriuz84/asteroidpy/commit/694519b949805e8ca92d09f4d883a9f6505d4f72))
- **configuration,scheduling:** add isolated test suite ([4a755ab](https://github.com/ziriuz84/asteroidpy/commit/4a755abdcea898c8a4813bd8a84d9abbf64ff997))

### Chores

- **pyproject.toml:** comment out the GPL v3 license classifier to avoid confusion ([c984bf4](https://github.com/ziriuz84/asteroidpy/commit/c984bf4d75f66d9755666fc869af9cd2e2b0e90d))
- **pyproject.toml:** update license format from table to string for consistency and clarity ([d1e6f1d](https://github.com/ziriuz84/asteroidpy/commit/d1e6f1dae36a64a0716bb8bb5545b35e3c338e7c))
- **pyproject.toml:** remove unnecessary 'i' character from the file to clean up the configuration ([f4bc4a6](https://github.com/ziriuz84/asteroidpy/commit/f4bc4a66bce272048a3491db4e88203d6e3e87aa))
- better setup tools ([7ec4157](https://github.com/ziriuz84/asteroidpy/commit/7ec4157e043cca94f97ea1224535d89fcf884f9a))
- **mypy:** extend type checking to tests and docs config ([520179b](https://github.com/ziriuz84/asteroidpy/commit/520179b805d14475dd70e3154f98ad42b7ca86d1))
- **setup.py:** better formatting ([5a6a542](https://github.com/ziriuz84/asteroidpy/commit/5a6a542da0c64c86af108e633395e7f9aab02837))
