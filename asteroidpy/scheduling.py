from configparser import ConfigParser
from typing import Dict, Tuple, List, Any, Union, Optional, cast
import requests
import asyncio
import httpx
import gettext
from asteroidpy import configuration
import datetime
from bs4 import BeautifulSoup
from astropy import units as u
from astropy.coordinates import (SkyCoord, EarthLocation, AltAz)
from astropy.table import QTable
from astropy.time import Time
from astroplan import Observer
from astroquery.mpc import MPC
from astropy.units import Quantity

_ = gettext.gettext

cloudcover_dict = {1: '0%-6%', 2: '6%-19%', 3: '19%-31%', 4: '31%-44%',
                   5: '44%-56%', 6: '56%-69%', 7: '69%-81%', 8: '81%-94%', 9: '94%-100%'}
seeing_dict = {1: '<0.5"', 2: '0.5"-0.75"', 3: '0.75"-1"', 4: '1"-1.25"',
               5: '1.25"-1.5"', 6: '1.5"-2"', 7: '2"-2.5"', 8: '>2.5"'}
transparency_dict = {1: '<0.3', 2: '0.3-0.4', 3: '0.4-0.5',
                     4: '0.5-0.6', 5: '0.6-0.7', 6: '0.7-0.85', 7: '0.85-1', 8: '>1', }
liftedIndex_dict = {-10: 'Below -7', -6: '-7 - -5', -4: '-5 - -3',
                    -1: '-3 - 0', 2: '0 - 4', 6: '4 - 8', 10: '8 - 11', 15: 'Over 11'}
rh2m_dict = {-4: '0%-5%', -3: '5%-10%', -2: '10%-15%', -1: '15%-20%', 0: '20%-25%', 1: '25%-30%', 2: '30%-35%', 3: '35%-40%', 4: '40%-45%', 5: '45%-50%',
             6: '50%-55%', 7: '55%-60%', 8: '60%-65%', 9: '65%-70%', 10: '70%-75%', 11: '75%-80%', 12: '80%-85%', 13: '85%-90%', 14: '90%-95%', 15: '95%-99%', 16: '100%'}
wind10m_speed_dict = {1: 'Below 0.3 m/s', 2: '0.3-3.4m/s', 3: '3.4-8.0m/s', 4: '8.0-10.8m/s',
                      5: '10.8-17.2m/s', 6: '17.2-24.5m/s', 7: '24.5-32.6m/s', 8: 'Over 32.6m/s'}


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
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=payload)
    if (return_type == 'json'):
        return cast(Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], (r.json(), r.status_code))
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
    async with httpx.AsyncClient() as client:
        r = await client.post(url, data=payload)
    if (return_type == 'json'):
        return cast(Tuple[Union[Dict[str, Any], List[Dict[str, Any]]], int], (r.json(), r.status_code))
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
    time_start = datetime.datetime(int(time_init[0:4]),  int(
        time_init[4:6]), int(time_init[6:8]), int(time_init[8:10]))
    time = time_start + datetime.timedelta(hours=deltaT)
    return time.strftime('%d/%m %H:%M')


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
    lat, long = config['Observatory']['latitude'], config['Observatory']['longitude']
    payload = {'lon': long, 'lat': lat, 'product': 'astro', 'output': 'json'}
    r = requests.get('http://www.7timer.info/bin/api.pl', params=payload)
    weather_forecast = r.json()
    table = QTable([[""], [""], [""], [""], [""], [""], [""], [""], [""]],
                   names=('Time', 'Clouds', 'Seeing', 'Transp',
                          'Instab', 'Temp', 'RH', 'Wind', 'Precip'),
                   meta={'name': 'Weather forecast'})
    for time in weather_forecast['dataseries']:
        table.add_row([weather_time(weather_forecast['init'], time['timepoint']),
                       cloudcover_dict[time['cloudcover']],
                       seeing_dict[time['seeing']],
                       transparency_dict[time['transparency']],
                       liftedIndex_dict[time['lifted_index']],
                       str(time['temp2m'])+' C',
                       rh2m_dict[time['rh2m']],
                       time['wind10m']['direction'] +
                       ' ' + wind10m_speed_dict[time['wind10m']['speed']],
                       time['prec_type']])
    table.remove_row(0)
    print(table)
    print('\n\n\n\n')


