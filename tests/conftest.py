"""Shared pytest fixtures.

The autouse :func:`isolated_cache` fixture points the response cache at a
per-test temporary directory. Without it, any test that reaches the network layer
would read and write the developer's real ``~/.cache/asteroidpy``, making the
suite order-dependent and polluting the user's cache. The fixture patches
:func:`asteroidpy.cache.cache_root` rather than ``platformdirs.user_cache_dir`` so
it cannot interfere with the configuration tests, which patch
``platformdirs.user_config_dir`` for the same reason.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path) -> None:
    """Redirect the response cache to ``tmp_path`` for the duration of a test."""

    from asteroidpy import cache

    monkeypatch.setattr(cache, "cache_root", lambda: tmp_path / "http")
