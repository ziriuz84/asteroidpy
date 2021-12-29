import os
import configparser
from pathlib import Path


def save_config(config):
    """
    Save configurations in config.ini file

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    f = open('config.ini', 'w')
    config.write(f)
    f.close()


def initialize(config):
    """
    Initialize Configuration parameters

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
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
    """
    Searchs for config.ini. If it's in the folder then it loads all parameter, else it initialize it

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for root, dirs, files in os.walk(dir_path):
        if 'config.ini' in files:
            config.read('config.ini')
            break
        else:
            initialize(config)


def change_obs_coords(config, place, lat, long):
    """
    Changes Observatory coordinates

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    load_config(config)
    config['Observatory']['place'] = place
    config['Observatory']['latitude'] = str(lat)
    config['Observatory']['longitude'] = str(long)
    save_config(config)


def change_obs_altitude(config, alt):
    """
    Changes Observatory altitude

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    load_config(config)
    config['Observatory']['altitude'] = str(alt)
    save_config(config)


def change_mpc_code(config, code):
    """
    Changes MPC code

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    load_config(config)
    config['Observatory']['mpc_code'] = str(code)
    save_config(config)


def change_obs_name(config, name):
    """
    Changes Observatory name

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    load_config(config)
    config['Observatory']['obs_name'] = str(name)
    save_config(config)


def change_observer_name(config, name):
    """
    Changes observer name

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    load_config(config)
    config['Observatory']['observer_name'] = str(name)
    save_config(config)


def print_obs_config(config):
    """
    Prints Observatory configuration parameters

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    load_config(config)
    print('Località: %s' % config['Observatory']['place'])
    print('Latitudine: %s' % config['Observatory']['latitude'])
    print('Longitudine: %s' % config['Observatory']['longitude'])
    print('Altitudine: %s' % config['Observatory']['altitude'])
    print('Osservatore: %s' % config['Observatory']['observer_name'])
    print('Nome Osservatorio: %s' % config['Observatory']['obs_name'])
    print('Codice MPC: %s' % config['Observatory']['mpc_code'])
