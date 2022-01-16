import requests
import gettext
import configuration
import datetime
from tabulate import tabulate
from bs4 import BeautifulSoup

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
        temp=time_start+datetime.timedelta(hours=time['timepoint'])
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
        temp = {}
        for i in range(len(headers)):
            if 'Time' in headers[i]:
                temp[headers[i]] = datetime.datetime.fromisoformat(
                    d[i].replace('Z', ''))
            else:
                temp[headers[i]] = d[i]
            if (i in [0, 1, 5, 6, 7]):
                print('%s: %s ' % (headers[i], d[i]))
        print('\n')
        result.append(temp)
    # print(result)
