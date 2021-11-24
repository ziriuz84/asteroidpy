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
import configparser
from pathlib import Path

config = configparser.ConfigParser()


def save_config():
    config.write('config.ini')

def initialize():
    config['OBSERVATORY']['latitude'] = 0.0
    config['OBSERVATORY']['longitude'] = 0.0
    config['OBSERVATORY']['altitude'] = 0.0
    save_config()

def load_config():
    try:
        config.read('config.ini')
    except:
        Path('config.ini').touch()
        initialize()


def change_obs_coords(lat, long):
    load_config()
    config['Observatory'] = {'latitude': lat,
                             'longitude': long}
    save_config()


def change_obs_altitude(alt):
    load_config()
    config['Observatory']['altitude'] = alt
    save_config()

def print_obs_config():
    load_config()
    print('Latitudine: %2.7f' % config['Observatory']['latitude'])
    print('Longitudine: %3.7f' % config['Observatory']['longitude'])
    print('Altitudine: %2.1f' % config['Observatory']['altitude'])
