##
# @file interface.py
#
# @brief The main interface module
#
# @section description_interface Description
# Simply tha main interface file
#
# @section todo_interface TODO
# - implement a more useful interface library, as Urwid
#
# @section author_interface Author(s)
# - Created by Sirio Negri on 11/23/2021
# - modified by Sirio Negri on 11/23/2021
import configuration


def observatory_config_menu(config):
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


def main_menu(config):
    choice = 99
    while (choice != 0):
        print('Benvenuto in AsteroidPY v. 0.1')
        print('==============================')
        print('\n')
        print('Scegli un\'opzione')
        print('1 - Configurazione')
        print('0 - Esci')
        choice = eval(input('scelta -> '))
        print('\n\n\n\n\n')
        if choice == 1:
            config_menu(config)


def interface(config):
    main_menu(config)
