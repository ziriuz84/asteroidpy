#!/bin/bash

set -euo pipefail

# Create a GitHub release for the latest CHANGELOG entry.
# Run after tagging/publishing (e.g. ./release.sh 1.2.4), from a clean checkout.

if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI is required but not found in PATH" >&2
    exit 1
fi

if [[ ! -f CHANGELOG.md ]]; then
    echo "CHANGELOG.md not found" >&2
    exit 1
fi

VERSION=$(sed -n 's/^## \[\([^]]*\)\].*/\1/p' CHANGELOG.md | head -1)
if [[ -z "$VERSION" ]]; then
    echo "Could not parse release version from CHANGELOG.md" >&2
    exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid version in CHANGELOG.md: $VERSION" >&2
    exit 1
fi

if [[ -f asteroidpy/version.py ]]; then
    PY_VERSION=$(grep -E '^__version__[[:space:]]*=' asteroidpy/version.py | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [[ -n "$PY_VERSION" && "$PY_VERSION" != "$VERSION" ]]; then
        echo "CHANGELOG version ($VERSION) does not match asteroidpy/version.py ($PY_VERSION)" >&2
        exit 1
    fi
fi

NOTES=$(awk -v v="$VERSION" '
  $0 ~ "^## \\[" v "\\]" { in_section=1; next }
  in_section && /^## \[/ { exit }
  in_section && /^---$/ { next }
  in_section {
    sub(/---$/, "", $0)
    if ($0 != "") print
  }
' CHANGELOG.md)

if [[ -z "${NOTES//[[:space:]]/}" ]]; then
    echo "Release notes for v$VERSION are empty in CHANGELOG.md" >&2
    exit 1
fi

TAG="v$VERSION"
if git rev-parse "$TAG^{commit}" >/dev/null 2>&1; then
    :
elif git rev-parse "$TAG" >/dev/null 2>&1; then
    :
else
    echo "Git tag $TAG not found; create it before running ghrelease.sh" >&2
    exit 1
fi

if gh release view "$TAG" >/dev/null 2>&1; then
    echo "GitHub release $TAG already exists" >&2
    exit 1
fi

gh release create "$TAG" --title "AsteroidPy $VERSION" --notes "$NOTES"
