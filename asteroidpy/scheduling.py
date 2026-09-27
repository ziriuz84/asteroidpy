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
"""

import asyncio
import datetime
import math
import re
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

from asteroidpy import configuration

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

# Last-resort token if MPC blocks scraping or markup changes (POST may still fail).
_MPC_WHATSUP_AUTH_TOKEN_FALLBACK = "W5eBzzw9Clj4tJVzkz0z%2F2EK18jvSS%2BffHxZpAshylg%3D"

_MPC_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}


def _scrape_whatsup_authenticity_token() -> str:
    """Return '' if scraping did not recover a Rails authenticity_token."""

    try:
        r = requests.get(
            MPC_WHATSUP_INDEX_URL,
            headers=_MPC_BROWSER_HEADERS,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException:
        return ""
    if r.status_code != 200:
        return ""
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
    return ""


def resolve_whatsup_authenticity_token() -> tuple[str, bool]:
    """Return ``(authenticity_token, used_fallback)`` for MPC What's Observable POST."""

    scraped = _scrape_whatsup_authenticity_token()
    if scraped:
        return scraped, False
    return _MPC_WHATSUP_AUTH_TOKEN_FALLBACK, True


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
        Parsed JSON body, or ``{}`` when the request fails, times out, the
        server returns an error status, or the body is not valid JSON.
    """

    configuration.load_config(config)
    lat, long = config["Observatory"]["latitude"], config["Observatory"]["longitude"]
    payload = {"lon": long, "lat": lat, "product": product, "output": "json"}
    try:
        r = requests.get(
            SEVENTIMER_API_URL,
            params=payload,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
        weather_forecast = r.json()
    except requests.RequestException:
        return {}
    except ValueError:
        return {}
    if not isinstance(weather_forecast, dict):
        return {}
    return weather_forecast


def weather_forecast_report(config: ConfigParser) -> str:
    """Fetch and format the 7Timer astronomical forecast as plain text.

    Returns a user-visible error message when the HTTP request fails or the body
    is not valid JSON; otherwise returns the plaintext rendering of the formatted table.
    """

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
        temp = f"{time.get('temp2m', 'N/A')} C" if "temp2m" in time else "N/A"
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

    Raises nothing: failures return an empty list.
    """
    # MPC Rails form expects a POST body, not query-string parameters.
    body: dict[str, Any] = dict(payload)
    if body.get("utf8") == "%E2%9C%93":
        body["utf8"] = "\u2713"

    try:
        r = requests.post(
            url,
            data=body,
            headers=_MPC_BROWSER_HEADERS,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(r.content, "lxml")
    tables = soup.find_all("table")

    _classic_headers = {"Designation", "Mag", "Time", "RA", "Dec", "Alt"}
    _beg_headers = {
        "Designation",
        "Mag",
        "Begin Time",
        "Beg RA",
        "Beg Dec",
        "Beg Alt",
    }

    def _table_matches_results(headers: set[str]) -> bool:
        return _classic_headers.issubset(headers) or _beg_headers.issubset(headers)

    # Prefer the 4th table if present (legacy behavior), otherwise try to detect by headers
    target_table = None
    if len(tables) >= 4:
        fourth = tables[3]
        header_cells = [th.get_text(strip=True) for th in fourth.find_all("th")]
        header_set = {h for h in header_cells if h}
        if _table_matches_results(header_set):
            target_table = fourth
    if target_table is None:
        for candidate in tables:
            header_cells = [th.get_text(strip=True) for th in candidate.find_all("th")]
            header_set = {h for h in header_cells if h}
            if _table_matches_results(header_set):
                target_table = candidate
                break

    # If no suitable table was found, return an empty result gracefully
    if target_table is None:
        return []

    # Extract non-empty data rows, skipping header rows
    data: list[list[str]] = []
    for row in target_table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        values = [cell.get_text(strip=True) for cell in cells]
        if any(values):
            data.append(values)
    return data


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
    """
    configuration.load_config(config)
    object_names_str = ",".join(object_names)
    obs_code = (
        config["Observatory"]["mpc_code"] if config["Observatory"]["mpc_code"] else ""
    )
    latitude = (
        config["Observatory"]["latitude"] if config["Observatory"]["latitude"] else ""
    )
    longitude = (
        config["Observatory"]["longitude"] if config["Observatory"]["longitude"] else ""
    )
    payload = f"mb=-30&mf=30&dl=-90&du=%2B90&nl=0&nu=100&sort=d&W=j&obj={object_names_str}&Parallax=1&obscode={obs_code}&long={longitude}&lat={latitude}&int=0&start=0&raty=a&mot=m&dmot=p&out=f&sun=x&oalt=20"
    url = "https://cgi.minorplanetcenter.net/cgi-bin/confirmeph2.cgi"
    timeout = httpx.Timeout(DEFAULT_REQUEST_TIMEOUT_SEC)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                content=payload,
            )
        response_text = r.text
    except httpx.RequestError:
        response_text = ""

    pattern = r"<b>([A-Za-z0-9]+)</b>[\s\S]*?<pre>([\s\S]*?)</pre>"
    matches = re.findall(pattern, response_text)

    result_dict = {}
    for key, value in matches:
        lines = value.strip().split("\n")
        if len(lines) > 2:
            second_line = lines[2]
        else:
            second_line = lines[0] if lines else ""

        values_array = re.split(r"\s+", second_line.strip())

        if len(values_array) < 4:
            continue

        values_array = [val for val in values_array if val]

        result_dict[key] = values_array

    return result_dict


async def fetch_neocp_json_and_ephemeris(
    config: ConfigParser,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], bool]:
    """Download NEOcp JSON and MPC confirm ephemerides in one event-loop run."""

    data_raw, status = await httpx_get(
        "https://www.minorplanetcenter.net/Extended_Files/neocp.json",
        {},
        "json",
    )
    if status != 200 or not isinstance(data_raw, list):
        return [], {}, False

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


def object_ephemeris(config: ConfigParser, object_name: str, stepping: str) -> QTable:
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

    Returns
    -------
    QTable
        An astropy QTable containing 30 ephemeris points with columns:
        - Date: Observation date/time
        - RA: Right ascension
        - Dec: Declination
        - Elongation: Solar elongation
        - V: Visual magnitude
        - Altitude: Altitude above horizon
        - Proper motion: Angular motion
        - Direction: Motion direction

    Notes
    -----
    The function uses astroquery.mpc.MPC to query the Minor Planet Center
    database. Ephemeris is calculated for the configured observatory location.
    """
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
        str(object_name).upper(), location=location, step=step, number=30
    )
    ephemeris = eph[
        "Date", "RA", "Dec", "Elongation", "V", "Altitude", "Proper motion", "Direction"
    ]
    return ephemeris


