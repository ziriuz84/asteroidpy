import asyncio
import datetime
import re
from configparser import ConfigParser
from typing import Any, Dict, List, Literal, Tuple, Union, cast

import httpx
import requests
from astroplan import Observer
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.table import QTable
from astropy.time import Time
from astroquery.mpc import MPC
from astropy.units import Quantity
from bs4 import BeautifulSoup

from asteroidpy import configuration

SEVENTIMER_API_URL = "https://www.7timer.info/bin/api.pl"
DEFAULT_REQUEST_TIMEOUT_SEC = 30.0

# MPC whats-up HTML table columns (minimum 8 cells per data row).
MPC_COL_DESIGNATION = 0
MPC_COL_MAG = 1
MPC_COL_TIME = 4
MPC_COL_RA = 5
MPC_COL_DEC = 6
MPC_COL_ALT = 7
MPC_MIN_COLS = 8

MPC_WHATSUP_INDEX_URL = "https://www.minorplanetcenter.net/whatsup/index"

# Last-resort token if MPC blocks scraping or markup changes (POST may still fail).
_MPC_WHATSUP_AUTH_TOKEN_FALLBACK = (
    "W5eBzzw9Clj4tJVzkz0z%2F2EK18jvSS%2BffHxZpAshylg%3D"
)

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


def resolve_whatsup_authenticity_token() -> Tuple[str, bool]:
    """Return ``(authenticity_token, used_fallback)`` for MPC What's Observable POST."""

    scraped = _scrape_whatsup_authenticity_token()
    if scraped:
        return scraped, False
    return _MPC_WHATSUP_AUTH_TOKEN_FALLBACK, True


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
    payload: Dict[str, Any],
    return_type: Literal["json", "text"],
) -> Tuple[Union[Dict[str, Any], List[Dict[str, Any]], str], int]:
    """Perform an asynchronous HTTP GET request.

    Makes an async GET request to the specified URL with the given query
    parameters and returns the parsed response along with the status code.

    Parameters
    ----------
    url : str
        The URL to query.
    payload : dict of str to Any
        Dictionary of query parameters to include in the request.
    return_type : {'json', 'text'}
        ``'json'`` parses JSON responses; ``'text'`` returns response body text.

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
            return cast(
                Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], ({}, 0)
            )
        return ("", 0)

    if return_type == "json":
        try:
            parsed = r.json()
        except ValueError:
            parsed = {}
        return cast(
            Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int],
            (parsed, r.status_code),
        )
    else:
        return (r.text, r.status_code)


async def httpx_post(
    url: str,
    payload: Dict[str, Any],
    return_type: Literal["json", "text"],
) -> Tuple[Union[Dict[str, Any], List[Dict[str, Any]], str], int]:
    """Perform an asynchronous HTTP POST request.

    Makes an async POST request to the specified URL with the given form data
    and returns the parsed response along with the status code.

    Parameters
    ----------
    url : str
        The URL to query.
    payload : dict of str to Any
        Dictionary of form data to include in the POST request body.
    return_type : {'json', 'text'}
        Same semantics as :func:`httpx_get`.

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
            return cast(
                Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], ({}, 0)
            )
        return ("", 0)

    if return_type == "json":
        try:
            parsed = r.json()
        except ValueError:
            parsed = {}
        return cast(
            Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int],
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
    configuration.load_config(config)
    lat, long = config["Observatory"]["latitude"], config["Observatory"]["longitude"]
    payload = {"lon": long, "lat": lat, "product": "astro", "output": "json"}
    try:
        r = requests.get(
            SEVENTIMER_API_URL,
            params=payload,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
        weather_forecast = r.json()
    except requests.RequestException as exc:
        print(f"Weather forecast request failed ({exc}).")
        return
    except ValueError:
        print("Weather forecast response was not valid JSON.")
        return

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

    def map_or_na(mapping: Dict[int, str], key: Any) -> str:
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
    print(table)
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


def is_visible(
    config: ConfigParser, coord: Union[SkyCoord, List[str]], time: Time
) -> bool:
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
    coord : SkyCoord or list of str
        Celestial coordinates to check. Can be a SkyCoord object or a list
        of two strings [RA, Dec] that will be converted to SkyCoord.
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


def observing_target_list_scraper(url: str, payload: Dict[str, Any]) -> List[List[str]]:
    """Scrape observing target list data from a web page.

    Performs a POST request to the specified URL and extracts table data
    containing observing target information. The function looks for a table
    with specific headers related to asteroid observations.

    Parameters
    ----------
    url : str
        The URL to scrape for observing target data.
    payload : dict of str to Any
        Query parameters to include in the POST request URL.

    Returns
    -------
    list of list of str
        A list of rows, where each row is a list of strings representing
        the cell values from the target table. Returns an empty list if
        no suitable table is found.

    Notes
    -----
    The function prefers the 4th table on the page (legacy behavior), but
    will also search for tables containing expected headers like 'Designation',
    'Mag', 'Time', 'RA', 'Dec', 'Alt'. Only non-empty data rows are returned.

    Raises nothing: failures return an empty list.
    """
    try:
        r = requests.post(
            url,
            params=payload,
            timeout=DEFAULT_REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(r.content, "lxml")
    tables = soup.find_all("table")

    # Prefer the 4th table if present (legacy behavior), otherwise try to detect by headers
    target_table = None
    if len(tables) >= 4:
        target_table = tables[3]
    else:
        for candidate in tables:
            header_cells = [th.get_text(strip=True) for th in candidate.find_all("th")]
            header_set = set(h for h in header_cells if h)
            expected_headers = {"Designation", "Mag", "Time", "RA", "Dec", "Alt"}
            if expected_headers.issubset(header_set):
                target_table = candidate
                break

    # If no suitable table was found, return an empty result gracefully
    if target_table is None:
        return []

    # Extract non-empty data rows, skipping header rows
    data: List[List[str]] = []
    for row in target_table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        values = [cell.get_text(strip=True) for cell in cells]
        if any(values):
            data.append(values)
    return data


def observing_target_list(config: ConfigParser, payload: Dict[str, Any]) -> QTable:
    """Generate an observing target list from the Minor Planet Center.

    Queries the MPC website for objects visible from the observatory location
    based on the provided parameters, filters them by virtual horizon visibility,
    and returns a formatted table.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location and virtual horizon settings.
    payload : dict of str to Any
        Dictionary of query parameters including:
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
            observing_time = Time(
                d[MPC_COL_TIME].replace("T", " ").replace("z", "")
            )
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
            "Velocity \"/min",
            "Direction",
            "NObs",
            "Arc",
            "Not_seen",
        ),
        meta={"name": "NEOcp confirmation"},
    )
    data_raw, response, fetch_ok = asyncio.run(
        fetch_neocp_json_and_ephemeris(config)
    )
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
    config: ConfigParser, object_names: List[str]
) -> Dict[str, List[str]]:
    """Retrieve ephemeris data for NEOcp objects from the Minor Planet Center.

    Queries the MPC confirmation ephemeris service for multiple objects and
    parses the HTML response to extract ephemeris data including velocity
    and direction information.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options, including
        observatory location and MPC code.
    object_names : list of str
        List of temporary designations for NEOcp objects to query.

    Returns
    -------
    dict of str to list of str
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
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]], bool]:
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


def twilight_times(config: ConfigParser) -> Dict[str, Any]:
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
    dict of str to Time
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


def sun_moon_ephemeris(config: ConfigParser) -> Dict[str, Any]:
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
    dict of str to Time or float
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
    step: Union[Quantity, str]
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
