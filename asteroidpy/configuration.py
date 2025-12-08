from configparser import ConfigParser
import os
from typing import Dict, Tuple
from platform import system
import math
from platformdirs import user_config_dir, user_config_path
from astropy.coordinates import Angle
from astroquery.mpc import MPC


def save_config(config: ConfigParser) -> None:
    """Save configurations to the user's configuration file.

    The configuration is persisted to `$HOME/.asteroidpy` in INI format.
    This function writes the current state of the ConfigParser object to disk.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object containing configuration options to save.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The configuration file is created if it doesn't exist. Existing files
    are overwritten with the current configuration state.
    """
    # Persist configuration at $HOME/.asteroidpy
    home_dir = os.path.expanduser("~")
    config_path = os.path.join(home_dir, ".asteroidpy")
    with open(config_path, "w", encoding="utf-8") as f:
        config.write(f)


def initialize(config: ConfigParser) -> None:
    """Initialize configuration parameters with default values.

    Sets up default configuration sections and values for the application,
    including general settings (language) and observatory settings (location,
    coordinates, altitude, names, MPC code, and virtual horizon).

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object to initialize with default values.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    After initialization, the configuration is automatically saved to disk
    via `save_config()`. All numeric values are stored as strings, as required
    by ConfigParser.
    """
    config['General'] = {'lang': 'en'}
    # ConfigParser stores values as strings; ensure all values are strings
    config['Observatory'] = {
        'place': '',
        'latitude': '0.0',
        'longitude': '0.0',
        'altitude': '0.0',
        'obs_name': '',
        'observer_name': '',
        'mpc_code': 'XXX',
        "east_altitude": '0',
        "nord_altitude": '0',
        "south_altitude": '0',
        "west_altitude": '0',
    }
    print("inizializzato")
    save_config(config)


def load_config(config: ConfigParser) -> None:
    """Load configuration from file or initialize with defaults.

    Searches for the configuration file at `$HOME/.asteroidpy`. If the file
    exists and is readable, loads all parameters. Otherwise, initializes
    the configuration with default values.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object to load configuration into.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    If the configuration file is unreadable (permissions error) or invalid/empty,
    the function falls back to initializing with default values to ensure
    required sections exist.
    """
    # Read configuration from $HOME/.asteroidpy if it exists; otherwise initialize
    home_dir = os.path.expanduser("~")
    config_path = os.path.join(home_dir, ".asteroidpy")
    if os.path.exists(config_path):
        # Attempt to read. If unreadable (permissions) or invalid/empty,
        # fall back to initialize to ensure required sections exist.
        try:
            read_files = config.read(config_path, encoding="utf-8")
        except Exception:
            read_files = []

        if not read_files or not config.sections():
            initialize(config)
        return
    initialize(config)


def change_language(config: ConfigParser, lang: str) -> None:
    """Change the interface language setting.

    Updates the language preference in the configuration and saves it to disk.
    The language code should match one of the available locale directories.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    lang : str
        The language code to set (e.g., 'en', 'it', 'de', 'fr', 'es', 'pt').

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The change is persisted immediately to the configuration file.
    """
    load_config(config)
    config["General"]["lang"] = lang
    save_config(config)


def change_obs_coords(config: ConfigParser, place: str, lat: float, long: float) -> None:
    """Change observatory geographic coordinates.

    Updates the observatory location name and geographic coordinates (latitude
    and longitude) in the configuration and saves the changes to disk.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    place : str
        Name of the locality/place where the observatory is located.
    lat : float
        Latitude in decimal degrees (positive for North, negative for South).
    long : float
        Longitude in decimal degrees (positive for East, negative for West).

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    Coordinates are stored as strings in the configuration file, as required
    by ConfigParser. The change is persisted immediately.
    """
    load_config(config)
    config["Observatory"]["place"] = place
    config["Observatory"]["latitude"] = str(lat)
    config["Observatory"]["longitude"] = str(long)
    save_config(config)


def change_obs_altitude(config: ConfigParser, alt: int) -> None:
    """Change observatory altitude above sea level.

    Updates the observatory altitude in meters and saves the change to disk.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    alt : int
        Altitude in meters above sea level.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The altitude value is stored as a string in the configuration file.
    The change is persisted immediately.
    """
    load_config(config)
    config["Observatory"]["altitude"] = str(alt)
    save_config(config)


