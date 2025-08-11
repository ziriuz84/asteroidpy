import datetime
import gettext
from configparser import ConfigParser
import asteroidpy.configuration as configuration
import asteroidpy.scheduling as scheduling
from typing import List, Dict, Union, Any, Tuple

_ = gettext.gettext


def get_integer(message: str) -> int:
    """

    Parameters
    ----------
    message :
        the input given

    Returns
    -------

    """
    while True:
        try:
            userInt = int(input(message))
            return userInt
        except ValueError:
            print('You must enter an integer')


def get_float(message: str) -> float:
    """

    Parameters
    ----------
    message :
        the input given

    Returns
    -------

    """
    while True:
        try:
            userFloat = float(input(message))
            return userFloat
        except ValueError:
            print('You must enter a number')


def local_coords(config: ConfigParser) -> List[str]:
    """Returns local geographical coordinates

    Parameters
    ----------
    config :
        

    Returns
    -------

    """
    configuration.load_config(config)
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    return [lat, long]


def select_specific_time() -> datetime.datetime:
    """Returns specific time"""
    print(_('Provide me with the observation start time parameters (UTC)'))
    day = get_integer(_('Day -> '))
    month = get_integer(_('Month -> '))
    year = get_integer(_('Year -> '))
    hour = get_integer(_('Hour -> '))
    minutes = get_integer(_('Minutes -> '))
    seconds = get_integer(_('Seconds -> '))
    time = datetime.datetime(
        year, month, day, hour, minutes, seconds)
    return time


def WIP() -> None:
    """Prints a simply Work in Progress"""
    print(_('Work in Progress'))
    print('\n\n\n\n\n\n\n\n')


def change_obs_coords_menu(config: ConfigParser) -> None:
    """Changes Observatory coordinates in Configuration file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    place = input(_('Locality -> '))
    latitude = get_float(_('Latitude -> '))
    longitude = get_float(_('Longitude -> '))
    configuration.change_obs_coords(config, place, latitude, longitude)


def change_obs_altitude_menu(config: ConfigParser) -> None:
    """Changes Observatory altitude in Configuration file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    altitude = get_integer(_('Altitude -> '))
    configuration.change_obs_altitude(config, altitude)


def change_observer_name_menu(config: ConfigParser) -> None:
    """Changes Observer name in Configuration file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    name = input(_('Observer name -> '))
    configuration.change_observer_name(config, name)


def change_obs_name_menu(config: ConfigParser) -> None:
    """Changes Observatory name in Configuration file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    name = input(_('Observatory name -> '))
    configuration.change_obs_name(config, name)


