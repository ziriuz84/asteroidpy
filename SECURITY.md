# Security Policy

## Supported Versions

Security fixes land on `main`, the release branch, and are published as tagged versions on GitHub/PyPI. Prefer upgrading to the **latest stable release**.

There is no long-term branch matrix: use the newest `v*` tag you can reasonably deploy.

## Reporting a Vulnerability

Please **do not** open a public issue for undisclosed vulnerabilities.

Instead:

1. Open a **[private security advisory](https://github.com/ziriuz84/asteroidpy/security/advisories/new)** on GitHub if you have access, **or**
2. Email the maintainers listed in `[project.authors]` in `pyproject.toml` with a clear subject (e.g. “Security: AsteroidPy …”).

Include:

- A short description of the impact and affected component
- Steps to reproduce (or a proof-of-concept), if safe to share
- The AsteroidPy version or commit you tested

You should receive an initial acknowledgement within a few business days. We will coordinate disclosure (fix, release note, and optional CVE) once a patch is ready.

## Scope Notes

AsteroidPy performs network requests to third-party services (e.g. MPC, 7Timer). Treat credentials, API keys, and the local config directory as sensitive.

That config directory is the [`platformdirs`](https://github.com/platformdirs/platformdirs) user config dir for `asteroidpy` — e.g. `~/.config/asteroidpy/` on Linux, `~/Library/Application Support/asteroidpy/` on macOS, `%LOCALAPPDATA%\asteroidpy\` on Windows. It may contain a `.mo`-compiled copy of the very same `CODE_OF_CONDUCT.md` and `SECURITY.md` you are reading. Legacy installs migrated a `~/.asteroidpy` file into that directory on first run, so check both locations when hunting for leaked material.
