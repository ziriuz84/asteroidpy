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
def config_menu():
    choice = 99
    while (choice!=0):
        print('Configurazione')
        print('==============================')
        print('\n')
        print('Scegli un sottomenu')
        print('1 - Osservatorio')
        print('0 - Torna al menu principale')
        choice = eval(input('scelta -> '))
        print('\n\n\n\n\n')

def main_menu():
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
            config_menu()


def interface():
    main_menu()
