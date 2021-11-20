from config import configuration


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
            configuration()


def interface():
    main_menu()
