from configparser import ConfigParser
from typing import Dict, Tuple, List, Any, Union, Optional, cast
import requests
import asyncio
import datetime
import gettext

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

# Use globally installed gettext from interface.setup_gettext

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


async def httpx_get(url: str, payload: Dict[str, Any], return_type: str) -> Tuple[Union[Dict[str, Any], List[Dict[str, Any]], str], int]:
    """
    Returns result from get query

    Args:
      url(string): the url to be queried
      payload(dictionary of strings): the payload of the query
      return_type(string): the type of formatted return

    Returns:
      array: The result of query and status code of the response

    """
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=payload)
    except Exception:
        # Network/timeout or unexpected errors: return safe defaults and status 0
        if return_type == 'json':
            return cast(Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], ({}, 0))
        return ("", 0)

    if return_type == 'json':
        try:
            parsed = r.json()
        except Exception:
            parsed = {}
        return cast(Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], (parsed, r.status_code))
    else:
        return (r.text, r.status_code)


async def httpx_post(url: str, payload: Dict[str, Any], return_type: str) -> Tuple[Union[Dict[str, Any], List[Dict[str, Any]], str], int]:
    """
    Returns result from post query

    Args:
      url(string): the url to be queried
      payload(dictionary of strings): the payload of the query
      return_type(string): the type of formatted return

    Returns:
      array: The result of query and status code of the response

    """
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=payload)
    except Exception:
        if return_type == 'json':
            return cast(Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], ({}, 0))
        return ("", 0)

    if return_type == 'json':
        try:
            parsed = r.json()
        except Exception:
            parsed = {}
        return cast(Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], (parsed, r.status_code))
    else:
        return (r.text, r.status_code)


def weather_time(time_init: str, deltaT: int) -> str:
    """

    Parameters
    ----------
    time_init : string
        The start time of weather forecast
    deltaT : int
        The time from start time

    Returns
    -------

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
    """Prints Weather forecast up to 72 hours

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    configuration.load_config(config)
    lat, long = config["Observatory"]["latitude"], config["Observatory"]["longitude"]
    payload = {"lon": long, "lat": lat, "product": "astro", "output": "json"}
    r = requests.get("http://www.7timer.info/bin/api.pl", params=payload)
    weather_forecast = r.json()
    table = QTable([[""], [""], [""], [""], [""], [""], [""], [""], [""]],
                   names=('Time', 'Clouds', 'Seeing', 'Transp',
                          'Instab', 'Temp', 'RH', 'Wind', 'Precip'),
                   meta={'name': 'Weather forecast'})
    def map_or_na(mapping: Dict[int, str], key: Any) -> str:
        return mapping.get(key, 'N/A')

    for time in weather_forecast.get('dataseries', []):
        try:
            when = weather_time(
                weather_forecast.get('init', ''),
                time.get('timepoint', 0),
            )
        except (TypeError, ValueError):
            when = 'N/A'

        cloudcover = map_or_na(cloudcover_dict, time.get('cloudcover'))
        seeing = map_or_na(seeing_dict, time.get('seeing'))
        transp = map_or_na(transparency_dict, time.get('transparency'))
        lifted = map_or_na(liftedIndex_dict, time.get('lifted_index'))
        temp = f"{time.get('temp2m', 'N/A')} C" if 'temp2m' in time else 'N/A'
        rh = map_or_na(rh2m_dict, time.get('rh2m'))
        wind = time.get('wind10m') or {}
        wind_dir = wind.get('direction', 'N/A')
        wind_speed = map_or_na(wind10m_speed_dict, wind.get('speed'))
        wind_str = f"{wind_dir} {wind_speed}"
        precip = time.get('prec_type', 'N/A')

        table.add_row([
            when,
            cloudcover,
            seeing,
            transp,
            lifted,
            temp,
            rh,
            wind_str,
            precip,
        ])
    table.remove_row(0)
    print(table)
    print("\n\n\n\n")