def _planner_settings(config: ConfigParser) -> dict[str, Any]:
    """Return planner tuning from the ``[Planner]`` INI section with hardcoded fallback.

    ``max_nights`` is clamped to at least 1; weights are normalized to sum to 1.
    Any missing or non-numeric value falls back to :data:`DEFAULT_PLANNER_WEIGHTS`
    / :data:`DEFAULT_PLANNER_MAX_NIGHTS`.

    Weights must be finite and non-negative: a negative weight would invert a
    quality factor (a negative ``w_moon`` would reward a brighter Moon) and let
    the score leave the 0-100 range, so such a value is rejected in favour of
    its default.
    """

    if not config.has_section("Planner"):
        return {
            "max_nights": DEFAULT_PLANNER_MAX_NIGHTS,
            "weights": dict(DEFAULT_PLANNER_WEIGHTS),
        }
    section = config["Planner"]

    def _float(key: str, default: float) -> float:
        try:
            value = float(section.get(key, str(default)))
        except (TypeError, ValueError):
            return default
        if not math.isfinite(value) or value < 0:
            return default
        return value

    weights = {
        "cloud": _float("w_cloud", DEFAULT_PLANNER_WEIGHTS["cloud"]),
        "seeing": _float("w_seeing", DEFAULT_PLANNER_WEIGHTS["seeing"]),
        "transparency": _float(
            "w_transparency", DEFAULT_PLANNER_WEIGHTS["transparency"]
        ),
        "moon": _float("w_moon", DEFAULT_PLANNER_WEIGHTS["moon"]),
    }
    total = sum(weights.values())
    if total <= 0:
        weights = dict(DEFAULT_PLANNER_WEIGHTS)
        total = 1.0
    try:
        max_nights = int(section.get("max_nights", ""))
        if max_nights < 1:
            raise ValueError
    except (ValueError, TypeError):
        max_nights = DEFAULT_PLANNER_MAX_NIGHTS
    return {
        "max_nights": max_nights,
        "weights": {key: value / total for key, value in weights.items()},
    }


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
    config: ConfigParser, max_nights: int | None = None
) -> list[dict[str, Any]]:
    """Rank upcoming astronomical nights from the 7Timer astro forecast.

    Each forecast timepoint is assigned to the night whose [evening, morning)
    astronomical twilight window contains it. Per night, the mean cloud cover
    (percent), seeing and transparency indices, and the Moon illumination at the
    middle of the night are combined into a 0–100 score using the ``[Planner]``
    weights (see ``_planner_settings``).

    Nights containing any precipitation timepoint are discarded.

    Parameters
    ----------
    config : ConfigParser
        Observatory settings and optional ``[Planner]`` tuning.
    max_nights : int, optional
        Override ``[Planner] max_nights``; defaults to the configured value.

    Returns
    -------
    list of dict
        Each entry has ``date`` (start date), ``start``/``end`` (astropy Time),
        ``length_h``, ``avg_cloud_pct``, ``avg_seeing``, ``avg_transparency``,
        ``moon_illum`` and ``score`` (100 = ideal). Empty when no forecast data.
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

    settings = _planner_settings(config)
    for entry in results:
        _score_night(entry, settings["weights"])
    results.sort(key=lambda entry: entry["score"], reverse=True)
    if max_nights is None:
        max_nights = settings["max_nights"]
    return results[: max(1, max_nights)]


def best_nights_report(config: ConfigParser, max_nights: int | None = None) -> str:
    """Render :func:`best_nights` as a plain-text ranking table.

    Returns a short error message when no forecast data is available.
    """

    settings = _planner_settings(config)
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
