"""Unit tests for the persistent response cache."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import httpx
import platformdirs
import pytest

from asteroidpy import cache

pytest.importorskip("platformdirs")


def _entry_file(key: str) -> Path:
    return cache.cache_root() / f"{key}.json"


def _write_aged(key: str, payload: object, age_seconds: float) -> None:
    """Store *payload* as if it had been fetched *age_seconds* ago."""

    cache.write(key, payload, kind=key[:8])
    path = _entry_file(key)
    entry = json.loads(path.read_text(encoding="utf-8"))
    entry["stored_at"] = time.time() - age_seconds
    path.write_text(json.dumps(entry), encoding="utf-8")


def test_cache_key_is_stable_and_order_independent():
    assert cache.cache_key("weather", lat="45", lon="9") == cache.cache_key(
        "weather", lon="9", lat="45"
    )
    # Different kinds and different parameters must not collide.
    assert cache.cache_key("weather", lat="45") != cache.cache_key("neocp", lat="45")
    assert cache.cache_key("weather", lat="45") != cache.cache_key("weather", lat="46")
    assert len(cache.cache_key("weather")) == 64  # sha256 hex digest


def test_cache_root_is_not_the_configuration_directory():
    from asteroidpy import configuration

    # The autouse fixture redirects cache_root() to a tmp dir, so call the real
    # implementation to check where an actual install would write.
    real_cache_root = platformdirs.user_cache_dir("asteroidpy", appauthor=False)
    real_config_dir = configuration.canonical_config_path().parent

    assert real_cache_root != real_config_dir
    assert "asteroidpy" in real_cache_root
    assert cache.cache_root() != real_config_dir


def test_read_and_write_round_trip(tmp_path):
    key = cache.cache_key("weather", lat="45")
    assert cache.read(key) is None

    cache.write(key, {"dataseries": [1, 2, 3]}, kind="weather")

    stored = cache.read(key)
    assert stored is not None
    payload, age = stored
    assert payload == {"dataseries": [1, 2, 3]}
    assert 0.0 <= age < 5.0

    entry = json.loads(_entry_file(key).read_text(encoding="utf-8"))
    assert entry["schema"] == cache.CACHE_SCHEMA
    assert entry["kind"] == "weather"
    assert entry["key"] == key
    assert entry["stored_at_iso"].endswith("+00:00")


def test_read_treats_a_corrupt_file_as_a_miss_and_removes_it(tmp_path):
    key = cache.cache_key("weather", lat="45")
    path = _entry_file(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    assert cache.read(key) is None
    assert not path.exists()


def test_read_ignores_an_entry_from_another_schema(tmp_path):
    key = cache.cache_key("weather", lat="45")
    path = _entry_file(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema": cache.CACHE_SCHEMA + 99, "stored_at": time.time()}),
        encoding="utf-8",
    )

    assert cache.read(key) is None
    assert not path.exists()


def test_fetch_cached_reports_a_miss_then_a_hit(tmp_path):
    key = cache.cache_key("weather", lat="45")
    calls = []

    def loader() -> dict[str, int]:
        calls.append(1)
        return {"init": "2026010100"}

    first = cache.fetch_cached(key, cache.TTL_WEATHER_SEC, loader)
    assert first.status == "miss"
    assert first.age_seconds is None
    assert first.value == {"init": "2026010100"}

    second = cache.fetch_cached(key, cache.TTL_WEATHER_SEC, loader)
    assert second.status == "hit"
    assert second.value == first.value
    assert second.age_seconds is not None and second.age_seconds >= 0
    assert len(calls) == 1, "the second run must not touch the network"


def test_fetch_cached_refetches_once_the_ttl_expired(tmp_path):
    key = cache.cache_key("weather", lat="45")
    calls = []

    def loader() -> str:
        calls.append(1)
        return f"payload {len(calls)}"

    assert cache.fetch_cached(key, 3600, loader).value == "payload 1"
    # A zero TTL forces a refresh but keeps the entry usable as a failover.
    refreshed = cache.fetch_cached(key, 0, loader)
    assert refreshed.status == "miss"
    assert refreshed.value == "payload 2"
    assert len(calls) == 2


def test_fetch_cached_fails_over_to_a_stale_entry(tmp_path):
    key = cache.cache_key("whatsup-token")
    # Past its TTL, so the request is attempted first and only then falls back.
    _write_aged(key, "cached-token", age_seconds=cache.TTL_TOKEN_SEC + 60)

    def boom() -> str:
        raise OSError("network down")

    result = cache.fetch_cached(key, cache.TTL_TOKEN_SEC, boom, failover_on=OSError)
    assert result.status == "failover"
    assert result.value == "cached-token"
    assert result.age_seconds is not None
    assert result.age_seconds >= cache.TTL_TOKEN_SEC


def test_fetch_cached_propagates_when_there_is_nothing_stored():
    key = cache.cache_key("whatsup-token")

    def boom() -> str:
        raise OSError("network down")

    with pytest.raises(OSError, match="network down"):
        cache.fetch_cached(key, 3600, boom, failover_on=OSError)


def test_fetch_cached_only_fails_over_on_the_listed_exceptions():
    key = cache.cache_key("whatsup-token")
    _write_aged(key, "cached-token", age_seconds=3600)

    def boom() -> str:
        raise OSError("network down")

    # A page that changed is not a network outage: the caller asked to be told,
    # so the failure must not be replaced by a stale body.
    with pytest.raises(OSError, match="network down"):
        cache.fetch_cached(key, 3600, boom, failover_on=httpx.RequestError)


def test_fetch_cached_accepts_a_predicate_for_one_exception_type():
    key = cache.cache_key("whatsup-token")
    _write_aged(key, "cached-token", age_seconds=3600)

    class SourceError(RuntimeError):
        def __init__(self, reason: str) -> None:
            super().__init__(reason)
            self.reason = reason

    def unreachable_only(exc: Exception) -> bool:
        return isinstance(exc, SourceError) and exc.reason == "network_error"

    def raise_unreachable() -> str:
        raise SourceError("network_error")

    def raise_changed_page() -> str:
        raise SourceError("page_changed")

    assert (
        cache.fetch_cached(key, 3600, raise_unreachable, failover_on=unreachable_only)
    ).status == "failover"
    with pytest.raises(SourceError, match="page_changed"):
        cache.fetch_cached(key, 3600, raise_changed_page, failover_on=unreachable_only)


def test_fetch_cached_can_be_disabled_by_environment(monkeypatch):
    key = cache.cache_key("weather", lat="45")
    cache.write(key, "stored")

    monkeypatch.setenv(cache.NO_CACHE_ENV_VAR, "1")
    assert cache.is_enabled() is False
    calls = []

    def loader() -> str:
        calls.append(1)
        return "fresh"

    result = cache.fetch_cached(key, cache.TTL_WEATHER_SEC, loader)
    assert result.status == "disabled"
    assert result.value == "fresh"
    assert result.age_seconds is None
    # A disabled cache neither reads nor writes.
    assert len(calls) == 1
    assert cache.read(key) is not None
    stored = cache.read(key)
    assert stored is not None and stored[0] == "stored"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", " on "])
def test_cache_is_disabled_only_by_documented_values(monkeypatch, value):
    monkeypatch.setenv(cache.NO_CACHE_ENV_VAR, value)
    assert cache.is_enabled() is False


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_cache_stays_enabled_for_other_environment_values(monkeypatch, value):
    monkeypatch.setenv(cache.NO_CACHE_ENV_VAR, value)
    assert cache.is_enabled() is True


def test_clear_removes_every_entry_and_counts_them(tmp_path):
    first = cache.cache_key("weather", lat="45")
    second = cache.cache_key("neocp")
    cache.write(first, "a", kind="weather")
    cache.write(second, "b", kind="neocp")

    assert cache.clear() == 2
    assert cache.read(first) is None
    assert cache.read(second) is None
    # Clearing an already empty cache is a no-op, not an error.
    assert cache.clear() == 0


def test_removing_the_cache_directory_does_not_break_a_fetch(tmp_path):
    key = cache.cache_key("weather", lat="45")
    cache.write(key, "stored")
    shutil.rmtree(cache.cache_root())
    assert not cache.cache_root().exists()

    calls = []

    def loader() -> str:
        calls.append(1)
        return "fresh"

    result = cache.fetch_cached(key, 3600, loader)
    assert result.status == "miss"
    assert result.value == "fresh"
    assert len(calls) == 1


def test_write_survives_an_unserializable_payload(tmp_path):
    key = cache.cache_key("weather", lat="45")

    class Opaque:
        def __repr__(self) -> str:
            return "<opaque>"

    # A payload the JSON encoder cannot handle must not raise: a cache is an
    # optimization, and the caller still needs its answer.
    cache.write(key, {"weird": Opaque()}, kind="weather")
    stored = cache.read(key)
    assert stored is not None
    assert stored[0] == {"weird": "<opaque>"}


def test_ttl_constants_are_ordered_by_how_fast_the_source_changes():
    # A CSRF token is the most perishable thing we cache; ephemerides are served
    # by astroquery with its own, much longer, cache.
    assert 0 < cache.TTL_TOKEN_SEC <= cache.TTL_NEOCP_JSON_SEC
    assert cache.TTL_NEOCP_JSON_SEC <= cache.TTL_TARGET_LIST_SEC
    assert cache.TTL_TARGET_LIST_SEC < cache.TTL_WEATHER_SEC


def test_write_does_not_leave_temporary_files_behind(tmp_path):
    key = cache.cache_key("weather", lat="45")
    cache.write(key, {"a": 1})
    leftovers = [p for p in cache.cache_root().iterdir() if p.suffix == ".tmp"]
    assert leftovers == []
    assert os.listdir(cache.cache_root()) == [f"{key}.json"]
