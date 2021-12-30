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
        print(_('Configurazione -> Osservatorio'))
        print(_('=============================='))
        print('\n')
        configuration.print_obs_config(config)
        print(_('Scegli un\'opzione'))
        print(_('1 - Cambia coordinate'))
        print(_('2 - Cambia altitudine'))
        print(_('3 - Cambia il nome dell\'osservatore'))
        print(_('4 - Cambia il nome dell\'osservatorio'))
        print(_('5 - Cambia il codice MPC'))
        print(_('0 - Torna la livello superiore'))
        print(_('Torna al menu della configurazione'))
        choice = eval(input(_('scelta -> ')))
        print('\n\n\n\n\n')
        if choice == 1:
            place = input(_('Località -> '))
            latitude = eval(input(_('Latitudine -> ')))
            longitude = eval(input(_('Longitudine -> ')))
            configuration.change_obs_coords(config, place, latitude, longitude)
        if choice == 2:
            altitude = eval(input(_('Altitudine -> ')))
            configuration.change_obs_altitude(config, altitude)
        if choice == 3:
            name = input(_('Nome osservatore -> '))
            configuration.change_observer_name(config, name)
        if choice == 4:
            name = input(_('Nome osservatorio -> '))
            configuration.change_obs_name(config, name)
        if choice == 5:
            code = input(_('Codice MPC -> '))
            configuration.change_mpc_code(config, code)


def config_menu(config):
    """
    Prints main config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print(_('Configurazione'))
        print('==============================')
        print('\n')
        print(_('Scegli un sottomenu'))
        print(_('1 - Osservatorio'))
        print(_('0 - Torna al menu principale'))
        choice = eval(input(_('scelta -> ')))
        print('\n\n\n\n\n')
        if choice == 1:
            observatory_config_menu(config)

def scheduling_menu(config):
    """
    Prints scheduling menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print(_('Programmazione osservazioni'))
        print('==============================')
        print('\n')
        print(_('Scegli un sottomenu'))
        print(_('1 - Previsioni meteo'))
        print(_('2 - Observing target List'))
        print(_('0 - Torna al menu principale'))
        choice = eval(input(_('scelta -> ')))
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
        print(_('Benvenuto in AsteroidPY v. 0.1'))
        print('==============================')
        print('\n')
        print(_('Scegli un\'opzione'))
        print(_('1 - Configurazione'))
        print(_('2 - Programmazione osservazioni'))
        print(_('0 - Esci'))
        choice = eval(input(_('scelta -> ')))
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
