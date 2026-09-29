"""Observation planning: ephemerides, weather, NEOcp, twilight and night ranking.

Public entry points fall into four groups:

* **Weather** — :func:`weather_forecast_raw` (raw 7Timer ``astro`` payload),
  :func:`weather_forecast_report` (plain-text report used by the TUI) and the
  legacy stdout helper :func:`weather`.
* **MPC data** — :func:`observing_target_list` / :func:`observing_target_list_scraper`
  for the MPC "What's Observable" table, :func:`neocp_confirmation` for
  Near-Earth Object candidates, and :func:`object_ephemeris` for named objects.
* **Time and visibility** — :func:`twilight_times`, :func:`sun_moon_ephemeris`,
  :func:`is_visible` and the shared :func:`earth_location_from_config` helper.
* **Best-night planner** — :func:`astronomical_night` (per-night twilight window),
  :func:`best_nights` (ranked scores) and :func:`best_nights_report`.

Observatory settings and planner weights are read from the configuration
object via :func:`asteroidpy.configuration.load_config`.

**Caching** — every request that does not go through astroquery is wrapped in
:func:`asteroidpy.cache.fetch_cached`, keyed by endpoint plus request parameters
and given a per-source TTL (see the ``cache.TTL_*`` constants). A repeated run
is therefore answered from disk, and a network failure falls back to the stored
answer instead of degrading to an empty table. The two astroquery calls
(:func:`object_ephemeris`, :func:`asteroidpy.configuration.get_observatory_coordinates`)
keep astroquery's own cache: it already stores those responses for a week, and
re-serializing an astropy table here would only duplicate it.
"""

import asyncio
import datetime
import math
import re
from collections.abc import Mapping, Sequence
from configparser import ConfigParser
from typing import Any, Literal, NamedTuple, cast

import httpx
import requests
from astroplan import Observer
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.table import QTable
from astropy.time import Time
from astropy.units import Quantity
from astroquery.mpc import MPC
from bs4 import BeautifulSoup

from asteroidpy import cache, configuration
from asteroidpy.errors import (
    REASON_HTTP_STATUS,
    REASON_NETWORK_ERROR,
    REASON_TOKEN_NOT_FOUND,
    DataSourceError,
)

#: 7Timer ``astro`` endpoint queried by the weather and best-night code paths.
SEVENTIMER_API_URL = "https://www.7timer.info/bin/api.pl"

#: Default HTTP timeout, in seconds, for 7Timer and MPC requests.
DEFAULT_REQUEST_TIMEOUT_SEC = 30.0

#: Best-night planner weights (fallback when ``[Planner]`` is absent or unreadable).
DEFAULT_PLANNER_WEIGHTS = {
    "cloud": 0.4,
    "seeing": 0.25,
    "transparency": 0.15,
    "moon": 0.2,
}

#: Maximum number of nights to report when ``[Planner] max_nights`` is missing.
DEFAULT_PLANNER_MAX_NIGHTS = 5

#: ``[Planner]`` INI option that stores the weight of each scoring factor.
PLANNER_WEIGHT_OPTIONS: dict[str, str] = {
    "cloud": "w_cloud",
    "seeing": "w_seeing",
    "transparency": "w_transparency",
    "moon": "w_moon",
}

#: Number of ephemeris points requested from the MPC when none is given.
DEFAULT_EPHEMERIS_POINTS = 30

#: Fewest ephemeris points that make sense, since one row is already an ephemeris.
MIN_EPHEMERIS_POINTS = 1

#: Highest ephemeris point count accepted, generous enough for any realistic
#: session and low enough to keep the MPC from answering with a huge table.
MAX_EPHEMERIS_POINTS = 10000

#: Forecast horizon, in hours, prefilled by the weather screen (three days).
DEFAULT_WEATHER_HOURS = 72

#: Shortest forecast horizon the weather screen accepts, in hours.
MIN_WEATHER_HOURS = 6

#: Longest forecast horizon the weather screen accepts, in hours, and the whole span
#: of the 7Timer ``astro`` series.
MAX_WEATHER_HOURS = 168

#: Temperature units accepted by :func:`weather_forecast_report`.
TEMPERATURE_UNITS: dict[str, str] = {"C": "Celsius", "F": "Fahrenheit"}

#: Midpoint cloud cover (percent) for each 7Timer ``cloudcover`` code (1 = clear, 9 = overcast).
CLOUDCOVER_MIDPOINT_PCT = {
    1: 3.0,
    2: 12.5,
    3: 25.0,
    4: 37.5,
    5: 50.0,
    6: 62.5,
    7: 75.0,
    8: 87.5,
    9: 97.0,
}

# 7Timer ``prec_type`` codes that make a night unsuitable for observation.
_PRECIPITATION_CODES = {
    "rain",
    "snow",
    "sleet",
    "fzsnow",
    "fzra",
    "tsnow",
    "tsra",
    "tsp",
    "tsleet",
}

# MPC whats-up HTML table columns (minimum 8 cells per data row).
MPC_COL_DESIGNATION = 0
MPC_COL_MAG = 1
MPC_COL_TIME = 4
MPC_COL_RA = 5
MPC_COL_DEC = 6
MPC_COL_ALT = 7
MPC_MIN_COLS = 8

#: MPC "What's Observable" query form endpoint used for target-list POSTs.
MPC_WHATSUP_INDEX_URL = "https://www.minorplanetcenter.net/whatsup/index"

#: Name of the What's Observable source, used in :class:`~asteroidpy.errors.DataSourceError`.
MPC_WHATSUP_SOURCE = "MPC What's Observable"

_MPC_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}


#: Cache key namespace and TTL of the What's Observable form token. The token
#: is scraped from a page that never changes otherwise, so one key covers every
#: request; the TTL is short because a Rails authenticity token is perishable.
_WHATSUP_TOKEN_CACHE_KIND = "whatsup-token"


