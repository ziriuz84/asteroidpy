import requests
import asyncio
import httpx
import gettext
from asteroidpy import configuration
import datetime
from tabulate import tabulate
from bs4 import BeautifulSoup
from astropy import units as u
from astropy.coordinates import (SkyCoord, EarthLocation, AltAz)
from astropy.table import QTable
from astropy.time import Time
from astroplan import Observer

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


async def httpx_get(url, payload, return_type):
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=payload)
    if (return_type == 'json'):
        return [r.json(), r.status_code]
    else:
        return [r.text, r.status_code]


async def httpx_post(url, payload, return_type):
    async with httpx.AsyncClient() as client:
        r = await client.post(url, data=payload)
    if (return_type == 'json'):
        return [r.json(), r.status_code]
    else:
        return [r.text, r.status_code]


def decimal_part(number):
    return number-round(number)


def deg_to_hms_coordinates(coordinates):
    coordinates_m = decimal_part(coordinates) * 60
    coordinates_s = decimal_part(coordinates_m) * 60
    return str(round(coordinates))+unity+" " + str(round(coordinates_m))+"m "+str(coordinates_s)+"s"


def weather(config):
    """
    Prints Weather forecast up to 72 hours

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    configuration.load_config(config)
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    payload = {'lon': long, 'lat': lat, 'product': 'astro', 'output': 'json'}
    r = requests.get('http://www.7timer.info/bin/api.pl', params=payload)
    weather_forecast = r.json()
    # print('{:<7} {:<9} {:<11} {:<9} {:<10} {:<9} {:<5} {:<7} {:<6}'.format(
    # 'DeltaT', 'Nuvolo', 'Seeing', 'Trasp', 'Instab', 'Temp', 'RH', 'Vento', 'Precip'))
    data = []
    time_init = weather_forecast['init']
    time_start = datetime.datetime(int(time_init[0:4]),  int(
        time_init[4:6]), int(time_init[6:8]), int(time_init[8:10]))
    deltaT = []
    cloudcover = []
    seeing = []
    transparency = []
    lifted_index = []
    temperature = []
    rh = []
    wind10m = []
    prec_type = []
    for time in weather_forecast['dataseries']:
        temp = time_start+datetime.timedelta(hours=time['timepoint'])
        deltaT.append(temp.strftime("%d/%m %H:%M"))
        cloudcover.append(cloudcover_dict[time['cloudcover']])
        seeing.append(seeing_dict[time['seeing']])
        transparency.append(transparency_dict[time['transparency']])
        lifted_index.append(liftedIndex_dict[time['lifted_index']])
        temperature.append(str(time['temp2m'])+' C')
        rh.append(rh2m_dict[time['rh2m']])
        wind10m.append(time['wind10m']['direction'] +
                       ' ' + wind10m_speed_dict[time['wind10m']['speed']])
        prec_type.append(time['prec_type'])
    data = {'Time': deltaT, 'Nuvolo': cloudcover, 'Seeing': seeing, 'Trasp': transparency,
            'Instab': lifted_index, 'Temp': temperature, 'RH': rh, 'Vento': wind10m, 'Precip': prec_type}
    print(tabulate(data, headers='keys', tablefmt='fancy_grid'))
    exit = input(_('Press enter to continue...'))
    print(exit)


def skycoord_format(coord, coordid):
    """
    Formats coordinates as described in coordid

    :param coord: the coordinates to be formatted
    :type coord: string
    :param coordid: the format
    :type coordid: string
    """
    temp = coord.split()
    if (coordid == 'ra'):
        return temp[0]+'h'+temp[1]+'m'+temp[2]+'s'
    elif (coordid == 'dec'):
        return temp[0]+'d'+temp[1]+'m'+temp[2]+'s'


def observing_target_list(config, payload):
    """
    Prints Observing target list from MPC

    :param config: the Configparser object with configuration option
    :type config: Configparser
    :param payload: the payload of parameters
    :type payload: dictionary of strings
    """
    r = requests.post(
        'https://www.minorplanetcenter.net/whatsup/index', params=payload)
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
    result = []
    for d in data:
        temp = []
        for i in range(len(headers)):
            if 'Begin Time' in headers[i]:
                temp.append(d[i].replace('Z', ''))
            if ('Beg RA' in headers[i]):
                temp.append(skycoord_format(d[i], 'ra'))
            if ('Beg Dec' in headers[i]):
                temp.append(skycoord_format(d[i], 'dec'))
            if ('Designation' in headers[i]):
                temp.append(d[i])
            if ('Mag' in headers[i]):
                temp.append(d[i])
            if ('Beg Alt' in headers[i]):
                temp.append(d[i])
        result.append(temp)
    headers = ['Designation', 'Mag', 'Time', 'RA', 'Dec', 'Alt']
    return [headers, result]


def neocp_search(config, min_score, max_magnitude, min_altitude):
    """
    Prints NEOcp visible at the moment

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    configuration.load_config(config)
    # r=requests.get('https://www.minorplanetcenter.net/Extended_Files/neocp.json')
    # data=r.json()
    response = asyncio.run(httpx_get(
        'https://www.minorplanetcenter.net/Extended_Files/neocp.json', {}, 'json'))
    data = response[0]
    result = []
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    location = EarthLocation.from_geodetic(lon=float(long), lat=float(lat))
    observing_date = Time(datetime.datetime.utcnow())
    altaz = AltAz(location=location, obstime=observing_date)
    table = QTable([[""],[0],[0.0],[0.0],[0.0],[0.0],[0],[0.0],[0.0]],
                   names=('Temp_Desig', 'Score', 'R.A.', 'Decl', 'Alt', 'V', 'NObs', 'Arc', 'Not_seen'),
                   meta={'name': 'NEOcp confirmation'})
    for item in data:
        coord = SkyCoord(float(item['R.A.'])*u.deg, float(item['Decl.'])*u.deg)
        coord_altaz = coord.transform_to(altaz)
        if (int(item['Score'] > min_score and coord_altaz.alt > min_altitude * u.deg and float(item['V'] < max_magnitude))):
            table.add_row([item['Temp_Desig'],
                          int(item['Score']),
                          coord.ra,
                          coord.dec,
                          coord_altaz.alt,
                          float(item['V']),
                          int(item['NObs']),
                          float(item['Arc']),
                          float(item['Not_Seen_dys'])])
    table.remove_row(0)
    return table


def twilight_times(config):
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


def sun_moon_ephemeris(config):
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
