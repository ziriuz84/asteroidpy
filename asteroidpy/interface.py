import datetime
import gettext
import tabulate
import asteroidpy.configuration as configuration
import asteroidpy.scheduling as scheduling

_ = gettext.gettext


def get_integer(message):
    while True:
        try:
            userInt = int(input(message))
            return userInt
        except ValueError:
            print('You must enter an integer')


def get_float(message):
    while True:
        try:
            userFloat = float(input(message))
            return userFloat
        except ValueError:
            print('You must enter a number')


def local_coords(config):
    """
    Returns local geographical coordinates

    :return coord: array
    """
    configuration.load_config(config)
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    return [lat, long]


def select_specific_time():
    """
    Returns specific time

    :type time: datetime
    """
    print('Provide me with the observation start time parameters (UTC)')
    day = get_integer(_('Day -> '))
    month = get_integer(_('Month -> '))
    year = get_integer(_('Year -> '))
    hour = get_integer(_('Hour -> '))
    minutes = get_integer(_('Minutes -> '))
    seconds = get_integer(_('Seconds -> '))
    time = datetime.datetime(
        year, month, day, hour, minutes, seconds)
    return time


def WIP():
    print(_('Work in Progress'))
    print('\n\n\n\n\n\n\n\n')


def change_obs_coords_menu(config):
    """
    Prints Observatory coordinates config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    place = input(_('Locality -> '))
    latitude = get_float(_('Latitude -> '))
    longitude = get_float(_('Longitude -> '))
    configuration.change_obs_coords(config, place, latitude, longitude)


def change_obs_altitude_menu(config):
    """
    Prints Observatory altitude config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    altitude = get_integer(_('Altitude -> '))
    configuration.change_obs_altitude(config, altitude)


def change_observer_name_menu(config):
    """
    Prints Observatory name config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    name = input(_('Observer name -> '))
    configuration.change_observer_name(config, name)


def change_obs_name_menu(config):
    """
    Prints Observer name config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    name = input(_('Observatory name -> '))
    configuration.change_obs_name(config, name)


def change_mpc_code_menu(config):
    """
    Prints MPC Code config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    code = input(_('MPC Code -> '))
    configuration.change_mpc_code(config, code)

def print_observatory_config_menu():
    print(_('''Choose an option
    1 - Change coordinates
    2 - Change altitude
    3 - Change the name of the observer
    4 - Change the name of the observatory
    5 - Change the MPC code
    0 - Back to configuration menu'''))

def observatory_config_menu(config):
    """
    Prints Observatory config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
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


def change_language(config):
    """
    Prints language configuration menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    lang = ''
    print(_('Select a language'))
    print('1 - English')
    lang_chosen = get_integer(_('Language -> '))
    if lang_chosen == 1:
        lang = 'en'
    configuration.change_language(config, lang)


def general_config_menu(config):
    """
    Prints menu for general configuration options

    :param config: the Configparser object with configuration option
    :type config: Configparser
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


def config_menu(config):
    """
    Prints main config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
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

def observing_target_list_menu(config):
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

def neocp_confirmation_menu(config):
    """
    Prints NEOcp confirmation menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    min_score=get_integer(_('Minimum score -> '))
    max_magnitude=get_float(_('Maximum magnitude -> '))
    min_altitude=get_integer(_('Minimum altitude -> '))
    browser_view = input(_("Do you want to view in Browser? (y/N) -> "))
    neocp=scheduling.neocp_confirmation(config, min_score, max_magnitude, min_altitude)
    # titles=['Designation', 'Score', 'R.A.', 'Dec.', 'Alt.', 'V', 'NObs', 'Arc', 'Not Seen Days']
    if (browser_view in ["y", "Y"]):
        neocp.show_in_browser(jsviewer=True)
    else:
        print(neocp)
    print('\n\n\n\n')
    # print(neocp)

def twilight_sun_moon_menu(config):
    """
    Prints Twilight, sun and moon menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    result_times = scheduling.twilight_times(config)
    print(_(f"Civil Twilight: {result_times['CivilM'].strftime('%H:%M:%S')} - {result_times['CivilE'].strftime('%H:%M:%S')}"))
    print(_(f"Nautical Twilight: {result_times['NautiM'].strftime('%H:%M:%S')} - {result_times['NautiE'].strftime('%H:%M:%S')}"))
    print(_(f"Astronomical Twilight: {result_times['AstroM'].strftime('%H:%M:%S')} - {result_times['AstroE'].strftime('%H:%M:%S')}"))
    print('\n')
    ephemeris=scheduling.sun_moon_ephemeris(config)
    print(_(f"Sunrise: {ephemeris['Sunrise'].strftime('%H:%M:%S')}"))
    print(_(f"Sunset: {ephemeris['Sunset'].strftime('%H:%M:%S')}"))
    print(_(f"Moonrise: {ephemeris['Moonrise'].strftime('%H:%M:%S')}"))
    print(_(f"Moonset: {ephemeris['Sunrise'].strftime('%H:%M:%S')}"))
    print(_(f"Moon Illumination: {ephemeris['MoonIll']}"))
    print('\n\n\n\n')

def print_scheduling_menu():
    """
    Prints scheduling menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    print(_('Observation scheduling'))
    print('==============================\n')
    print(_('''Choose a submenu
    1 - Weather forecast
    2 - Observing target List
    3 - NEOcp list
    4 - Twilight Times
    0 - Back to main menu\n'''))


def scheduling_menu(config):
    """
    Prints scheduling menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
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
            twilight_sun_moon_menu(config)


def main_menu(config):
    """
    Prints Main menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
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


def interface(config):
    """
    Main interface function

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    main_menu(config)
