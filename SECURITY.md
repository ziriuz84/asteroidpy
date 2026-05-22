# Security Policy

## Supported Versions

Security fixes land on the `main` development branch and are released as tagged versions on GitHub/PyPI. Prefer upgrading to the **latest stable release**.

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

AsteroidPy performs network requests to third-party services (e.g. MPC, 7Timer). Treat credentials, API keys, and local config under `~/.asteroidpy` as sensitive.
