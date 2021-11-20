import configparser
import os
import urwid

config = configparser.ConfigParser


def configuration():
    try:
        config.read('config.ini')
        config_interface()
    except:
        first_start()