def skycoord_format(coord: str, coordid: str) -> str:
    """Formats coordinates as described in coordid

    Parameters
    ----------
    coord : string
        the coordinates to be formatted
    coordid : string
        the format

    Returns
    -------

    """
    temp = coord.split()
    if (coordid == 'ra'):
        return temp[0]+'h'+temp[1]+'m'+temp[2]+'s'
    elif (coordid == 'dec'):
        return temp[0]+'d'+temp[1]+'m'+temp[2]+'s'
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
    location = EarthLocation.from_geodetic(lat=float(config['Observatory']['latitude'])*u.deg, lon=float(
        config['Observatory']['longitude'])*u.deg, height=float(config['Observatory']['altitude'])*u.m)
    if isinstance(coord, list):
        coord = SkyCoord(skycoord_format(
            coord[0], "ra") + " " + skycoord_format(coord[1], "dec"))
    coord = coord.transform_to(AltAz(obstime=time, location=location))
    configuration.load_config(config)
    result = False
    if (coord.az > 315*u.deg and coord.az < 45*u.deg and coord.alt > float(config['Observatory']['nord_altitude'])*u.deg):
        result = True
    elif (coord.az > 45*u.deg and coord.az < 135*u.deg and coord.alt > float(config['Observatory']['east_altitude'])*u.deg):
        result = True
    elif (coord.az > 135*u.deg and coord.az < 225*u.deg and coord.alt > float(config['Observatory']['south_altitude'])*u.deg):
        result = True
    elif (coord.az > 225*u.deg and coord.az < 315*u.deg and coord.alt > float(config['Observatory']['west_altitude'])*u.deg):
        result = True
    return result


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
    r = requests.post(
        url, params=payload)
    soup = BeautifulSoup(r.content, 'lxml')
    tables = soup.find_all('table')
    table = tables[3]
    headerstag = table.find_all('th')
    headers = []
    for header in headerstag:
        headers.append(header.string.strip())
    rowstag = table.find_all('tr')
    datatag = []
    for row in rowstag:
        datatag.append(row.find_all('td'))
    data = []
    for d in datatag:
        temp = []
        for i in d:
            temp.append(i.string.strip())
        data.append(temp)
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
    results = QTable([[""], [""], [""], [""], [""], [""]],
                     names=('Designation', 'Mag', 'Time', 'RA', 'Dec', 'Alt'),
                     meta={'name': 'Observing Target List'})
    data = observing_target_list_scraper(
        'https://www.minorplanetcenter.net/whatsup/index', payload)
    for d in data:
        if (is_visible(config, [d[5], d[6]], Time(d[4].replace('T', ' ').replace('z', '')))):
            results.add_row([d[0], d[1], d[4].replace('z', ''), skycoord_format(
                d[5], 'ra'), skycoord_format(d[6], 'dec'), d[7]])
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
    location = EarthLocation.from_geodetic(lon=float(long), lat=float(lat))
    observing_date = Time(datetime.datetime.utcnow())
    altaz = AltAz(location=location, obstime=observing_date)
    # table already created above
    for item in data:
        coord = SkyCoord(float(item['R.A.'])*u.deg, float(item['Decl.'])*u.deg)
        coord_altaz = coord.transform_to(altaz)
        try:
            score = int(item['Score'])
            mag = float(item['V'])
        except Exception:
            continue
        if score > min_score and mag < max_magnitude and is_visible(config, coord, observing_date):
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
    location = EarthLocation.from_geodetic(float(config['Observatory']['longitude'])*u.deg, float(
        config['Observatory']['latitude'])*u.deg, float(config['Observatory']['altitude'])*u.m)
    observer = Observer(name=config['Observatory']
                        ['obs_name'], location=location)
    observing_date = Time(datetime.datetime.utcnow())
    result = {'AstroM': observer.twilight_morning_astronomical(observing_date, which='next'),
              'AstroE': observer.twilight_evening_astronomical(observing_date, which='next'),
              'CivilM': observer.twilight_morning_civil(observing_date, which='next'),
              'CivilE': observer.twilight_evening_civil(observing_date, which='next'),
              'NautiM': observer.twilight_morning_nautical(observing_date, which='next'),
              'NautiE': observer.twilight_evening_nautical(observing_date, which='next')}
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
    location = EarthLocation.from_geodetic(float(config['Observatory']['longitude'])*u.deg, float(
        config['Observatory']['latitude'])*u.deg, float(config['Observatory']['altitude'])*u.m)
    observer = Observer(name=config['Observatory']
                        ['obs_name'], location=location)
    observing_date = Time(datetime.datetime.utcnow())
    result = {'Sunrise': observer.sun_rise_time(observing_date, which='next'),
              'Sunset': observer.sun_set_time(observing_date, which='next'),
              'Moonrise': observer.moon_rise_time(observing_date, which='next'),
              'Moonset': observer.moon_set_time(observing_date, which='next'),
              'MoonIll': observer.moon_illumination(observing_date)
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
    ephemeris = eph['Date', 'RA', 'Dec', 'Elongation',
                    'V', 'Altitude', 'Proper motion', 'Direction']
    return ephemeris
