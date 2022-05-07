import os


def save_config(config):
    """Save configurations in config.ini file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    with open(os.path.expanduser('~')+'/'+'.asteroidpy', 'w') as f:
        config.write(f)


def initialize(config):
    """Initialize Configuration parameters

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    config['General'] = {'lang': 'en'}
    config['Observatory'] = {'place': '',
                             'latitude': 0.0,
                             'longitude': 0.0,
                             'altitude': 0.0,
                             'obs_name': '',
                             'observer_name': '',
                             'mpc_code': 'XXX'}
    print('inizializzato')
    save_config(config)


def load_config(config):
    """Searchs for .asteroidpy. If it's in the folder then it loads all parameter, else it initialize it

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    dir_path = os.path.dirname(os.path.expanduser('~'))
    i = 0
    for root, dirs, files in os.walk(dir_path):
        if '.asteroidpy' in files:
            config.read(os.path.expanduser('~')+'/'+'.asteroidpy')
            break
        elif (i != 0 and i != 1):
            initialize(config)
        i += 1


def change_language(config, lang):
    """Changes language for interface

    Parameters
    ----------
    config : configparser
        the configparser object with configuration options
    lang : string
        the language chosen

    Returns
    -------

    """
    load_config(config)
    config['General']['lang'] = lang
    save_config(config)


def change_obs_coords(config, place, lat, long):
    """Changes Observatory coordinates

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option
    place : string
        Name of Locality
    lat : float
        latitude
    long : float
        longitude

    Returns
    -------

    """
    load_config(config)
    config['Observatory']['place'] = place
    config['Observatory']['latitude'] = str(lat)
    config['Observatory']['longitude'] = str(long)
    save_config(config)


def change_obs_altitude(config, alt):
    """Changes Observatory altitude

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option
    alt : int
        altitude

    Returns
    -------

    """
    load_config(config)
    config['Observatory']['altitude'] = str(alt)
    save_config(config)


def change_mpc_code(config, code):
    """Changes MPC code

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option
    code : string
        MPC Code

    Returns
    -------

    """
    load_config(config)
    config['Observatory']['mpc_code'] = str(code)
    save_config(config)


def change_obs_name(config, name):
    """Changes Observatory name

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option
    name : string
        Name of obseratory

    Returns
    -------

    """
    load_config(config)
    config['Observatory']['obs_name'] = str(name)
    save_config(config)


def change_observer_name(config, name):
    """Changes observer name

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option
    name : string
        Name of observer

    Returns
    -------

    """
    load_config(config)
    config['Observatory']['observer_name'] = str(name)
    save_config(config)


def print_obs_config(config):
    """Prints Observatory configuration parameters

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    load_config(config)
    print('Località: %s' % config['Observatory']['place'])
    print('Latitudine: %s' % config['Observatory']['latitude'])
    print('Longitudine: %s' % config['Observatory']['longitude'])
    print('Altitudine: %s' % config['Observatory']['altitude'])
    print('Osservatore: %s' % config['Observatory']['observer_name'])
    print('Nome Osservatorio: %s' % config['Observatory']['obs_name'])
    print('Codice MPC: %s' % config['Observatory']['mpc_code'])
