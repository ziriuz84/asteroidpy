import configparser

config = configparser.ConfigParser()


def save_config():
    config.write('config.ini')


def load_config():
    config.read('config.ini')


def change_obs_coords(lat, long):
    load_config()
    config['Observatory'] = {'latitude': lat,
                             'longitude': long}
    save_config()


def change_obs_altitude(alt):
    load_config()
    config['Observatory']['altitude'] = alt
    save_config()