def skycoord_format(coord: str, coordid: str) -> str:
    """Formats coordinates as described in coordid

    Parameters
    ----------
    coord : string
        the coordinates to be formatted
    coordid : string
        the format (either 'ra' or 'dec')

    Returns
    -------
    string
        Formatted coordinate or the original string if invalid.

    Notes
    -----
    This function is intentionally defensive: when the input does not
    represent three numeric fields (hours/degrees, minutes, seconds),
    the original string is returned unchanged instead of raising.
    """
    # Normalize common separators and split
    parts = coord.replace(":", " ").split()
    if len(parts) != 3:
        return coord

    hours_or_degrees, minutes, seconds = parts

    # Validate that all parts are integers (sign allowed on the first)
    def _is_int_string(value: str) -> bool:
        try:
            int(value)
            return True
        except (TypeError, ValueError):
            return False

    if not (_is_int_string(hours_or_degrees) and _is_int_string(minutes) and _is_int_string(seconds)):
        return coord

    # Zero-pad minutes and seconds to two digits; keep sign on the first part
    minutes = minutes.zfill(2)
    seconds = seconds.zfill(2)

    # Be liberal in what we accept: allow case-insensitive coord identifiers
    coordid_normalized = coordid.lower()

    if coordid_normalized == 'ra':
        return f"{hours_or_degrees}h{minutes}m{seconds}s"
    elif coordid_normalized == 'dec':
        return f"{hours_or_degrees}d{minutes}m{seconds}s"
    # Fallback to original coord if unknown coordid
    return coord


def is_visible(config: ConfigParser, coord: Union[SkyCoord, List[str]], time: Time) -> bool:
    """Compare object's coordinates with Virtual Horizon to find if it's visible

    Parameters
    ----------
    config : Configparser
        the configparser object with configuration options
    coord : SkyCoord or array of strings
        Coordinate to control
    time : Time
        time of the observation

    Returns
    -------


    """
    location = EarthLocation.from_geodetic(
        lat=float(config["Observatory"]["latitude"]) * u.deg,
        lon=float(config["Observatory"]["longitude"]) * u.deg,
        height=float(config["Observatory"]["altitude"]) * u.m,
    )
    if isinstance(coord, list):
        coord = SkyCoord(
            skycoord_format(coord[0], "ra") + " " + skycoord_format(coord[1], "dec")
        )
    coord = coord.transform_to(AltAz(obstime=time, location=location))
    configuration.load_config(config)

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
    """

    Parameters
    ----------
    url : string
        the url to scrape
    payload : dictionary of strings
        the payload of the request

    Returns
    -------

    """
    r = requests.post(url, params=payload)
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
    """Prints Observing target list from MPC

    Parameters
    ----------
    payload : dictionary of strings
        the payload of parameters
    config :


    Returns
    -------

    """
    results = QTable(
        [[""], [""], [""], [""], [""], [""]],
        names=("Designation", "Mag", "Time", "RA", "Dec", "Alt"),
        meta={"name": "Observing Target List"},
    )
    data = observing_target_list_scraper(
        "https://www.minorplanetcenter.net/whatsup/index", payload
    )
    for d in data:
        # Require at least 8 fields as used below; skip malformed rows defensively
        if len(d) < 8:
            continue
        try:
            observing_time = Time(d[4].replace("T", " ").replace("z", ""))
        except Exception:
            # Skip rows with unparseable time values
            continue
        if is_visible(config, [d[5], d[6]], observing_time):
            results.add_row(
                [
                    d[0],
                    d[1],
                    d[4].replace("z", ""),
                    skycoord_format(d[5], "ra"),
                    skycoord_format(d[6], "dec"),
                    d[7],
                ]
            )
    results.remove_row(0)
    return results


