import requests
import json
import configuration
import datetime
from tabulate import tabulate
from bs4 import BeautifulSoup

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
        deltaT.append(time['timepoint'])
        cloudcover.append(cloudcover_dict[time['cloudcover']])
        seeing.append(seeing_dict[time['seeing']])
        transparency.append(transparency_dict[time['transparency']])
        lifted_index.append(liftedIndex_dict[time['lifted_index']])
        temperature.append(str(time['temp2m'])+' C')
        rh.append(rh2m_dict[time['rh2m']])
        wind10m.append(time['wind10m']['direction'] +
                       ' ' + wind10m_speed_dict[time['wind10m']['speed']])
        prec_type.append(time['prec_type'])
    data = {'DeltaT': deltaT, 'Nuvolo': cloudcover, 'Seeing': seeing, 'Trasp': transparency,
            'Instab': lifted_index, 'Temp': temperature, 'RH': rh, 'Vento': wind10m, 'Precip': prec_type}
    print(tabulate(data, headers='keys', tablefmt='fancy_grid'))
    exit = input('Premi invio per continuare...')


def observing_target_list(config):
    """
    Prints Observing target list from MPC

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    authenticity_token = "W5eBzzw9Clj4tJVzkz0z%2F2EK18jvSS%2BffHxZpAshylg%3D"
    configuration.load_config(config)
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    select_time = input(
        'Vuoi sapere gli asteroidi visibili in questo momento? ')
    if (select_time == 's' or select_time == 'y'):
        time = datetime.datetime.utcnow()
    else:
        print('Forniscimi i parametri temporali di inizio osservazione (UTC)')
        day = input('Giorno -> ')
        month = input('Mese -> ')
        year = input('Anno -> ')
        hour = input('Ora -> ')
        minutes = input('Minuti -> ')
        seconds = input('Secondi -> ')
        time = datetime.datetime(year, month, day, hour, minutes, seconds)
    duration = input("Durata dell'osservazione -> ")
    sun_elongation = input("Minima elongazione solare -> ")
    moon_elongation = input("Minima elongazione lunare -> ")
    minimal_height = input("Altezza minima -> ")
    max_number = input("Numero massimo di oggetti -> ")
    object_request = input(
        'Seleziona il tipo di oggetto\n1 - Asteroide\n2 - NEA\n3 - Cometa\nScelta -> ')
    if (object_request == '2'):
        object_type = 'neo'
    elif (object_request == '3'):
        object_type = 'cmt'
    else:
        object_type = 'mp'
    payload = {
        'utf8': '%E2%9C%93',
        'authenticity_token': authenticity_token,
        'latitude': lat,
        'longitude': long,
        'year': time.year,
        'month': time.month,
        'day': time.day,
        'hour': time.hour,
        'minute': time.minute,
        'duration': duration,
        'max_objects': max_number,
        'min_alt': minimal_height,
        'solar_elong': sun_elongation,
        'lunar_elong': moon_elongation,
        'object_type': object_type,
        'submit': 'Submit'
    }
    r = requests.post(
        'https://www.minorplanetcenter.net/whatsup/index', params=payload)
    soup = BeautifulSoup(r.content, 'lxml')
    tables = soup.find_all('table')
    i=0
    for table in tables:
        print('tabella'+str(i)+': ')
        print(table)
        i+=1

