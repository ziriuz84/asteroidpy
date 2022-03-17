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

def observatory_config_menu(config):
    """
    Prints Observatory config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print(_('Configuration -> Observatory'))
        print('==============================')
        print('\n')
        configuration.print_obs_config(config)
        print(_('Choose an option'))
        print(_('1 - Change coordinates'))
        print(_('2 - Change altitude'))
        print(_('3 - Change the name of the observer'))
        print(_('4 - Change the name of the observatory'))
        print(_('5 - Change the MPC code'))
        print(_('0 - Back to configuration menu'))
        choice = get_integer(_('choice -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            place = input(_('Locality -> '))
            latitude = get_float(_('Latitude -> '))
            longitude = get_float(_('Longitude -> '))
            configuration.change_obs_coords(config, place, latitude, longitude)
        if choice == 2:
            altitude = get_integer(_('Altitude -> '))
            configuration.change_obs_altitude(config, altitude)
        if choice == 3:
            name = input(_('Observer name -> '))
            configuration.change_observer_name(config, name)
        if choice == 4:
            name = input(_('Observatory name -> '))
            configuration.change_obs_name(config, name)
        if choice == 5:
            code = input(_('MPC Code -> '))
            configuration.change_mpc_code(config, code)


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


def scheduling_menu(config):
    """
    Prints scheduling menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print(_('Observation scheduling'))
        print('==============================')
        print('\n')
        print(_('Choose a submenu'))
        print(_('1 - Weather forecast'))
        print(_('2 - Observing target List'))
        print(_('3 - NEOcp list'))
        print(_('4 - Twilight Times'))
        print(_('0 - Back to main menu'))
        choice = get_integer(_('choice -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            scheduling.weather(config)
        if choice == 2:
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
            result = scheduling.observing_target_list(config, payload)
            asteroids = []
            for i in range(len(result[1])):
                asteroids.append(result[1][i])
            print('\n')
            print(tabulate.tabulate(asteroids,
                  headers=result[0], tablefmt='fancy_grid'))
            print('\n\n\n\n')
        if choice == 3:
            min_score=get_integer(_('Minimum score -> '))
            max_magnitude=get_float(_('Maximum magnitude -> '))
            min_altitude=get_integer(_('Minimum altitude -> '))
            neocp=scheduling.neocp_search(config, min_score, max_magnitude, min_altitude)
            titles=['Designation', 'Score', 'R.A.', 'Dec.', 'Alt.', 'V', 'NObs', 'Arc', 'Not Seen Days']
            print(tabulate.tabulate(neocp, headers=titles, tablefmt='fancy_grid'))
            print('\n\n\n\n')
            # print(neocp)
        if choice == 4:
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