def _scrape_whatsup_authenticity_token() -> str:
    """Return the Rails authenticity token of the What's Observable form.

    The token is cached for :data:`asteroidpy.cache.TTL_TOKEN_SEC`, so opening the
    target-list form twice in a row does not scrape the page twice.

    Raises
    ------
    DataSourceError
        The page was unreachable, answered with a non-200 status, or no longer
        carries a form token. The caller must report it: posting without a
        token only produces a confusing empty result. A *network* failure is the
        one case a stored token can cover, so it fails over to the cached one
        instead of raising.
    """

    def load() -> str:
        r = requests.get(
            MPC_WHATSUP_INDEX_URL,
            headers=_MPC_BROWSER_HEADERS,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
        if r.status_code != 200:
            raise DataSourceError(
                MPC_WHATSUP_SOURCE,
                REASON_HTTP_STATUS,
                f"HTTP {r.status_code}",
            )
        soup = BeautifulSoup(r.content, "lxml")
        inp = soup.find("input", attrs={"name": "authenticity_token"})
        if inp and inp.get("value"):
            return str(inp["value"])
        html = r.text
        m = re.search(
            r'name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if m:
            return m.group(1)
        meta = re.search(
            r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if meta:
            return meta.group(1)
        raise DataSourceError(MPC_WHATSUP_SOURCE, REASON_TOKEN_NOT_FOUND)

    def is_network_failure(exc: Exception) -> bool:
        return isinstance(exc, DataSourceError) and exc.reason == REASON_NETWORK_ERROR

    key = cache.cache_key(_WHATSUP_TOKEN_CACHE_KIND)
    try:
        result = cache.fetch_cached(
            key,
            cache.TTL_TOKEN_SEC,
            load,
            failover_on=is_network_failure,
        )
    except requests.RequestException as exc:
        raise DataSourceError(
            MPC_WHATSUP_SOURCE,
            REASON_NETWORK_ERROR,
            str(exc) or type(exc).__name__,
        ) from exc
    return cast(str, result.value)


def resolve_whatsup_authenticity_token() -> str:
    """Return a fresh authenticity token for the MPC What's Observable POST.

    Raises
    ------
    DataSourceError
        When the token cannot be scraped. There is no cached or embedded
        substitute: an unusable token is reported instead of hidden.
    """

    return _scrape_whatsup_authenticity_token()


# MPC observing-target calendar times, e.g. ``2026 5 24.559 (13:25 UT)``, optional ``UTC``.
_MPC_WHATSUP_CALENDAR_TIME_RE = re.compile(
    r"^\s*(?P<y>\d{4})\s+(?P<mo>\d{1,2})\s+(?P<dy>\d+(?:\.\d*)?)(\s|$)"
)
_MPC_WHATSUP_UT_PAREN_TIME_RE = re.compile(
    r"\(\s*(?P<h>\d{1,2})\s*:\s*(?P<m>\d{1,2})\s+(?:UTC|UT)\s*\)",
    re.IGNORECASE,
)


def mpc_whatsup_table_cell_to_time(timestr: str) -> Time:
    """Parse an MPC observing-target-table time cell into UTC :class:`~astropy.time.Time`.

    Newer MPC HTML cells look like::

        ``2026 5 24.559 (13:25 UT)``

    Prefer the UT clock time in parentheses for ephemerides. Older tables used iso-like strings.
    """

    stripped = timestr.strip()
    if not stripped:
        raise ValueError("empty MPC whats-up table time cell")

    cal_match = _MPC_WHATSUP_CALENDAR_TIME_RE.match(stripped)
    paren_match = _MPC_WHATSUP_UT_PAREN_TIME_RE.search(stripped)
    if cal_match is not None and paren_match is not None:
        year = int(cal_match.group("y"))
        month = int(cal_match.group("mo"))
        day_field = float(cal_match.group("dy"))
        day = int(day_field // 1)
        hour = int(paren_match.group("h"))
        minute = int(paren_match.group("m"))
        return Time(
            datetime.datetime(
                year,
                month,
                day,
                hour,
                minute,
                tzinfo=datetime.UTC,
            )
        )

    normalized = stripped.replace("T", " ").replace("z", "").replace("Z", "").strip()
    return Time(normalized)


# MPC confirmeph2 CGI: numeric fields parsed from HTML <pre>; indices from ephemeris line.
NEOCP_EPHEM_VELOCITY_IDX = 12
NEOCP_EPHEM_DIRECTION_IDX = 13
NEOCP_EPHEM_MIN_LEN = NEOCP_EPHEM_DIRECTION_IDX + 1

#: ``Parallax`` values accepted by the MPC confirmeph2 CGI: the viewing-point
#: selector, where only one of ``obscode`` and the explicit coordinates counts.
NEOCP_PARALLAX_GEOCENTRIC = 0
NEOCP_PARALLAX_OBS_CODE = 1
NEOCP_PARALLAX_COORDINATES = 2

#: ``[Observatory] mpc_code`` values that name no real observing site, so the
#: ephemeris site falls back to the explicit coordinates or to the geocenter.
#: ``500`` is the MPC's own geocentric code; ``XXX`` and ``0`` are placeholders the
#: MPC refuses as observing sites, kept here so configurations written before the
#: ``500`` default still produce a usable ephemeris.
NEOCP_GENERIC_MPC_CODES = frozenset({"", "0", "500", "XXX"})

#: Name of the confirmeph2 source, used in :class:`~asteroidpy.errors.DataSourceError`.
NEOCP_EPHEM_SOURCE = "MPC confirm ephemerides"

#: NEOcp live feed (JSON) endpoint, refreshed by the MPC every few minutes.
NEOCP_JSON_URL = "https://www.minorplanetcenter.net/Extended_Files/neocp.json"

cloudcover_dict = {
    1: "0%-6%",
    2: "6%-19%",
    3: "19%-31%",
    4: "31%-44%",
    5: "44%-56%",
    6: "56%-69%",
    7: "69%-81%",
    8: "81%-94%",
    9: "94%-100%",
}
seeing_dict = {
    1: '<0.5"',
    2: '0.5"-0.75"',
    3: '0.75"-1"',
    4: '1"-1.25"',
    5: '1.25"-1.5"',
    6: '1.5"-2"',
    7: '2"-2.5"',
    8: '>2.5"',
}
transparency_dict = {
    1: "<0.3",
    2: "0.3-0.4",
    3: "0.4-0.5",
    4: "0.5-0.6",
    5: "0.6-0.7",
    6: "0.7-0.85",
    7: "0.85-1",
    8: ">1",
}
liftedIndex_dict = {
    -10: "Below -7",
    -6: "-7 - -5",
    -4: "-5 - -3",
    -1: "-3 - 0",
    2: "0 - 4",
    6: "4 - 8",
    10: "8 - 11",
    15: "Over 11",
}
rh2m_dict = {
    -4: "0%-5%",
    -3: "5%-10%",
    -2: "10%-15%",
    -1: "15%-20%",
    0: "20%-25%",
    1: "25%-30%",
    2: "30%-35%",
    3: "35%-40%",
    4: "40%-45%",
    5: "45%-50%",
    6: "50%-55%",
    7: "55%-60%",
    8: "60%-65%",
    9: "65%-70%",
    10: "70%-75%",
    11: "75%-80%",
    12: "80%-85%",
    13: "85%-90%",
    14: "90%-95%",
    15: "95%-99%",
    16: "100%",
}
wind10m_speed_dict = {
    1: "Below 0.3 m/s",
    2: "0.3-3.4m/s",
    3: "3.4-8.0m/s",
    4: "8.0-10.8m/s",
    5: "10.8-17.2m/s",
    6: "17.2-24.5m/s",
    7: "24.5-32.6m/s",
    8: "Over 32.6m/s",
}


def earth_location_from_config(config: ConfigParser) -> EarthLocation:
    """Earth location from ``[Observatory]`` latitude, longitude, altitude (m)."""

    return EarthLocation.from_geodetic(
        lon=float(config["Observatory"]["longitude"]) * u.deg,
        lat=float(config["Observatory"]["latitude"]) * u.deg,
        height=float(config["Observatory"]["altitude"]) * u.m,
    )


async def httpx_get(
    url: str,
    payload: dict[str, Any],
    return_type: Literal["json", "text"],
) -> tuple[dict[str, Any] | list[dict[str, Any]] | str, int]:
    """Perform an asynchronous HTTP GET request.

    Makes an async GET request to the specified URL with the given query
    parameters and returns the parsed response along with the status code.

    Parameters
    ----------
    url : str
        The URL to query.
    payload : Dict[str, Any]
        Query parameters forwarded to HTTPX.
    return_type : str
        Either ``"json"`` (parse JSON body) or ``"text"`` (return raw response text).

    Returns
    -------
    tuple
        Parsed body and HTTP status code, or ``(empty, 0)`` on transport errors.

    Notes
    -----
    On transport errors or timeouts, returns empty data ({}, "") and status 0.
    JSON decoding failures yield ``{}``.
    """
    timeout = httpx.Timeout(DEFAULT_REQUEST_TIMEOUT_SEC)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, params=payload)
    except httpx.RequestError:
        # Network/timeouts/unreachable hosts: safe defaults and status 0
        if return_type == "json":
            return cast(tuple[dict[str, Any] | list[dict[str, Any]], int], ({}, 0))
        return ("", 0)

    if return_type == "json":
        try:
            parsed = r.json()
        except ValueError:
            parsed = {}
        return cast(
            tuple[dict[str, Any] | list[dict[str, Any]], int],
            (parsed, r.status_code),
        )
    else:
        return (r.text, r.status_code)


async def httpx_post(
    url: str,
    payload: dict[str, Any],
    return_type: Literal["json", "text"],
) -> tuple[dict[str, Any] | list[dict[str, Any]] | str, int]:
    """Perform an asynchronous HTTP POST request.

    Makes an async POST request to the specified URL with the given form data
    and returns the parsed response along with the status code.

    Parameters
    ----------
    url : str
        The URL to query.
    payload : Dict[str, Any]
        Form fields forwarded in the POST body.
    return_type : str
        Either ``"json"`` or ``"text"`` (same semantics as :func:`httpx_get`).

    Returns
    -------
    tuple
        Parsed body and HTTP status code, or ``(empty, 0)`` on transport errors.

    Notes
    -----
    Uses ``application/x-www-form-urlencoded``.
    """
    timeout = httpx.Timeout(DEFAULT_REQUEST_TIMEOUT_SEC)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=payload,
            )
    except httpx.RequestError:
        if return_type == "json":
            return cast(tuple[dict[str, Any] | list[dict[str, Any]], int], ({}, 0))
        return ("", 0)

    if return_type == "json":
        try:
            parsed = r.json()
        except ValueError:
            parsed = {}
        return cast(
            tuple[dict[str, Any] | list[dict[str, Any]], int],
            (parsed, r.status_code),
        )
    else:
        return (r.text, r.status_code)


def weather_time(time_init: str, deltaT: int) -> str:
    """Calculate a future time from an initial time string and time delta.

    Parses an initial time string in format 'YYYYMMDDHH' and adds a specified
    number of hours to calculate a future time, then formats it for display.

    Parameters
    ----------
    time_init : str
        Initial time string in format 'YYYYMMDDHH' (e.g., '2024010112').
    deltaT : int
        Number of hours to add to the initial time.

    Returns
    -------
    str
        Formatted time string in format 'DD/MM HH:MM' (e.g., '01/01 14:00').

    Notes
    -----
    The function assumes the time_init string is exactly 10 characters long
    and follows the format YYYYMMDDHH.
    """
    time_start = datetime.datetime(
        int(time_init[0:4]),
        int(time_init[4:6]),
        int(time_init[6:8]),
        int(time_init[8:10]),
    )
    time = time_start + datetime.timedelta(hours=deltaT)
    return time.strftime("%d/%m %H:%M")


def weather_forecast_raw(
    config: ConfigParser, product: str = "astro"
) -> dict[str, Any]:
    """Fetch the 7Timer JSON forecast for the configured observatory.

    Parameters
    ----------
    config : ConfigParser
        Observatory latitude/longitude under the ``[Observatory]`` section.
    product : str
        7Timer product name (default ``"astro"``, the astronomical forecast).

    Returns
    -------
    dict
        Parsed JSON body. An empty dict is returned when the request fails, times
        out, the server returns an error status, or the body is not valid JSON —
        unless a previous forecast is still on disk, in which case that one is
        returned instead: see :func:`asteroidpy.cache.fetch_cached`.
    """

    configuration.load_config(config)
    lat, long = config["Observatory"]["latitude"], config["Observatory"]["longitude"]
    payload = {"lon": long, "lat": lat, "product": product, "output": "json"}
    key = cache.cache_key("weather", url=SEVENTIMER_API_URL, **payload)

    def load() -> dict[str, Any]:
        r = requests.get(
            SEVENTIMER_API_URL,
            params=payload,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
        forecast = r.json()
        if not isinstance(forecast, dict):
            raise ValueError("7Timer returned a non-object payload")
        return forecast

    try:
        result = cache.fetch_cached(
            key,
            cache.TTL_WEATHER_SEC,
            load,
            # Only a transport failure is worth answering from disk: a body we
            # cannot read means the service changed, and that is worth saying.
            failover_on=requests.RequestException,
        )
    except (requests.RequestException, ValueError):
        return {}
    return cast(dict[str, Any], result.value)


def validated_ephemeris_points(number: int | str) -> int:
    """Return *number* as a whole number of ephemeris points to request.

    Parameters
    ----------
    number : int or str
        The requested count, as typed in the UI or passed by a caller.

    Returns
    -------
    int
        *number* as an ``int``.

    Raises
    ------
    ValueError
        If *number* is not a whole number, or is outside
        :data:`MIN_EPHEMERIS_POINTS`/:data:`MAX_EPHEMERIS_POINTS`. The UI turns this
        into a translated message instead of silently asking for another count.
    """
    if isinstance(number, bool):
        raise ValueError(
            f"number of ephemeris points must be an integer, got {number!r}"
        )
    try:
        points = int(str(number).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"number of ephemeris points must be an integer, got {number!r}"
        ) from None
    if points < MIN_EPHEMERIS_POINTS or points > MAX_EPHEMERIS_POINTS:
        raise ValueError(
            f"number of ephemeris points must be between {MIN_EPHEMERIS_POINTS} "
            f"and {MAX_EPHEMERIS_POINTS}, got {points}"
        )
    return points


def weather_temperature(celsius: Any, unit: str = "C") -> str:
    """Return *celsius* rendered for *unit* (``"C"`` or ``"F"``), or ``"N/A"``.

    7Timer reports ``temp2m`` in Celsius; the Fahrenheit rendering keeps one
    decimal, the Celsius one keeps the value as the service reported it.
    """

    if celsius is None:
        return "N/A"
    if unit == "F":
        try:
            return f"{float(celsius) * 9 / 5 + 32:.1f} F"
        except (TypeError, ValueError):
            return "N/A"
    return f"{celsius} C"


def weather_forecast_report(
    config: ConfigParser, hours: int | None = None, temperature_unit: str = "C"
) -> str:
    """Fetch and format the 7Timer astronomical forecast as plain text.

    Returns a user-visible error message when the HTTP request fails or the body
    is not valid JSON; otherwise returns the plaintext rendering of the formatted table.

    Parameters
    ----------
    config : ConfigParser
        Observatory settings, used to build the request URL.
    hours : int, optional
        Show only the timepoints within this many hours of the forecast start
        (7Timer ``astro`` steps are 3-hourly). ``None`` shows the whole series.
    temperature_unit : str
        ``"C"`` (default) or ``"F"``: unit of the ``Temp`` column.

    Raises
    ------
    ValueError
        If *hours* is not a whole number of hours.
    """

    if hours is not None:
        hours = int(hours)
        if hours < 0:
            raise ValueError(f"hours must not be negative, got {hours}")
    configuration.load_config(config)
    weather_forecast = weather_forecast_raw(config)
    if not weather_forecast:
        return "Weather forecast request failed or the response was not valid JSON."

    table = QTable(
        [[""], [""], [""], [""], [""], [""], [""], [""], [""]],
        names=(
            "Time",
            "Clouds",
            "Seeing",
            "Transp",
            "Instab",
            "Temp",
            "RH",
            "Wind",
            "Precip",
        ),
        meta={"name": "Weather forecast"},
    )

    def map_or_na(mapping: dict[int, str], key: Any) -> str:
        return mapping.get(key, "N/A")

    for time in weather_forecast.get("dataseries", []):
        if not isinstance(time, dict):
            continue
        if hours is not None:
            timepoint = time.get("timepoint", 0)
            if not isinstance(timepoint, int) or timepoint > hours:
                continue
        try:
            when = weather_time(
                weather_forecast.get("init", ""),
                time.get("timepoint", 0),
            )
        except (TypeError, ValueError):
            when = "N/A"

        cloudcover = map_or_na(cloudcover_dict, time.get("cloudcover"))
        seeing = map_or_na(seeing_dict, time.get("seeing"))
        transp = map_or_na(transparency_dict, time.get("transparency"))
        lifted = map_or_na(liftedIndex_dict, time.get("lifted_index"))
        temp = weather_temperature(time.get("temp2m"), temperature_unit)
        rh = map_or_na(rh2m_dict, time.get("rh2m"))
        wind = time.get("wind10m") or {}
        wind_dir = wind.get("direction", "N/A")
        wind_speed = map_or_na(wind10m_speed_dict, wind.get("speed"))
        wind_str = f"{wind_dir} {wind_speed}"
        precip = time.get("prec_type", "N/A")

        table.add_row(
            [
                when,
                cloudcover,
                seeing,
                transp,
                lifted,
                temp,
                rh,
                wind_str,
                precip,
            ]
        )
    table.remove_row(0)
    return str(table)


def weather(config: ConfigParser) -> None:
    """Display weather forecast for the observatory location.

    Retrieves astronomical weather forecast data from 7Timer API for up to
    72 hours and displays it in a formatted table. Includes cloud cover,
    seeing conditions, transparency, atmospheric instability, temperature,
    relative humidity, wind conditions, and precipitation.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory latitude and longitude.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The forecast is retrieved via HTTPS from the 7Timer API (``astro`` product).
    Numeric codes are mapped using the module dictionaries.

    Raises nothing: network and HTTP failures are reported on stdout.
    """

    print(weather_forecast_report(config))
    print("\n\n\n\n")


def skycoord_format(coord: str, coordid: str) -> str:
    """Format celestial coordinates in a standardized string format.

    Converts coordinate strings to a standardized format suitable for
    astronomical use. Supports both right ascension (RA) and declination (Dec)
    formats.

    Parameters
    ----------
    coord : str
        The coordinate string to format. Should contain three numeric values
        separated by spaces or colons (e.g., '12 34 56.7' or '12:34:56.7').
    coordid : str
        The coordinate type identifier. Use 'ra' or 'RA' for right ascension,
        'dec' or 'Dec' for declination (case-insensitive).

    Returns
    -------
    str
        Formatted coordinate string:
        - For RA: 'HHhMMmSSs' format (e.g., '12h34m56s')
        - For Dec: 'DDdMMmSSs' format (e.g., '+45d30m15s')
        - Original string if input is invalid or coordid is unknown.

    Notes
    -----
    This function is intentionally defensive: when the input does not
    represent three numeric fields (hours/degrees, minutes, seconds),
    the original string is returned unchanged instead of raising an exception.
    Minutes and seconds are zero-padded to two digits.
    """
    # Normalize common separators and split
    coord = coord.strip()
    parts = coord.replace(":", " ").split()
    if len(parts) != 3:
        return coord

    hours_or_degrees, minutes, seconds = parts

    # Validate that h/deg and min are integers, and sec is numeric
    def _is_int_string(value: str) -> bool:
        try:
            int(value)
            return True
        except (TypeError, ValueError):
            return False

    def _is_numeric_string(value: str) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    if not (
        _is_int_string(hours_or_degrees)
        and _is_int_string(minutes)
        and _is_numeric_string(seconds)
    ):
        return coord

    # Zero-pad minutes and seconds to two digits; keep sign on the first part
    minutes = minutes.zfill(2)
    seconds = seconds.zfill(2)

    # Be liberal in what we accept: allow case-insensitive coord identifiers
    coordid_normalized = coordid.lower()

    if coordid_normalized == "ra":
        return f"{hours_or_degrees}h{minutes}m{seconds}s"
    elif coordid_normalized == "dec":
        return f"{hours_or_degrees}d{minutes}m{seconds}s"
    # Fallback to original coord if unknown coordid
    return coord


def is_visible(config: ConfigParser, coord: SkyCoord | list[str], time: Time) -> bool:
    """Check if an object is visible above the virtual horizon.

    Determines whether an object at the given celestial coordinates is
    visible from the observatory location at the specified time, taking into
    account the configured virtual horizon altitude thresholds for each
    cardinal direction.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location and virtual horizon settings.
    coord : Union[SkyCoord, List[str]]
        Celestial coordinates. When a list is given it must contain two RA/Dec
        strings convertible via :func:`skycoord_format`.
    time : Time
        Observation time (astropy Time object).

    Returns
    -------
    bool
        True if the object is above the virtual horizon threshold for its
        azimuth direction, False otherwise.

    Notes
    -----
    The function divides the sky into four azimuth sectors:
    - North: 315° to 45° (wrapping around 0°)
    - East: 45° to 135°
    - South: 135° to 225°
    - West: 225° to 315°

    Each sector has its own minimum altitude threshold configured in the
    virtual horizon settings.
    """
    configuration.load_config(config)
    location = earth_location_from_config(config)
    if isinstance(coord, list):
        coord = SkyCoord(
            skycoord_format(coord[0], "ra") + " " + skycoord_format(coord[1], "dec")
        )
    coord = coord.transform_to(AltAz(obstime=time, location=location))

    # Extract degrees for clear comparisons
    azimuth_deg: float = coord.az.to(u.deg).value
    altitude_deg: float = coord.alt.to(u.deg).value

    north_alt_threshold = float(config["Observatory"]["nord_altitude"])
    east_alt_threshold = float(config["Observatory"]["east_altitude"])
    south_alt_threshold = float(config["Observatory"]["south_altitude"])
    west_alt_threshold = float(config["Observatory"]["west_altitude"])

    # Define inclusive azimuth sectors with proper wrap-around for North
    in_north = azimuth_deg >= 315.0 or azimuth_deg < 45.0
    in_east = 45.0 <= azimuth_deg < 135.0
    in_south = 135.0 <= azimuth_deg < 225.0
    in_west = 225.0 <= azimuth_deg < 315.0

    if in_north and altitude_deg >= north_alt_threshold:
        return True
    if in_east and altitude_deg >= east_alt_threshold:
        return True
    if in_south and altitude_deg >= south_alt_threshold:
        return True
    return in_west and altitude_deg >= west_alt_threshold


class _TransportUnavailable(RuntimeError):
    """The request never reached the source (DNS, TLS, timeout, refused).

    Distinct from :class:`_UnexpectedResponse`: the first justifies answering
    from the cache, the second does not, because a body we do not recognize
    means the service changed and the user should be told.
    """


class _UnexpectedResponse(RuntimeError):
    """The source answered, but not with something usable."""


class _NoTargetTable(RuntimeError):
    """The What's Observable response carried no recognizable results table.

    Raised instead of returning an empty list so the caller can tell "the sky
    offers nothing" (a real, cacheable answer) from "the page is not what we
    expect" (a change worth reporting, and never worth caching).
    """


#: Volatile MPC form fields excluded from the target-list cache key. A CSRF token
#: is re-scraped on every run, so including it would make every key unique and
#: the cache would never be read.
_VOLATILE_FORM_FIELDS = frozenset({"authenticity_token"})


def _cacheable_form(body: Mapping[str, Any]) -> dict[str, Any]:
    """Return the POST fields that identify a query, minus the volatile ones."""

    return {
        name: value for name, value in body.items() if name not in _VOLATILE_FORM_FIELDS
    }


def _target_table_rows(content: bytes) -> list[list[str]] | None:
    """Extract the target rows from a What's Observable page, or ``None``.

    The 4th table is preferred (legacy behavior), then any table whose headers
    match the classic or extended MPC layout. ``None`` means the page carried no
    recognizable results table at all, which is not the same as a table with no
    rows in it.

    MPC currently uses either the classic columns (… Time / RA / Dec / Alt) or
    the extended layout with solar/lunar elongation and Begin/Max epochs (indices
    4–7 still map to Begin time / Beg RA / Dec / Alt for visibility filtering).
    Only non-empty data rows are returned.
    """

    soup = BeautifulSoup(content, "lxml")
    tables = soup.find_all("table")

    classic_headers = {"Designation", "Mag", "Time", "RA", "Dec", "Alt"}
    beg_headers = {
        "Designation",
        "Mag",
        "Begin Time",
        "Beg RA",
        "Beg Dec",
        "Beg Alt",
    }

    def matches_results(headers: set[str]) -> bool:
        return classic_headers.issubset(headers) or beg_headers.issubset(headers)

    target_table = None
    if len(tables) >= 4:
        fourth = tables[3]
        header_set = {
            h for h in (th.get_text(strip=True) for th in fourth.find_all("th")) if h
        }
        if matches_results(header_set):
            target_table = fourth
    if target_table is None:
        for candidate in tables:
            header_set = {
                h
                for h in (th.get_text(strip=True) for th in candidate.find_all("th"))
                if h
            }
            if matches_results(header_set):
                target_table = candidate
                break

    if target_table is None:
        return None

    data: list[list[str]] = []
    for row in target_table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        values = [cell.get_text(strip=True) for cell in cells]
        if any(values):
            data.append(values)
    return data


def observing_target_list_scraper(url: str, payload: dict[str, Any]) -> list[list[str]]:
    """Scrape observing target list data from a web page.

    Performs an ``application/x-www-form-urlencoded`` POST (same as the MPC
    What's Observable HTML form), then extracts observing-target table rows.

    Parameters
    ----------
    url : str
        The URL to POST to (typically :data:`MPC_WHATSUP_INDEX_URL`).
    payload : Dict[str, Any]
        Form fields for the MPC query (latitude/longitude, time window, filters,
        ``authenticity_token``, etc.). Values are serialized like a browser form.

    Returns
    -------
    List[List[str]]
        A list of rows, where each row is a list of strings representing
        the cell values from the target table. Returns an empty list if
        no suitable table is found.

    Notes
    -----
    The function prefers the 4th table on the page (legacy behavior), but
    will also search for tables containing expected headers. MPC currently
    uses either the classic columns (… Time / RA / Dec / Alt) or the extended
    layout with solar/lunar elongation and Begin/Max epochs (indices 4–7 still
    map to Begin time / Beg RA / Dec / Alt for visibility filtering). Only
    non-empty data rows are returned.

    The rows are cached for :data:`asteroidpy.cache.TTL_TARGET_LIST_SEC` under a
    key built from the query itself. The ``authenticity_token`` field is
    deliberately left out of that key: it changes on every run, and including it
    would mean the cache is never hit.

    Raises nothing: a request that fails, or a page with no recognizable table,
    yields an empty list — unless rows from the same query are still on disk, in
    which case those are returned instead.
    """
    # MPC Rails form expects a POST body, not query-string parameters.
    body: dict[str, Any] = dict(payload)
    if body.get("utf8") == "%E2%9C%93":
        body["utf8"] = "\u2713"

    key = cache.cache_key("whatsup-targets", url=url, body=_cacheable_form(body))

    def load() -> list[list[str]]:
        try:
            r = requests.post(
                url,
                data=body,
                headers=_MPC_BROWSER_HEADERS,
                timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            # Only a transport failure may be answered from the cache: a page
            # that no longer carries the table is a change worth reporting, and
            # silently returning yesterday's rows would hide it.
            raise _NoTargetTable(str(exc)) from exc
        rows = _target_table_rows(r.content)
        if rows is None:
            raise _NoTargetTable("no results table in the response")
        return rows

    try:
        result = cache.fetch_cached(
            key,
            cache.TTL_TARGET_LIST_SEC,
            load,
            failover_on=requests.RequestException,
        )
    except (requests.RequestException, _NoTargetTable):
        return []
    return cast(list[list[str]], result.value)


def observing_target_list(config: ConfigParser, payload: dict[str, Any]) -> QTable:
    """Generate an observing target list from the Minor Planet Center.

    Queries the MPC website for objects visible from the observatory location
    based on the provided parameters, filters them by virtual horizon visibility,
    and returns a formatted table.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location and virtual horizon settings.
    payload : Dict[str, Any]
        Dictionary of POST form fields including:
        - latitude, longitude: Observatory coordinates
        - year, month, day, hour, minute: Observation start time
        - duration: Observation duration
        - max_objects: Maximum number of objects to return
        - min_alt: Minimum altitude
        - solar_elong, lunar_elong: Minimum elongations
        - object_type: Type of objects ('mp', 'neo', or 'cmt')

    Returns
    -------
    QTable
        An astropy QTable containing visible objects with columns:
        - Designation: Object designation
        - Mag: Magnitude
        - Time: Observation time
        - RA: Right ascension
        - Dec: Declination
        - Alt: Altitude

    Notes
    -----
    Objects are filtered to only include those visible above the virtual
    horizon at the specified observation time. The function scrapes HTML
    from the MPC website and parses table data.
    """
    results = QTable(
        [[""], [""], [""], [""], [""], [""]],
        names=("Designation", "Mag", "Time", "RA", "Dec", "Alt"),
        meta={"name": "Observing Target List"},
    )
    data = observing_target_list_scraper(MPC_WHATSUP_INDEX_URL, payload)
    for d in data:
        if len(d) < MPC_MIN_COLS:
            continue
        try:
            observing_time = mpc_whatsup_table_cell_to_time(d[MPC_COL_TIME])
        except (ValueError, TypeError):
            continue
        if is_visible(
            config,
            [d[MPC_COL_RA], d[MPC_COL_DEC]],
            observing_time,
        ):
            results.add_row(
                [
                    d[MPC_COL_DESIGNATION],
                    d[MPC_COL_MAG],
                    d[MPC_COL_TIME].replace("z", ""),
                    skycoord_format(d[MPC_COL_RA], "ra"),
                    skycoord_format(d[MPC_COL_DEC], "dec"),
                    d[MPC_COL_ALT],
                ]
            )
    results.remove_row(0)
    return results


def neocp_confirmation(
    config: ConfigParser, min_score: int, max_magnitude: float, min_altitude: int
) -> QTable:
    """Generate a list of NEOcp (Near Earth Object Confirmation Page) candidates.

    Queries the Minor Planet Center's NEOcp database for near-Earth objects
    that meet the specified criteria and are visible from the observatory
    location. Includes ephemeris data such as velocity and direction.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location, MPC code, and virtual horizon settings.
    min_score : int
        Minimum score threshold for NEO candidates (higher scores indicate
        higher priority).
    max_magnitude : float
        Maximum visual magnitude (brighter objects have lower magnitudes).
    min_altitude : int
        Minimum altitude in degrees above the horizon.

    Returns
    -------
    QTable
        An astropy QTable containing NEOcp candidates with columns:
        - Temp_Desig: Temporary designation
        - Score: Priority score
        - R.A.: Right ascension
        - Decl: Declination
        - Alt: Altitude
        - V: Visual magnitude
        - Velocity "/min: Angular velocity in arcseconds per minute
        - Direction: Motion direction
        - NObs: Number of observations
        - Arc: Observation arc
        - Not_seen: Days since last observation

    Notes
    -----
    Objects are filtered by score, magnitude, altitude, and virtual horizon
    visibility. Ephemeris data is retrieved asynchronously for all candidates
    to calculate velocity and direction. Objects with zero velocity are
    excluded from the results.

    This function uses :func:`asyncio.run` internally when no asyncio event loop
    is already running. From async code, Jupyter, or any context where a loop
    is active, call :func:`async_neocp_confirmation` with ``await`` instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            async_neocp_confirmation(config, min_score, max_magnitude, min_altitude)
        )
    raise RuntimeError(
        "neocp_confirmation() cannot be used while an asyncio event loop is running "
        "(e.g. inside async code or Jupyter). Use "
        "await async_neocp_confirmation(config, min_score, max_magnitude, min_altitude) "
        "instead."
    )


async def async_neocp_confirmation(
    config: ConfigParser, min_score: int, max_magnitude: float, min_altitude: int
) -> QTable:
    """Async implementation of NEOcp candidate table generation.

    Use this from code that already runs an asyncio event loop instead of
    :func:`neocp_confirmation`.
    """
    configuration.load_config(config)
    # r=requests.get('https://www.minorplanetcenter.net/Extended_Files/neocp.json')
    # data=r.json()
    # Pre-create result table so we can return it early if needed
    table = QTable(
        [[""], [0], [""], [""], [0.0], [0.0], [0.0], [0.0], [0], [0.0], [0.0]],
        names=(
            "Temp_Desig",
            "Score",
            "R.A.",
            "Decl",
            "Alt",
            "V",
            'Velocity "/min',
            "Direction",
            "NObs",
            "Arc",
            "Not_seen",
        ),
        meta={"name": "NEOcp confirmation"},
    )
    data_raw, response, fetch_ok = await fetch_neocp_json_and_ephemeris(config)
    if not fetch_ok:
        table.remove_row(0)
        return table

    data = data_raw
    try:
        min_altitude_deg = float(min_altitude)
    except (TypeError, ValueError):
        min_altitude_deg = 0.0

    location = earth_location_from_config(config)
    observing_date = Time(datetime.datetime.now(datetime.UTC))
    altaz = AltAz(location=location, obstime=observing_date)

    # table already created above
    for item in data:
        coord = SkyCoord(float(item["R.A."]) * u.deg, float(item["Decl."]) * u.deg)
        coord_altaz = coord.transform_to(altaz)
        try:
            score = int(item["Score"])
            mag = float(item["V"])
        except (ValueError, TypeError):
            continue
        # Apply score, magnitude, altitude threshold and visibility filters
        if (
            score > min_score
            and mag < max_magnitude
            and coord_altaz.alt.to(u.deg).value > min_altitude_deg
            and is_visible(config, coord, observing_date)
        ):
            # Safely access ephemeris data with bounds checking
            temp_desig = item["Temp_Desig"]

            if (
                temp_desig in response
                and len(response[temp_desig]) >= NEOCP_EPHEM_MIN_LEN
            ):
                velocity = float(response[temp_desig][NEOCP_EPHEM_VELOCITY_IDX])
                direction = float(response[temp_desig][NEOCP_EPHEM_DIRECTION_IDX])
            else:
                # Use default values if ephemeris data is not available
                velocity = 0.0
                direction = 0.0

            if velocity == 0.0:
                continue

            table.add_row(
                [
                    temp_desig,
                    score,
                    coord.ra.to_string(u.hour),
                    coord.dec.to_string(u.degree, alwayssign=True),
                    coord_altaz.alt,
                    mag,
                    velocity,
                    direction,
                    int(item["NObs"]),
                    float(item["Arc"]),
                    float(item["Not_Seen_dys"]),
                ]
            )
    table.remove_row(0)
    return table


def _neocp_viewing_point_fields(config: ConfigParser) -> str:
    """Build the ``Parallax``/``obscode``/``long``/``lat``/``alt`` form fields.

    ``Parallax`` selects the MPC confirmeph2 viewing point and the CGI honours only
    the matching fields, so a real ``mpc_code`` always wins. Otherwise the
    ``[Observatory]`` coordinates drive the ephemeris when they differ from the
    shipped defaults, keeping the MPC in step with the coordinates the local
    altitude and virtual-horizon filters already use; with no usable site or no
    coordinates, the geocenter is requested.

    ``long``/``lat`` are validated for every ``Parallax`` value, so unparsable or
    blank coordinates are sent as ``0.0`` rather than failing the whole request.
    """

    observatory = config["Observatory"]
    defaults = configuration.SECTION_DEFAULTS["Observatory"]

    def option_float(option: str) -> float | None:
        raw = observatory.get(option) or defaults.get(option, "")
        try:
            return float(raw)
        except ValueError:
            return None

    obs_code = (observatory.get("mpc_code") or "").strip()
    latitude = option_float("latitude")
    longitude = option_float("longitude")
    altitude = option_float("altitude")

    generic_code = obs_code.upper() in NEOCP_GENERIC_MPC_CODES
    coordinates_set = (
        latitude is not None
        and longitude is not None
        and (
            (latitude, longitude)
            != (float(defaults["latitude"]), float(defaults["longitude"]))
        )
    )

    if not generic_code:
        parallax = NEOCP_PARALLAX_OBS_CODE
    elif coordinates_set:
        parallax = NEOCP_PARALLAX_COORDINATES
    else:
        parallax = NEOCP_PARALLAX_GEOCENTRIC

    return (
        f"Parallax={parallax}"
        f"&obscode={obs_code}"
        f"&long={0.0 if latitude is None else latitude}"
        f"&lat={0.0 if longitude is None else longitude}"
        f"&alt={0.0 if altitude is None else altitude}"
    )


def _parse_neocp_ephemerides(response_text: str) -> dict[str, list[str]]:
    """Parse confirmeph2 HTML into ``designation -> ephemeris values``.

    The third line of each ``<pre>`` block carries the ephemeris row; blocks with
    fewer than four values are skipped, as they were before the response was
    made cacheable.
    """

    pattern = r"<b>([A-Za-z0-9]+)</b>[\s\S]*?<pre>([\s\S]*?)</pre>"
    matches = re.findall(pattern, response_text)

    result: dict[str, list[str]] = {}
    for designation, block in matches:
        lines = block.strip().split("\n")
        if len(lines) > 2:
            second_line = lines[2]
        else:
            second_line = lines[0] if lines else ""

        values_array = re.split(r"\s+", second_line.strip())
        if len(values_array) < 4:
            continue
        result[designation] = [val for val in values_array if val]

    return result


async def get_neocp_ephemeris(
    config: ConfigParser, object_names: list[str]
) -> dict[str, list[str]]:
    """Retrieve ephemeris data for NEOcp objects from the Minor Planet Center.

    Queries the MPC confirmation ephemeris service for multiple objects and
    parses the HTML response to extract ephemeris data including velocity
    and direction information.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location and MPC code.
    object_names : List[str]
        Temporary designations for NEOcp objects to query.

    Returns
    -------
    Dict[str, List[str]]
        Dictionary mapping object temporary designations to lists of
        ephemeris values. Each list contains parsed values from the ephemeris
        table, including velocity at index ``NEOCP_EPHEM_VELOCITY_IDX``
        and direction at ``NEOCP_EPHEM_DIRECTION_IDX``.

    Notes
    -----
    The function constructs a form-encoded payload with observation parameters
    and queries the MPC CGI service. The HTML response is parsed using regex
    to extract ephemeris data. Only objects with at least 4 values in their
    ephemeris data are included in the results.

    The viewing point is resolved by :func:`_neocp_viewing_point_fields` from
    ``[Observatory] mpc_code``, ``latitude``, ``longitude`` and ``altitude``,
    so the returned velocity and direction are computed for the same site the
    caller filters on locally. Those fields, together with the sorted object
    designations, form the cache key, so moving the observatory invalidates the
    entries computed for the old site.
    """
    configuration.load_config(config)
    object_names_str = ",".join(object_names)
    payload = f"mb=-30&mf=30&dl=-90&du=%2B90&nl=0&nu=100&sort=d&W=j&obj={object_names_str}&{_neocp_viewing_point_fields(config)}&int=0&start=0&raty=a&mot=m&dmot=p&out=f&sun=x&oalt=20"
    url = "https://cgi.minorplanetcenter.net/cgi-bin/confirmeph2.cgi"
    key = cache.cache_key(
        "neocp-ephemerides",
        url=url,
        payload=payload,
        objects=sorted(set(object_names)),
    )

    async def load() -> dict[str, list[str]]:
        timeout = httpx.Timeout(DEFAULT_REQUEST_TIMEOUT_SEC)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                content=payload,
            )
        return _parse_neocp_ephemerides(r.text)

    try:
        result = await cache.fetch_cached_async(
            key,
            cache.TTL_NEOCP_EPHEM_SEC,
            load,
            failover_on=httpx.RequestError,
        )
    except httpx.RequestError:
        return {}
    return cast(dict[str, list[str]], result.value)


async def fetch_neocp_json_and_ephemeris(
    config: ConfigParser,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], bool]:
    """Download NEOcp JSON and MPC confirm ephemerides in one event-loop run.

    The feed is cached for :data:`asteroidpy.cache.TTL_NEOCP_JSON_SEC` and the
    ephemerides for :data:`asteroidpy.cache.TTL_NEOCP_EPHEM_SEC`, so re-opening
    the NEOcp screen minutes apart does not re-query the MPC.
    """

    key = cache.cache_key("neocp-json", url=NEOCP_JSON_URL)

    async def load() -> list[dict[str, Any]]:
        data_raw, status = await httpx_get(NEOCP_JSON_URL, {}, "json")
        if status == 0:
            # httpx_get reports a transport failure as status 0; the cache needs
            # to see it as a failure rather than as an empty answer.
            raise _TransportUnavailable("neocp.json is unreachable")
        if status != 200 or not isinstance(data_raw, list):
            raise _UnexpectedResponse(f"neocp.json answered with HTTP {status}")
        return data_raw

    try:
        result = await cache.fetch_cached_async(
            key,
            cache.TTL_NEOCP_JSON_SEC,
            load,
            failover_on=_TransportUnavailable,
        )
    except (httpx.RequestError, ValueError, _TransportUnavailable, _UnexpectedResponse):
        return [], {}, False

    data_raw = cast(list[dict[str, Any]], result.value)
    designation_names = [item["Temp_Desig"] for item in data_raw]
    if not designation_names:
        return data_raw, {}, True

    response = await get_neocp_ephemeris(config, designation_names)
    return data_raw, response, True


def twilight_times(config: ConfigParser) -> dict[str, Any]:
    """Calculate twilight times for the observatory location.

    Computes civil, nautical, and astronomical twilight times (both morning
    and evening) for the next occurrence from the current UTC time.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location (latitude, longitude, altitude) and name.

    Returns
    -------
    Dict[str, Time]
        Dictionary containing twilight times with keys:
        - 'CivilM': Morning civil twilight (astropy Time)
        - 'CivilE': Evening civil twilight (astropy Time)
        - 'NautiM': Morning nautical twilight (astropy Time)
        - 'NautiE': Evening nautical twilight (astropy Time)
        - 'AstroM': Morning astronomical twilight (astropy Time)
        - 'AstroE': Evening astronomical twilight (astropy Time)

    Notes
    -----
    All times are calculated for the next occurrence from the current UTC time
    using the astroplan Observer class. Twilight definitions:
    - Civil: Sun 6° below horizon
    - Nautical: Sun 12° below horizon
    - Astronomical: Sun 18° below horizon
    """
    configuration.load_config(config)
    location = earth_location_from_config(config)
    observer = Observer(name=config["Observatory"]["obs_name"], location=location)
    observing_date = Time(datetime.datetime.now(datetime.UTC))
    result = {
        "AstroM": observer.twilight_morning_astronomical(observing_date, which="next"),
        "AstroE": observer.twilight_evening_astronomical(observing_date, which="next"),
        "CivilM": observer.twilight_morning_civil(observing_date, which="next"),
        "CivilE": observer.twilight_evening_civil(observing_date, which="next"),
        "NautiM": observer.twilight_morning_nautical(observing_date, which="next"),
        "NautiE": observer.twilight_evening_nautical(observing_date, which="next"),
    }
    return result


def sun_moon_ephemeris(config: ConfigParser) -> dict[str, Any]:
    """Calculate Sun and Moon ephemeris for the observatory location.

    Computes sunrise, sunset, moonrise, moonset times and moon illumination
    for the next occurrence from the current UTC time.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location (latitude, longitude, altitude) and name.

    Returns
    -------
    Dict[str, Union[Time, float]]
        Dictionary containing ephemeris data with keys:
        - 'Sunrise': Next sunrise time (astropy Time)
        - 'Sunset': Next sunset time (astropy Time)
        - 'Moonrise': Next moonrise time (astropy Time)
        - 'Moonset': Next moonset time (astropy Time)
        - 'MoonIll': Moon illumination fraction (float, 0.0 to 1.0)

    Notes
    -----
    All times are calculated for the next occurrence from the current UTC time
    using the astroplan Observer class. Moon illumination is a fraction
    between 0.0 (new moon) and 1.0 (full moon).
    """
    configuration.load_config(config)
    location = earth_location_from_config(config)
    observer = Observer(name=config["Observatory"]["obs_name"], location=location)
    observing_date = Time(datetime.datetime.now(datetime.UTC))
    result = {
        "Sunrise": observer.sun_rise_time(observing_date, which="next"),
        "Sunset": observer.sun_set_time(observing_date, which="next"),
        "Moonrise": observer.moon_rise_time(observing_date, which="next"),
        "Moonset": observer.moon_set_time(observing_date, which="next"),
        "MoonIll": observer.moon_illumination(observing_date),
    }
    return result


def object_ephemeris(
    config: ConfigParser,
    object_name: str,
    stepping: str,
    number: int | str = DEFAULT_EPHEMERIS_POINTS,
) -> QTable:
    """Retrieve ephemeris data for a specific object from the Minor Planet Center.

    Queries the MPC database for ephemeris data of the specified object,
    calculated for the observatory location with the requested time step.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location (latitude, longitude, altitude).
    object_name : str
        The object designation or name (e.g., 'Ceres', '2001 AA').
        The name is automatically converted to uppercase.
    stepping : str
        Time step between ephemeris points. Valid options:
        - 'm': 1 minute
        - 'h': 1 hour
        - 'd': 1 day
        - 'w': 1 week
        Defaults to '1h' if an unknown value is provided.
    number : int, optional
        How many points to request, :data:`DEFAULT_EPHEMERIS_POINTS` by default.

    Returns
    -------
    QTable
        An astropy QTable with *number* ephemeris points and columns:
        - Date: Observation date/time
        - RA: Right ascension
        - Dec: Declination
        - Elongation: Solar elongation
        - V: Visual magnitude
        - Altitude: Altitude above horizon
        - Proper motion: Angular motion
        - Direction: Motion direction

    Raises
    ------
    ValueError
        If *number* is not a whole number within
        :data:`MIN_EPHEMERIS_POINTS`/:data:`MAX_EPHEMERIS_POINTS`, checked by
        :func:`validated_ephemeris_points`.

    Notes
    -----
    The function uses astroquery.mpc.MPC to query the Minor Planet Center
    database. Ephemeris is calculated for the configured observatory location.
    """
    points = validated_ephemeris_points(number)
    configuration.load_config(config)
    location = earth_location_from_config(config)
    step: Quantity | str
    if stepping == "m":
        step = 1 * u.minute
    elif stepping == "h":
        step = "1h"
    elif stepping == "d":
        step = "1d"
    elif stepping == "w":
        step = "7d"
    else:
        # Default to 1 hour if unknown stepping value
        step = "1h"
    eph = MPC.get_ephemeris(
        str(object_name).upper(), location=location, step=step, number=points
    )
    ephemeris = eph[
        "Date", "RA", "Dec", "Elongation", "V", "Altitude", "Proper motion", "Direction"
    ]
    return ephemeris


class PlannerValueError(ValueError):
    """Raised for a ``[Planner]`` value that the best-night planner cannot use.

    *reason* is a stable machine-readable code, so a UI can pick a translated
    message without parsing prose, and *options* lists the INI option names to
    blame. Reasons:

    * ``not_a_number`` — the value is not numeric;
    * ``not_an_integer`` — ``max_nights`` is not a whole number;
    * ``out_of_range`` — the value is negative, not finite, or below the minimum
      (weights must be non-negative, ``max_nights`` at least 1);
    * ``zero_sum`` — every weight is zero, which would leave the score undefined.
    """

    def __init__(self, reason: str, options: Sequence[str]) -> None:
        super().__init__(f"{reason}: {', '.join(options)}")
        self.reason = reason
        self.options = tuple(options)


def _weight_problem(raw: Any) -> str | None:
    """Return why *raw* is unusable as a planner weight, or None when it is fine."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return "not_a_number"
    if not math.isfinite(value) or value < 0:
        return "out_of_range"
    return None


def normalize_planner_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Validate planner weights and return them divided by their sum.

    This is the single place where the weighting rules live: the in-app editor
    validates with it before saving, and :func:`best_nights` applies the result
    to every night it ranks.

    Raises
    ------
    PlannerValueError
        If a weight is not a finite non-negative number, or all of them are zero
        (the score would divide by zero).
    """
    problems = [(factor, _weight_problem(value)) for factor, value in weights.items()]
    invalid = [(factor, reason) for factor, reason in problems if reason is not None]
    if invalid:
        raise PlannerValueError(
            invalid[0][1], [PLANNER_WEIGHT_OPTIONS.get(f, f) for f, _ in invalid]
        )
    total = math.fsum(float(value) for value in weights.values())
    if total <= 0:
        raise PlannerValueError("zero_sum", list(PLANNER_WEIGHT_OPTIONS.values()))
    return {factor: float(value) / total for factor, value in weights.items()}


def parse_planner_max_nights(raw: Any) -> int:
    """Return ``[Planner] max_nights`` as a whole number of nights (at least 1).

    Raises
    ------
    PlannerValueError
        If *raw* is not an integer or is below 1. The editor must refuse to store
        such a value, while :func:`planner_settings` stays tolerant of a
        hand-edited file.
    """
    if isinstance(raw, bool):
        raise PlannerValueError("not_an_integer", ("max_nights",))
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise PlannerValueError("not_an_integer", ("max_nights",)) from None
    if value < 1:
        raise PlannerValueError("out_of_range", ("max_nights",))
    return value


def parse_planner_weights(raw: Mapping[str, Any]) -> dict[str, float]:
    """Parse raw ``[Planner]`` values into the weights the scorer really uses.

    Options absent from *raw* fall back to :data:`DEFAULT_PLANNER_WEIGHTS`; the
    result is normalized to sum to 1, so the editor can show the user the numbers
    that will be applied (see :func:`normalize_planner_weights`).

    Raises
    ------
    PlannerValueError
        If any weight is unusable, naming every offending option.
    """
    parsed: dict[str, float] = {}
    problems: list[str] = []
    reason = ""
    for factor, option in PLANNER_WEIGHT_OPTIONS.items():
        value = raw.get(option, DEFAULT_PLANNER_WEIGHTS[factor])
        problem = _weight_problem(value)
        if problem is None:
            parsed[factor] = float(value)
        else:
            problems.append(option)
            reason = reason or problem
    if problems:
        raise PlannerValueError(reason, problems)
    return normalize_planner_weights(parsed)


def planner_settings(config: ConfigParser) -> dict[str, Any]:
    """Return the planner tuning of *config*, tolerating a hand-edited INI file.

    The returned mapping has two keys: ``max_nights`` (an ``int`` of at least 1)
    and ``weights`` (the four factors, normalized to sum to 1). Each option is read
    through its strict parser, so the accepted ranges are defined once in
    :func:`parse_planner_max_nights` and :func:`parse_planner_weights`; a value
    those reject falls back to :data:`DEFAULT_PLANNER_MAX_NIGHTS` or, weight by
    weight, to :data:`DEFAULT_PLANNER_WEIGHTS`.

    A negative or non-finite weight is rejected because it would invert a quality
    factor (a negative ``w_moon`` would reward a brighter Moon) and let the score
    leave the 0-100 range.
    """
    if not config.has_section("Planner"):
        return {
            "max_nights": DEFAULT_PLANNER_MAX_NIGHTS,
            "weights": dict(DEFAULT_PLANNER_WEIGHTS),
        }
    section = config["Planner"]

    try:
        max_nights = parse_planner_max_nights(section.get("max_nights", ""))
    except PlannerValueError:
        max_nights = DEFAULT_PLANNER_MAX_NIGHTS

    weights: dict[str, float] = {}
    for factor, option in PLANNER_WEIGHT_OPTIONS.items():
        value = section.get(option, DEFAULT_PLANNER_WEIGHTS[factor])
        weights[factor] = (
            float(value)
            if _weight_problem(value) is None
            else DEFAULT_PLANNER_WEIGHTS[factor]
        )
    try:
        normalized = normalize_planner_weights(weights)
    except PlannerValueError:
        # All-zero weights (or a bad mix that still adds up to nothing): start over.
        normalized = dict(DEFAULT_PLANNER_WEIGHTS)
    return {"max_nights": max_nights, "weights": normalized}


def astronomical_night(config: ConfigParser, date: datetime.date) -> tuple[Time, Time]:
    """Return ``(evening, morning)`` astronomical twilight for the night of *date*.

    The bright-limit is the evening astronomical twilight after *date* and the
    end is the following morning's astronomical twilight. Twilight is searched
    from local solar noon (approximated as ``12:00 - longitude/15`` UTC) so both
    horizons are resolved for any longitude.

    Returns
    -------
    tuple
        ``(evening, morning)`` astropy :class:`~astropy.time.Time` in UTC.
    """

    location = earth_location_from_config(config)
    observer = Observer(name=config["Observatory"]["obs_name"], location=location)
    try:
        longitude = float(config["Observatory"]["longitude"])
    except (KeyError, ValueError):
        longitude = 0.0
    solar_noon_hour = 12.0 - longitude / 15.0
    reference = Time(
        datetime.datetime(date.year, date.month, date.day)
        + datetime.timedelta(hours=solar_noon_hour)
    )
    evening = observer.twilight_evening_astronomical(reference, which="next")
    morning = observer.twilight_morning_astronomical(reference, which="next")
    return evening, morning


def _forecast_start(init: str) -> datetime.datetime | None:
    """Parse the 7Timer ``init`` stamp (``YYYYMMDDHHMM``) into a datetime.

    Returns ``None`` when the stamp is missing or malformed, so the caller can
    report an unusable forecast instead of raising.
    """
    try:
        return datetime.datetime(
            int(init[0:4]),
            int(init[4:6]),
            int(init[6:8]),
            int(init[8:10]),
        )
    except (ValueError, TypeError):
        return None


def _forecast_points(
    dataseries: Any, time_start: datetime.datetime
) -> list[tuple[Time, dict[str, Any]]]:
    """Turn 7Timer timepoints (hours since ``init``) into absolute astropy times.

    Entries that are not mappings, or that carry no usable ``timepoint``, are
    skipped: 7Timer occasionally returns a partially malformed series and one
    bad entry must not invalidate the whole forecast.
    """
    points: list[tuple[Time, dict[str, Any]]] = []
    for item in dataseries:
        if not isinstance(item, dict):
            continue
        timepoint = item.get("timepoint")
        if timepoint is None:
            continue
        try:
            hours = int(timepoint)
        except (TypeError, ValueError):
            continue
        points.append((Time(time_start + datetime.timedelta(hours=hours)), item))
    return points


def _night_windows(
    config: ConfigParser, first_date: datetime.date, last_date: datetime.date
) -> list[dict[str, Any]]:
    """Return the astronomical twilight window of every night in the forecast span.

    Dates whose twilight cannot be resolved are skipped, and inverted windows
    (polar day or polar night) are dropped because no timepoint can fall in them.
    """
    windows: list[dict[str, Any]] = []
    date = first_date
    one_day = datetime.timedelta(days=1)
    while date <= last_date:
        try:
            evening, morning = astronomical_night(config, date)
        except Exception:
            date += one_day
            continue
        if evening < morning:
            windows.append({"date": date, "start": evening, "end": morning})
        date += one_day
    return windows


class _NightConditions(NamedTuple):
    """Forecast values collected from the timepoints falling inside one night."""

    clouds: list[float]
    seeing: list[int]
    transparency: list[int]
    precipitation: bool


def _night_conditions(
    night: dict[str, Any], points: list[tuple[Time, dict[str, Any]]]
) -> _NightConditions:
    """Aggregate the forecast codes of every timepoint inside a night window."""
    clouds: list[float] = []
    seeing: list[int] = []
    transparency: list[int] = []
    precipitation = False
    for t, item in points:
        if not (night["start"] <= t < night["end"]):
            continue
        cloudcover = item.get("cloudcover")
        if isinstance(cloudcover, int):
            clouds.append(CLOUDCOVER_MIDPOINT_PCT.get(cloudcover, float(cloudcover)))
        seeing_code = item.get("seeing")
        if isinstance(seeing_code, int):
            seeing.append(seeing_code)
        transparency_code = item.get("transparency")
        if isinstance(transparency_code, int):
            transparency.append(transparency_code)
        if str(item.get("prec_type") or "none").lower() in _PRECIPITATION_CODES:
            precipitation = True
    return _NightConditions(clouds, seeing, transparency, precipitation)


def _night_summary(
    night: dict[str, Any],
    points: list[tuple[Time, dict[str, Any]]],
    observer: Observer,
) -> dict[str, Any] | None:
    """Summarize one night window, or ``None`` when the night is not usable.

    A night is discarded when it reports any precipitation, or when no
    cloud-cover timepoint falls inside the window (the score cannot be computed).
    """
    clouds, seeing, transparency, precipitation = _night_conditions(night, points)
    if not clouds or precipitation:
        return None
    middle = night["start"] + (night["end"] - night["start"]) / 2
    return {
        "date": night["date"],
        "start": night["start"],
        "end": night["end"],
        "length_h": float((night["end"] - night["start"]).to_value(u.hour)),
        "avg_cloud_pct": sum(clouds) / len(clouds),
        "avg_seeing": (sum(seeing) / len(seeing)) if seeing else 6.0,
        "avg_transparency": (
            (sum(transparency) / len(transparency)) if transparency else 2.0
        ),
        "moon_illum": float(observer.moon_illumination(middle)),
        "score": 0.0,
    }


def _score_night(entry: dict[str, Any], weights: dict[str, float]) -> None:
    """Fill in ``entry["score"]`` (0-100, 100 = ideal) from the night conditions.

    Each factor is mapped to a 0-1 quality first, then combined with the
    ``[Planner]`` weights.
    """
    cloud_quality = 1.0 - entry["avg_cloud_pct"] / 100.0
    seeing_quality = 1.0 - (entry["avg_seeing"] - 1.0) / 7.0
    transparency_quality = (entry["avg_transparency"] - 1.0) / 7.0
    moon_quality = 1.0 - entry["moon_illum"]
    entry["score"] = 100.0 * (
        weights["cloud"] * cloud_quality
        + weights["seeing"] * seeing_quality
        + weights["transparency"] * transparency_quality
        + weights["moon"] * moon_quality
    )


def best_nights(
    config: ConfigParser,
    max_nights: int | None = None,
    weights: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Rank upcoming astronomical nights from the 7Timer astro forecast.

    Each forecast timepoint is assigned to the night whose [evening, morning)
    astronomical twilight window contains it. Per night, the mean cloud cover
    (percent), seeing and transparency indices, and the Moon illumination at the
    middle of the night are combined into a 0–100 score using the ``[Planner]``
    weights (see :func:`planner_settings`).

    Nights containing any precipitation timepoint are discarded.

    Parameters
    ----------
    config : ConfigParser
        Observatory settings and optional ``[Planner]`` tuning.
    max_nights : int, optional
        Override ``[Planner] max_nights``; defaults to the configured value.
    weights : mapping, optional
        Score with these weights instead of the configured ones, which is how the
        planner editor previews unsaved values. They are validated and normalized
        by :func:`normalize_planner_weights`.

    Returns
    -------
    list of dict
        Each entry has ``date`` (start date), ``start``/``end`` (astropy Time),
        ``length_h``, ``avg_cloud_pct``, ``avg_seeing``, ``avg_transparency``,
        ``moon_illum`` and ``score`` (100 = ideal). Empty when no forecast data.

    Raises
    ------
    PlannerValueError
        If *weights* is supplied and unusable.
    """

    configuration.load_config(config)
    data = weather_forecast_raw(config)
    time_start = _forecast_start(data.get("init") or "")
    if time_start is None:
        return []
    points = _forecast_points(data.get("dataseries", []), time_start)
    if not points:
        return []

    windows = _night_windows(
        config, points[0][0].datetime.date(), points[-1][0].datetime.date()
    )
    observer = Observer(
        name=config["Observatory"]["obs_name"],
        location=earth_location_from_config(config),
    )

    results: list[dict[str, Any]] = []
    for night in windows:
        entry = _night_summary(night, points, observer)
        if entry is not None:
            results.append(entry)

    settings = planner_settings(config)
    scoring_weights = (
        settings["weights"] if weights is None else normalize_planner_weights(weights)
    )
    for entry in results:
        _score_night(entry, scoring_weights)
    results.sort(key=lambda entry: entry["score"], reverse=True)
    if max_nights is None:
        max_nights = settings["max_nights"]
    return results[: max(1, max_nights)]


def best_nights_report(config: ConfigParser, max_nights: int | None = None) -> str:
    """Render :func:`best_nights` as a plain-text ranking table.

    Returns a short error message when no forecast data is available.
    """

    settings = planner_settings(config)
    if max_nights is None:
        max_nights = settings["max_nights"]
    nights = best_nights(config, max_nights)
    if not nights:
        return "No weather forecast available."

    lines = ["Best upcoming nights"]
    for entry in nights:
        lines.append(
            f"{entry['date']}  "
            f"{entry['start'].strftime('%H:%M')} - {entry['end'].strftime('%H:%M')} UTC  "
            f"{entry['length_h']:>5.1f}h  "
            f"{entry['avg_cloud_pct']:>5.0f}%  "
            f"{entry['avg_seeing']:>4.1f}  "
            f"{entry['avg_transparency']:>5.2f}  "
            f"{entry['moon_illum']:>4.2f}  "
            f"{entry['score']:>5.1f}"
        )
    labels = "Date  Night (UTC)  Hours  Clouds  Seeing  Transp  Moon  Score".split()
    lines.insert(1, "  ".join(labels))
    lines.insert(2, "-" * len(lines[1]))
    weights = settings["weights"]
    weights_note = (
        f"Score weights: clouds {weights['cloud']:.2f}, "
        f"seeing {weights['seeing']:.2f}, "
        f"transparency {weights['transparency']:.2f}, "
        f"moon {weights['moon']:.2f} (higher is better)."
    )
    lines.append(weights_note)
    return "\n".join(lines)