def neocp_confirmation(config: ConfigParser, min_score: int, max_magnitude: float, min_altitude: int) -> QTable:
    """Prints NEOcp visible at the moment

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option
    min_score : int
        The minimum score to query
    max_magnitude : int
        The maximum magnitude to query
    min_altitude : int
        The minimum altitude of the object

    Returns
    -------

    """
    configuration.load_config(config)
    # r=requests.get('https://www.minorplanetcenter.net/Extended_Files/neocp.json')
    # data=r.json()
    # Pre-create result table so we can return it early if needed
    table = QTable([[""], [0], [""], [""], [0.0], [0.0], [0], [0.0], [0.0]],
                   names=('Temp_Desig', 'Score', 'R.A.', 'Decl',
                          'Alt', 'V', 'NObs', 'Arc', 'Not_seen'),
                   meta={'name': 'NEOcp confirmation'})
    data_raw, _status = asyncio.run(httpx_get(
        'https://www.minorplanetcenter.net/Extended_Files/neocp.json', {}, 'json'))
    # The first element is expected to be a list of dicts
    if not isinstance(data_raw, list):
        table.remove_row(0)
        return table  # empty table
    data = data_raw
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    # Normalize altitude threshold once
    try:
        min_altitude_deg = float(min_altitude)
    except (TypeError, ValueError):
        min_altitude_deg = 0.0

    location = EarthLocation.from_geodetic(lon=float(long), lat=float(lat))
    observing_date = Time(datetime.datetime.now(datetime.UTC))
    altaz = AltAz(location=location, obstime=observing_date)
    # table already created above
    for item in data:
        coord = SkyCoord(float(item["R.A."]) * u.deg, float(item["Decl."]) * u.deg)
        coord_altaz = coord.transform_to(altaz)
        try:
            score = int(item['Score'])
            mag = float(item['V'])
        except (ValueError, TypeError):
            continue
        # Apply score, magnitude, altitude threshold and visibility filters
        if (
            score > min_score
            and mag < max_magnitude
            and coord_altaz.alt.to(u.deg).value > min_altitude_deg
            and is_visible(config, coord, observing_date)
        ):
            table.add_row([item['Temp_Desig'],
                           score,
                           coord.ra.to_string(u.hour),
                           coord.dec.to_string(u.degree, alwayssign=True),
                           coord_altaz.alt,
                           mag,
                           int(item['NObs']),
                           float(item['Arc']),
                           float(item['Not_Seen_dys'])])
    table.remove_row(0)
    return table


def twilight_times(config: ConfigParser) -> Dict[str, Any]:
    """Returns twilight times for a given location

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    configuration.load_config(config)
    location = EarthLocation.from_geodetic(
        float(config["Observatory"]["longitude"]) * u.deg,
        float(config["Observatory"]["latitude"]) * u.deg,
        float(config["Observatory"]["altitude"]) * u.m,
    )
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
    """Returns the Sun and Moon ephemeris

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    configuration.load_config(config)
    location = EarthLocation.from_geodetic(
        float(config["Observatory"]["longitude"]) * u.deg,
        float(config["Observatory"]["latitude"]) * u.deg,
        float(config["Observatory"]["altitude"]) * u.m,
    )
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
    """Search Object ephemeris with astroquery

    Parameters
    ----------
    config : Configparser
        the configparser object with configuration option
    object_name : string
        the object name
    stepping : string
        steps between points

    Returns
    -------
    QTable:
        the ephemeris table

    """
    configuration.load_config(config)
    location = EarthLocation.from_geodetic(float(config['Observatory']['longitude'])*u.deg, float(
        config['Observatory']['latitude'])*u.deg, float(config['Observatory']['altitude'])*u.m)
    step: Union[Quantity, str]
    if stepping == 'm':
        step = 1 * u.minute
    elif stepping == 'h':
        step = '1h'
    elif stepping == 'd':
        step = '1d'
    elif stepping == 'w':
        step = '7d'
    else:
        # Default to 1 hour if unknown stepping value
        step = '1h'
    eph = MPC.get_ephemeris(str(object_name).upper(), location=location, step=step, number=30)
    ephemeris = eph[
        "Date", "RA", "Dec", "Elongation", "V", "Altitude", "Proper motion", "Direction"
    ]
    return ephemeris
