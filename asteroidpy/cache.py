"""Persistent cache for remote responses, keyed by request identity.

Every non-astroquery source reached from :mod:`asteroidpy.scheduling` goes
through :func:`fetch_cached`, so a repeated run answers from disk instead of
re-hitting the MPC and 7Timer. The cache is a directory of small JSON files, one
per key, under the platform *cache* dir — deliberately not the config dir, so
discarding the settings never discards data and vice versa.

Outcomes are distinguished because the UI has to tell them apart:

* ``"hit"`` — the stored answer was fresh enough, no request was made;
* ``"miss"`` — the request ran and its answer was stored;
* ``"failover"`` — the request failed and a stored entry was served instead;
* ``"disabled"`` — :func:`is_enabled` returned ``False``; nothing was read.

A ``failover`` deliberately prefers a stale entry over an empty result: a
six-hour-old forecast is still useful, while an empty table is indistinguishable
from "nothing to see". The entry age travels with the result, so a caller can
report how old the data is without parsing anything.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal, NamedTuple

import platformdirs

logger = logging.getLogger(__name__)

APP_NAME = "asteroidpy"

#: Sub-directory of the platform cache dir holding the response files.
CACHE_SUBDIR = "http"

#: Version of the on-disk entry format, stored in every file so an incompatible
#: future layout is detected rather than silently misread.
CACHE_SCHEMA = 1

#: Environment variable that turns the cache off, for debugging, reproducible
#: screenshots and support requests. Any of ``1``, ``true``, ``yes``, ``on``
#: (case-insensitive) disables it.
NO_CACHE_ENV_VAR = "ASTEROIDPY_NO_CACHE"

#: Values of :data:`NO_CACHE_ENV_VAR` that disable the cache.
_DISABLED_VALUES = frozenset({"1", "true", "yes", "on"})

#: Cache lifetime of the MPC What's Observable form token, in seconds. A Rails
#: authenticity token is short-lived by nature, so it gets the shortest TTL.
TTL_TOKEN_SEC = 900

#: Cache lifetime of a 7Timer forecast, in seconds. 7Timer ``astro`` refreshes
#: twice a day, so three hours keep a planning session off the network without
#: serving a noticeably stale sky.
TTL_WEATHER_SEC = 3 * 3600

#: Cache lifetime of ``neocp.json``, in seconds. It is a live feed: the point of
#: the page is what is new right now.
TTL_NEOCP_JSON_SEC = 900

#: Cache lifetime of the MPC confirmeph2 ephemerides, in seconds. They are
#: derived from the designations in the live feed above, so they expire with it.
TTL_NEOCP_EPHEM_SEC = 900

#: Cache lifetime of a What's Observable target table, in seconds. Each table
#: describes the sky at a single instant, so it ages quickly too.
TTL_TARGET_LIST_SEC = 900

#: Outcome of a :func:`fetch_cached` call.
CacheStatus = Literal["hit", "miss", "failover", "disabled"]


class FetchResult(NamedTuple):
    """A payload plus where it came from and, for a hit, how old it is.

    *value* is the payload the caller asked for, *status* is one of the
    :data:`CacheStatus` values, and *age_seconds* is the age of the served entry
    for a ``"hit"`` or ``"failover"`` (``None`` when the payload came off the
    network or the cache was disabled).
    """

    value: Any
    status: CacheStatus
    age_seconds: float | None


#: Exception types whose *instances* may be matched by ``failover_on``.
ExceptionTypes = type[Exception] | tuple[type[Exception], ...]

#: A predicate alternative to :data:`ExceptionTypes`, for sources that raise one
#: exception type with several meanings (a ``DataSourceError`` whose ``reason``
#: distinguishes "unreachable" from "the page changed").
FailoverOn = ExceptionTypes | Callable[[Exception], bool]


def cache_root() -> Path:
    """Directory holding the response files.

    Uses the platform cache dir (``~/.cache/asteroidpy/http`` on Linux,
    ``~/Library/Caches/asteroidpy/http`` on macOS and
    ``%LOCALAPPDATA%\\asteroidpy\\http`` on Windows), never the config dir.
    """

    return Path(platformdirs.user_cache_dir(APP_NAME, appauthor=False)) / CACHE_SUBDIR


def is_enabled() -> bool:
    """Whether responses may be read from and written to the cache.

    The environment is read on every call rather than cached at import time, so
    a test or a wrapper script can flip the cache at any point.
    """

    value = os.environ.get(NO_CACHE_ENV_VAR, "")
    return value.strip().lower() not in _DISABLED_VALUES


def cache_key(kind: str, **parts: Any) -> str:
    """Return the sha256 file name identifying one request.

    *kind* namespaces the source (``"weather"``, ``"whatsup-token"``, ...) so two
    requests to different endpoints can never collide. *parts* holds the request
    parameters; they are serialized to canonical JSON first, so ``a=1, b=2`` and
    ``b=2, a=1`` produce the same key.

    Volatile parameters — a freshly scraped CSRF token, for instance — must be
    left out by the caller: including one would change the key on every run and
    the entry would never be reused.
    """

    canonical = json.dumps(
        {"kind": kind, "parts": parts},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def entry_path(key: str) -> Path:
    """Path of the file holding *key*."""

    return cache_root() / f"{key}.json"


def _discard_unreadable(path: Path, reason: str) -> None:
    """Log and drop a cache file that cannot be used, so the next call refetches."""

    logger.debug("Discarding unusable cache entry %s: %s", path, reason)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.debug("Could not remove cache entry %s", path)


def read(key: str) -> tuple[Any, float] | None:
    """Return ``(payload, age_seconds)`` for *key*, or ``None`` when absent.

    A file that is missing, unreadable, corrupt, or written by another schema
    version counts as a miss and is removed: a bad cache must never break the
    application. TTL is *not* applied here, so a caller can still use an expired
    entry as a failover value.
    """

    path = entry_path(key)
    try:
        with path.open(encoding="utf-8") as handle:
            entry = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        _discard_unreadable(path, str(exc))
        return None

    if not isinstance(entry, dict) or entry.get("schema") != CACHE_SCHEMA:
        _discard_unreadable(path, "unrecognized cache schema")
        return None
    stored_at = entry.get("stored_at")
    if not isinstance(stored_at, (int, float)) or isinstance(stored_at, bool):
        _discard_unreadable(path, "missing or invalid stored_at")
        return None
    return entry.get("payload"), max(0.0, time.time() - float(stored_at))


def write(key: str, payload: Any, kind: str = "") -> None:
    """Store *payload* under *key*, atomically.

    The file is written to a temporary name in the same directory and then moved
    with :func:`os.replace`, so a concurrent reader (or a second TUI worker)
    never observes a half-written file and a crash mid-write leaves no truncated
    entry behind.

    Failures are logged and swallowed: a cache is an optimization, so being
    unable to store an answer must not fail the query that produced it.
    """

    now = time.time()
    entry = {
        "schema": CACHE_SCHEMA,
        "key": key,
        "kind": kind,
        "stored_at": now,
        "stored_at_iso": datetime.datetime.fromtimestamp(now, datetime.UTC).isoformat(),
        "payload": payload,
    }
    path = entry_path(key)
    tmp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{key}.", suffix=".tmp", dir=path.parent
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(entry, handle, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    except (OSError, TypeError, ValueError) as exc:
        logger.debug("Could not write cache entry %s: %s", key, exc)
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Could not remove partial cache file %s", tmp_path)


def clear() -> int:
    """Remove every cached response and return how many entries were dropped.

    Returns 0 when the cache directory does not exist, so calling it on a fresh
    install is a no-op rather than an error.
    """

    root = cache_root()
    try:
        entries = list(root.glob("*.json"))
    except OSError as exc:
        logger.debug("Could not list cache directory %s: %s", root, exc)
        return 0

    removed = 0
    for path in entries:
        try:
            path.unlink()
        except OSError as exc:
            logger.debug("Could not remove cache entry %s: %s", path, exc)
        else:
            removed += 1
    try:
        root.rmdir()
    except OSError:
        # Still holds files, or is already gone: nothing left to tidy up.
        pass
    return removed


def _accepts(failover_on: FailoverOn, exc: Exception) -> bool:
    """Whether *exc* is one of the failures *failover_on* covers.

    *failover_on* is either exception types (matched with :func:`isinstance`) or
    a predicate, so a source that raises one type with several meanings can fail
    over on some of them and still report the others.
    """

    if callable(failover_on) and not isinstance(failover_on, type):
        return failover_on(exc)
    return isinstance(exc, failover_on)


def _fresh_hit(
    stored: tuple[Any, float] | None, ttl_seconds: float
) -> FetchResult | None:
    """Return the stored payload as a ``"hit"`` when it is within *ttl_seconds*."""

    if stored is None or ttl_seconds <= 0:
        return None
    payload, age = stored
    if age > ttl_seconds:
        return None
    return FetchResult(payload, "hit", age)


def fetch_cached(
    key: str,
    ttl_seconds: float,
    loader: Callable[[], Any],
    *,
    failover_on: FailoverOn = Exception,
) -> FetchResult:
    """Return ``loader()``'s payload, served from the cache when possible.

    Parameters
    ----------
    key:
        A cache key from :func:`cache_key`.
    ttl_seconds:
        Age past which a stored entry is refreshed. A TTL of zero or less always
        refetches, while the entry stays available as a failover value.
    loader:
        Zero-argument callable performing the request. It runs only on a miss,
        on an expired entry, or when the cache is disabled.
    failover_on:
        Which failures justify falling back to a stored entry: exception types,
        or a predicate receiving the raised exception. Defaults to every
        exception, but a call site should narrow it to the failures that mean
        "the source did not answer" — an unexpected page, for instance, is worth
        reporting rather than silently replacing with a stale body.

    Returns
    -------
    FetchResult
        The payload, a :data:`CacheStatus`, and the entry age for ``"hit"`` and
        ``"failover"``.

    Notes
    -----
    If *loader* fails in a way *failover_on* covers and an entry exists — even
    one past its TTL — the stored payload is returned as a ``"failover"`` instead
    of the exception propagating. A failure with nothing stored propagates, so a
    genuine outage still reaches the caller and is reported.
    """

    if not is_enabled():
        return FetchResult(loader(), "disabled", None)

    stored = read(key)
    hit = _fresh_hit(stored, ttl_seconds)
    if hit is not None:
        return hit

    try:
        value = loader()
    except Exception as exc:
        if stored is None or not _accepts(failover_on, exc):
            raise
        payload, age = stored
        logger.info(
            "Serving cached response %s after a failed request (age %.0fs)", key, age
        )
        return FetchResult(payload, "failover", age)

    write(key, value)
    return FetchResult(value, "miss", None)


async def fetch_cached_async(
    key: str,
    ttl_seconds: float,
    loader: Callable[[], Awaitable[Any]],
    *,
    failover_on: FailoverOn = Exception,
) -> FetchResult:
    """Await *loader* unless the cache can answer, mirroring :func:`fetch_cached`.

    The parameters, the returned :class:`FetchResult` and the failover rules are
    identical to the synchronous version; only *loader* is a coroutine function.
    The disk access itself stays synchronous: the entries are a few kilobytes, and
    keeping the cache logic in one place is worth more than avoiding a thread hop.
    """

    if not is_enabled():
        return FetchResult(await loader(), "disabled", None)

    stored = read(key)
    hit = _fresh_hit(stored, ttl_seconds)
    if hit is not None:
        return hit

    try:
        value = await loader()
    except Exception as exc:
        if stored is None or not _accepts(failover_on, exc):
            raise
        payload, age = stored
        logger.info(
            "Serving cached response %s after a failed request (age %.0fs)", key, age
        )
        return FetchResult(payload, "failover", age)

    write(key, value)
    return FetchResult(value, "miss", None)
