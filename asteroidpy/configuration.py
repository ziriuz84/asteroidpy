##
# @file configuration.py
#
# @brief The main configuration module
#
# @section description_configuration Description
# Simply tha main configuration management module
#
# @section libraries_configuration Libraries/Modules
# - ConfigParser
#
# @section todo_interface TODO
#
# @section author_interface Author(s)
# - Created by Sirio Negri on 11/23/2021
# - modified by Sirio Negri on 11/23/2021
import os
import configparser
from pathlib import Path


def save_config(config):
    f = open('config.ini', 'w')
    config.write(f)
    f.close()


def initialize(config):
    config['Observatory'] = {'latitude': 0.0,
                             'longitude': 0.0,
                             'altitude': 0.0,
                             'obs_name': '',
                             'observer_name': '',
                             'mpc_code': 'XXX'}
    print('inizializzato')
    save_config(config)


def load_config(config):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for root, dirs, files in os.walk(dir_path):
        print(root)
        print(dirs)
        print(files)
        if 'config.ini' in files:
            config.read('config.ini')
            break
        else:
            initialize(config)


def change_obs_coords(config, lat, long):
    load_config(config)
    config['Observatory']['latitude'] = str(lat)
    config['Observatory']['longitude'] = str(long)
    save_config(config)


def change_obs_altitude(config, alt):
    load_config(config)
    config['Observatory']['altitude'] = str(alt)
    save_config(config)


def change_mpc_code(config, code):
    load_config(config)
    config['Observatory']['mpc_code'] = str(code)
    save_config(config)


def change_obs_name(config, name):
    load_config(config)
    config['Observatory']['obs_name'] = str(name)
    save_config(config)


def change_observer_name(config, name):
    load_config(config)
    config['Observatory']['observer_name'] = str(name)
    save_config(config)


def print_obs_config(config):
    load_config(config)
    print('Latitudine: %s' % config['Observatory']['latitude'])
    print('Longitudine: %s' % config['Observatory']['longitude'])
    print('Altitudine: %s' % config['Observatory']['altitude'])
