#!/bin/bash

# Create a GitHub release for the top CHANGELOG entry.
# Run after tagging/publishing (e.g. ./release.sh 1.2.4), from a clean checkout.
#
# Thin wrapper kept for backwards compatibility: the real implementation now
# lives in release.sh, so this entry point shares its preflight checks, its
# release-branch enforcement and its tag-in-history validation instead of
# keeping a second, drifting copy of the same logic.

set -euo pipefail

# Resolve the script's directory with bash expansion rather than dirname, so the
# wrapper adds no external dependency of its own: release.sh preflight() is then
# the single place that decides which executables must exist.
script_dir=${0%/*}
[ "$script_dir" = "$0" ] && script_dir=.
cd "$script_dir"

if [ ! -x ./release.sh ]; then
    echo "release.sh not found or not executable in $(pwd)" >&2
    exit 1
fi

exec ./release.sh --github-release "$@"
