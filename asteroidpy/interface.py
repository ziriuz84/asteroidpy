import configuration
import datetime
import gettext
import scheduling

_ = gettext.gettext


def local_coords(config):
    configuration.load_config(config)
    lat = config['Observatory']['latitude']
    long = config['Observatory']['longitude']
    return [lat, long]

def select_specific_time():
    print('Provide me with the observation start time parameters (UTC)')
    day = eval(input(_('Day -> ')))
    month = eval(input(_('Month -> ')))
    year = eval(input(_('Year -> ')))
    hour = eval(input(_('Hour -> ')))
    minutes = eval(input(_('Minutes -> ')))
    seconds = eval(input(_('Seconds -> ')))
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
        choice = eval(input(_('choice -> ')))
        print('\n\n\n\n\n')
        if choice == 1:
            place = input(_('Locality -> '))
            latitude = eval(input(_('Latitude -> ')))
            longitude = eval(input(_('Longitude -> ')))
            configuration.change_obs_coords(config, place, latitude, longitude)
        if choice == 2:
            altitude = eval(input(_('Altitude -> ')))
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
    lang = ''
    print(_('Select a language'))
    print('1 - English')
    lang_chosen = input(_('Language -> '))
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
        choice = eval(input(_('choice -> ')))
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
        print(_('0 - Back to main menu'))
        choice = eval(input(_('choice -> ')))
        print('\n\n\n\n\n')
        if choice == 1:
            scheduling.weather(config)
        if choice == 2:
            authenticity_token = "W5eBzzw9Clj4tJVzkz0z%2F2EK18jvSS%2BffHxZpAshylg%3D"
            coordinates=local_coords(config)
            select_time = input(_(
                'Do you want to know the asteroids visible right now? '))
            if (select_time == 's' or select_time == 'y'):
                time = datetime.datetime.utcnow()
            else:
                time = select_specific_time()
            duration = input(_("Duration of observation -> "))
            solar_elongation = input(_("Minimal solar elongation -> "))
            lunar_elongation = input(_("Minimal lunar elongation -> "))
            minimal_height = input(_("Minimal altitude-> "))
            max_objects = input(_("Maximum number of objects -> "))
            object_request = input(_(
                'Select type of object\n1 - Asteroids\n2 - NEAs\n3 - Comets\nChoice -> '))
            if (object_request == '2'):
                object_type = 'neo'
            elif (object_request == '3'):
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
            scheduling.observing_target_list(config, payload)


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
        choice = eval(input(_('choice -> ')))
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
