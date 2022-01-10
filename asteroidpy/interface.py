import configuration
import gettext
import scheduling

_ = gettext.gettext


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
            lang = ''
            print(_('Select a language'))
            print('1 - English')
            lang_chosen = input(_('Language -> '))
            if lang_chosen == 1:
                lang = 'en'
            configuration.change_language(config, lang)


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
            scheduling.observing_target_list(config)


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
