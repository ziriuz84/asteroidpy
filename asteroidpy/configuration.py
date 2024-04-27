import os
import math
from platformdirs import user_config_dir
from astropy.coordinates import Angle
from astroquery.mpc import MPC


def save_config(config):
    """Save configurations in config.ini file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    dir_path = user_config_dir("AsteroidPy")
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(dir_path + "/asteroidpy.ini", "w") as f:
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
    config["General"] = {"lang": "en"}
    config["Observatory"] = {
        "place": "",
        "latitude": 0.0,
        "longitude": 0.0,
        "altitude": 0.0,
        "obs_name": "",
        "observer_name": "",
        "mpc_code": "XXX",
    }
    print("inizializzato")
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
    dir_path = user_config_dir("AsteroidPy")
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    print(user_config_dir("AsteroidPy"))
    i = 0
    for root, dirs, files in os.walk(user_config_dir("AsteroidPy")):
        if "asteroidpy.ini" in files:
            config.read(user_config_dir("AsteroidPy") + "/asteroidpy.ini")
            break
        else:
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
    config["General"]["lang"] = lang
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
    config["Observatory"]["place"] = place
    config["Observatory"]["latitude"] = str(lat)
    config["Observatory"]["longitude"] = str(long)
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
    config["Observatory"]["altitude"] = str(alt)
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
    config["Observatory"]["mpc_code"] = str(code)
    save_config(config)


def get_observatory_coordinates(code):
    observatory_location = MPC.get_observatory_location(str(code))
    latitude = math.acos(
        observatory_location[1]
        / math.sqrt(observatory_location[1] ** 2 + observatory_location[2] ** 2)
    )
    altitude = math.sqrt(observatory_location[1] ** 2 + observatory_location[2] ** 2)
    return (
        observatory_location[0].degree,
        math.degrees(latitude),
        altitude,
        observatory_location[3],
    )


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
    config["Observatory"]["obs_name"] = str(name)
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
    config["Observatory"]["observer_name"] = str(name)
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
    if config.has_section("Observatory"):
        if config.has_option("Observatory", "place"):
            print("Località: %s" % config["Observatory"]["place"])
        if config.has_option("Observatory", "latitude"):
            print("Latitudine: %s" % config["Observatory"]["latitude"])
        if config.has_option("Observatory", "longitude"):
            print("Longitudine: %s" % config["Observatory"]["longitude"])
        if config.has_option("Observatory", "altitude"):
            print("Altitudine: %s" % config["Observatory"]["altitude"])
        if config.has_option("Observatory", "observer_name"):
            print("Osservatore: %s" % config["Observatory"]["observer_name"])
        if config.has_option("Observatory", "obs_name"):
            print("Nome Osservatorio: %s" % config["Observatory"]["obs_name"])
        if config.has_option("Observatory", "mpc_code"):
            print("Codice MPC: %s" % config["Observatory"]["mpc_code"])


def virtual_horizon_configuration(config, horizon):
    """Change the Virtual horizon configuration

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration options
    horizon : dictionary of string
        Altitudes for cardinal directions

    Returns
    -------

    """
    load_config(config)
    config["Observatory"]["nord_altitude"] = horizon["nord"]
    config["Observatory"]["south_altitude"] = horizon["south"]
    config["Observatory"]["east_altitude"] = horizon["east"]
    config["Observatory"]["west_altitude"] = horizon["west"]
    save_config(config)