def change_mpc_code_menu(config: ConfigParser) -> None:
    """Changes MPC code in Configuration file

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    code = input(_('MPC Code -> '))
    configuration.change_mpc_code(config, code)


def print_observatory_config_menu() -> None:
    """Prints Observatory config text menu"""
    print(_('''Choose an option
    1 - Change coordinates
    2 - Change altitude
    3 - Change the name of the observer
    4 - Change the name of the observatory
    5 - Change the MPC code
    6 - Change Virtual Horizon
    0 - Back to configuration menu'''))


def observatory_config_menu(config: ConfigParser) -> None:
    """Prints Observatory config menu and it launches correct interface

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    choice = 99
    while (choice != 0):
        print(_('Configuration -> Observatory'))
        print('==============================\n')
        configuration.print_obs_config(config)
        print_observatory_config_menu()
        choice = get_integer(_('choice -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            change_obs_coords_menu(config)
        if choice == 2:
            change_obs_altitude_menu(config)
        if choice == 3:
            change_observer_name_menu(config)
        if choice == 4:
            change_obs_name_menu(config)
        if choice == 5:
            change_mpc_code_menu(config)
        if choice == 6:
            change_horizon(config)


def change_language(config: ConfigParser) -> None:
    """Prints language configuration menu

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    lang = ''
    print(_('Select a language'))
    print('1 - English')
    lang_chosen = get_integer(_('Language -> '))
    if lang_chosen == 1:
        lang = 'en'
    configuration.change_language(config, lang)


def general_config_menu(config: ConfigParser) -> None:
    """Prints menu for general configuration options and it launches correct interface

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    choice = 99
    while (choice != 0):
        print(_('Configuration -> General'))
        print('==============================')
        print('\n')
        print(_('Choose a submenu'))
        print(_('1 - Language'))
        print(_('0 - Back to configuration menu'))
        choice = get_integer(_('choice -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            change_language(config)


def config_menu(config: ConfigParser) -> None:
    """Prints main config menu and it launches correct interface

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    choice = 99
    while (choice != 0):
        print(_('Configuration'))
        print('==============================')
        print('\n')
        print(_('Choose a submenu'))
        print(_('1 - General'))
        print(_('2 - Observatory'))
        print(_('0 - Back to main menu'))
        choice = eval(input(_('choice -> ')))
        print('\n\n\n\n\n')
        if choice == 1:
            general_config_menu(config)
        if choice == 2:
            observatory_config_menu(config)


def observing_target_list_menu(config: ConfigParser) -> None:
    """Prints observing target list

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    authenticity_token = "W5eBzzw9Clj4tJVzkz0z%2F2EK18jvSS%2BffHxZpAshylg%3D"
    coordinates = local_coords(config)
    select_time = input(_(
        'Do you want to know the asteroids visible right now? [y/N]'))
    if (select_time == 's' or select_time == 'y'):
        time = datetime.datetime.utcnow()
    else:
        time = select_specific_time()
    duration = get_integer(_("Duration of observation -> "))
    solar_elongation = get_integer(_("Minimal solar elongation -> "))
    lunar_elongation = get_integer(_("Minimal lunar elongation -> "))
    minimal_height = get_integer(_("Minimal altitude-> "))
    max_objects = get_integer(_("Maximum number of objects -> "))
    object_request = get_integer(_(
        'Select type of object\n1 - Asteroids\n2 - NEAs\n3 - Comets\nChoice -> '))
    if (object_request == 2):
        object_type = 'neo'
    elif (object_request == 3):
        object_type = 'cmt'
    else:
        object_type = 'mp'
    payload = {
        'utf8': '%E2%9C%93',
        'authenticity_token': authenticity_token,
        'latitude': coordinates[0],
        'longitude': coordinates[1],
        'year': time.year,
        'month': time.month,
        'day': time.day,
        'hour': time.hour,
        'minute': time.minute,
        'duration': duration,
        'max_objects': max_objects,
        'min_alt': minimal_height,
        'solar_elong': solar_elongation,
        'lunar_elong': lunar_elongation,
        'object_type': object_type,
        'submit': 'Submit'
    }
    target_list = scheduling.observing_target_list(config, payload)
    browser_view = input(_("Do you want to view in Browser? (y/N) -> "))
    if (browser_view in ["y", "Y"]):
        target_list.show_in_browser(jsviewer=True)
    else:
        print(target_list)
    print('\n\n\n\n')


def neocp_confirmation_menu(config: ConfigParser) -> None:
    """Prints NEOcp confirmation list

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    min_score = get_integer(_('Minimum score -> '))
    max_magnitude = get_float(_('Maximum magnitude -> '))
    min_altitude = get_integer(_('Minimum altitude -> '))
    browser_view = input(_("Do you want to view in Browser? (y/N) -> "))
    neocp = scheduling.neocp_confirmation(
        config, min_score, max_magnitude, min_altitude)
    # titles=['Designation', 'Score', 'R.A.', 'Dec.', 'Alt.', 'V', 'NObs', 'Arc', 'Not Seen Days']
    if (browser_view in ["y", "Y"]):
        neocp.show_in_browser(jsviewer=True)
    else:
        print(neocp)
    print('\n\n\n\n')
    # print(neocp)


def twilight_sun_moon_menu(config: ConfigParser) -> None:
    """Prints Twilight, sun and moon times

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    result_times = scheduling.twilight_times(config)
    print(
        _(f"Civil Twilight: {result_times['CivilM'].strftime('%H:%M:%S')} - {result_times['CivilE'].strftime('%H:%M:%S')}"))
    print(
        _(f"Nautical Twilight: {result_times['NautiM'].strftime('%H:%M:%S')} - {result_times['NautiE'].strftime('%H:%M:%S')}"))
    print(
        _(f"Astronomical Twilight: {result_times['AstroM'].strftime('%H:%M:%S')} - {result_times['AstroE'].strftime('%H:%M:%S')}"))
    print('\n')
    ephemeris = scheduling.sun_moon_ephemeris(config)
    print(_(f"Sunrise: {ephemeris['Sunrise'].strftime('%H:%M:%S')}"))
    print(_(f"Sunset: {ephemeris['Sunset'].strftime('%H:%M:%S')}"))
    print(_(f"Moonrise: {ephemeris['Moonrise'].strftime('%H:%M:%S')}"))
    print(_(f"Moonset: {ephemeris['Sunrise'].strftime('%H:%M:%S')}"))
    print(_(f"Moon Illumination: {ephemeris['MoonIll']}"))
    print('\n\n\n\n')


def print_scheduling_menu() -> None:
    """Prints scheduling menu"""
    print(_('Observation scheduling'))
    print('==============================\n')
    print(_('''Choose a submenu
    1 - Weather forecast
    2 - Observing target List
    3 - NEOcp list
    4 - Object Ephemeris
    5 - Twilight Times
    0 - Back to main menu\n'''))


def scheduling_menu(config: ConfigParser) -> None:
    """Prints scheduling menu and it launches correct interface

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    choice = 99
    while (choice != 0):
        print_scheduling_menu()
        choice = get_integer(_('choice -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            scheduling.weather(config)
        if choice == 2:
            observing_target_list_menu(config)
        if choice == 3:
            neocp_confirmation_menu(config)
        if choice == 4:
            object_ephemeris_menu(config)
        if choice == 5:
            twilight_sun_moon_menu(config)


def main_menu(config: ConfigParser) -> None:
    """Prints Main menu

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    choice = 99
    while (choice != 0):
        print(_('Welcome to AsteroidPY v. 0.1'))
        print('==============================')
        print('\n')
        print(_('Choose a submenu'))
        print(_('1 - Configuration'))
        print(_('2 - Observation scheduling'))
        print(_('0 - Exit'))
        choice = get_integer(_('choice -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            config_menu(config)
        if choice == 2:
            scheduling_menu(config)


def interface(config: ConfigParser) -> None:
    """Main interface function

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    main_menu(config)


def print_change_horizon_menu() -> Dict[str, str]:
    """Prints Virtual Horizon menu"""
    horizon = {}
    horizon['nord'] = input(_('Nord Altitude -> '))
    horizon['south'] = input(_('South Altitude -> '))
    horizon['east'] = input(_('East Altitude -> '))
    horizon['west'] = input(_('West Altitude -> '))
    return horizon


def change_horizon(config: ConfigParser) -> None:
    """Prints Virtual horizon configuration menu and calls configuration function

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration option

    Returns
    -------

    """
    horizon = print_change_horizon_menu()
    configuration.virtual_horizon_configuration(config, horizon)

def object_ephemeris_menu(config: ConfigParser) -> None:
    """Prints Object Ephemeris menu and calls scheduling.object_ephemeris

    Parameters
    ----------
    config : Configparser
        the Configparser object with configuration options

    Returns
    -------

    """
    object_name = input(_('Object Name -> '))
    print(_( '''Stepping
    m - 1 minute
    h - 1 hour
    d - 1 day
    w - 1 week
    '''))
    step=input(_('Choice -> '))
    ephemeris = scheduling.object_ephemeris(config, object_name, step)
    print(ephemeris)
