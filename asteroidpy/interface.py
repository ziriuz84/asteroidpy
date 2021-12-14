import configuration
import scheduling

def WIP():
    print('Work in Progress')
    print('\n\n\n\n\n\n\n\n')


def observatory_config_menu(config):
    """
    Prints Observatory config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print('Configurazione -> Osservatorio')
        print('==============================')
        print('\n')
        configuration.print_obs_config(config)
        print('Scegli un\'opzione')
        print('1 - Cambia coordinate')
        print('2 - Cambia altitudine')
        print('3 - Cambia il nome dell\'osservatore')
        print('4 - Cambia il nome dell\'osservatorio')
        print('5 - Cambia il codice MPC')
        print('0 - Torna la livello superiore')
        print('Torna al menu della configurazione')
        choice = eval(input('scelta -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            place = input('Località -> ')
            latitude = eval(input('Latitudine -> '))
            longitude = eval(input('Longitudine -> '))
            configuration.change_obs_coords(config, place, latitude, longitude)
        if choice == 2:
            altitude = eval(input('Altitudine -> '))
            configuration.change_obs_altitude(config, altitude)
        if choice == 3:
            name = input('Nome osservatore -> ')
            configuration.change_observer_name(config, name)
        if choice == 4:
            name = input('Nome osservatorio -> ')
            configuration.change_obs_name(config, name)
        if choice == 5:
            code = input('Codice MPC -> ')
            configuration.change_mpc_code(config, code)


def config_menu(config):
    """
    Prints main config menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print('Configurazione')
        print('==============================')
        print('\n')
        print('Scegli un sottomenu')
        print('1 - Osservatorio')
        print('0 - Torna al menu principale')
        choice = eval(input('scelta -> '))
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
        print('Programmazione osservazioni')
        print('==============================')
        print('\n')
        print('Scegli un sottomenu')
        print('1 - Previsioni meteo')
        print('2 - Observing target List')
        print('0 - Torna al menu principale')
        choice = eval(input('scelta -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            scheduling.weather(config)
        if choice == 2:
            WIP()

def main_menu(config):
    """
    Prints Main menu

    :param config: the Configparser object with configuration option
    :type config: Configparser
    """
    choice = 99
    while (choice != 0):
        print('Benvenuto in AsteroidPY v. 0.1')
        print('==============================')
        print('\n')
        print('Scegli un\'opzione')
        print('1 - Configurazione')
        print('2 - Programmazione osservazioni')
        print('0 - Esci')
        choice = eval(input('scelta -> '))
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
