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

config = configparser.ConfigParser()


def save_config():
    f = open('config.ini', 'w')
    config.write(f)
    f.close()

def initialize():
    config['Observatory'] = {'latitude': 0.0,
                             'longitude': 0.0,
                             'altitude': 0.0}
    save_config()

def load_config():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.ini'):
                f=open(file, 'r')
                config.read(f)
                f.close() 
                break
            else:
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
    print('Latitudine: %s' % config['Observatory']['latitude'])
    print('Longitudine: %s' % config['Observatory']['longitude'])
    print('Altitudine: %s' % config['Observatory']['altitude'])