def change_mpc_code(config: ConfigParser, code: str) -> None:
    """Change the Minor Planet Center (MPC) observatory code.

    Updates the MPC observatory code in the configuration and saves the change
    to disk. The MPC code is used for official observations reporting.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    code : str
        The MPC observatory code (typically 3 characters, e.g., 'XXX' for unknown).

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The change is persisted immediately to the configuration file.
    """
    load_config(config)
    config["Observatory"]["mpc_code"] = str(code)
    save_config(config)


def get_observatory_coordinates(code: str) -> Tuple[float, float, float, str]:
    """Retrieve observatory coordinates from the Minor Planet Center database.

    Queries the MPC database for the observatory location associated with the
    given MPC code and returns the geographic coordinates and name.

    Parameters
    ----------
    code : str
        The MPC observatory code to look up.

    Returns
    -------
    tuple of (float, float, float, str)
        A tuple containing:
        - Longitude in decimal degrees
        - Latitude in decimal degrees
        - Altitude in meters
        - Observatory name as a string

    Raises
    ------
    Exception
        If the MPC code is invalid or the query fails.

    Notes
    -----
    The function uses astroquery.mpc.MPC to query the Minor Planet Center
    database. The coordinates are converted from the MPC's internal format
    to standard decimal degrees.
    """

def change_obs_name(config: ConfigParser, name: str) -> None:
    """Change the observatory name.

    Updates the observatory name in the configuration and saves the change
    to disk.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    name : str
        Name of the observatory.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The change is persisted immediately to the configuration file.
    """
    load_config(config)
    config["Observatory"]["obs_name"] = str(name)
    save_config(config)


def change_observer_name(config: ConfigParser, name: str) -> None:
    """Change the observer's name.

    Updates the observer's name in the configuration and saves the change
    to disk.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    name : str
        Name of the observer.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The change is persisted immediately to the configuration file.
    """
    load_config(config)
    config["Observatory"]["observer_name"] = str(name)
    save_config(config)


def print_obs_config(config: ConfigParser, show_sensitive: bool = False) -> None:
    """Print observatory configuration parameters to stdout.

    Displays the current observatory configuration including location, coordinates,
    altitude, observer name, observatory name, and MPC code. Sensitive location
    information can be optionally redacted.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    show_sensitive : bool, optional
        If True, prints sensitive observer location information (latitude,
        longitude, altitude). If False (default), these values are redacted
        as "***REDACTED***".

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The output is printed in Italian. Coordinates and altitude are considered
    sensitive information and are redacted by default for privacy.
    """
    load_config(config)
    if config.has_section("Observatory"):
        if config.has_option("Observatory", "place"):
            print("Località: %s" % config["Observatory"]["place"])
        if config.has_option("Observatory", "latitude"):
            print("Latitudine: %s" % (config["Observatory"]["latitude"] if show_sensitive else "***REDACTED***"))
        if config.has_option("Observatory", "longitude"):
            print("Longitudine: %s" % (config["Observatory"]["longitude"] if show_sensitive else "***REDACTED***"))
        if config.has_option("Observatory", "altitude"):
            print("Altitudine: %s" % (config["Observatory"]["altitude"] if show_sensitive else "***REDACTED***"))
        if config.has_option("Observatory", "observer_name"):
            print("Osservatore: %s" % config["Observatory"]["observer_name"])
        if config.has_option("Observatory", "obs_name"):
            print("Nome Osservatorio: %s" % config["Observatory"]["obs_name"])
        if config.has_option("Observatory", "mpc_code"):
            print("Codice MPC: %s" % config["Observatory"]["mpc_code"])


def virtual_horizon_configuration(config: ConfigParser, horizon: Dict[str, str]) -> None:
    """Change the virtual horizon configuration.

    Updates the minimum altitude thresholds for each cardinal direction (north,
    south, east, west) used to determine object visibility. These thresholds
    are used to simulate obstructions like buildings or mountains.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.
    horizon : dict of str
        Dictionary containing altitude thresholds for each cardinal direction.
        Expected keys: 'nord', 'south', 'east', 'west'. Values should be
        strings representing altitude in degrees.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The virtual horizon is used by the visibility checking functions to filter
    objects that would be below the configured altitude thresholds in each
    direction. The change is persisted immediately to the configuration file.
    """
    load_config(config)
    config["Observatory"]["nord_altitude"] = horizon["nord"]
    config["Observatory"]["south_altitude"] = horizon["south"]
    config["Observatory"]["east_altitude"] = horizon["east"]
    config["Observatory"]["west_altitude"] = horizon["west"]
    save_config(config)
