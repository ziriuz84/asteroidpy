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

config = configparser.ConfigParser()


def save_config():
    config.write('config.ini')


def load_config():
    config.read('config.ini')


def change_obs_coords(lat, long):
    load_config()
    config['Observatory'] = {'latitude': lat,
                             'longitude': long}
    save_config()


def change_obs_altitude(alt):
    load_config()
    config['Observatory']['altitude'] = alt
    save_config()
