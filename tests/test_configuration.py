import unittest
import configparser
from unittest.mock import patch, MagicMock, mock_open
from asteroidpy import configuration
import os # Import os for os.walk mock
from astropy.coordinates import Angle

class TestConfiguration(unittest.TestCase):

    def setUp(self):
        self.config = configparser.ConfigParser()
        self.config['General'] = {'lang': 'en'}
        self.config['Observatory'] = {
            "place": "",
            "latitude": "0.0",
            "longitude": "0.0",
            "altitude": "0.0",
            "obs_name": "",
            "observer_name": "",
            "mpc_code": "XXX",
            "east_altitude": "0",
            "nord_altitude": "0",
            "south_altitude": "0",
            "west_altitude": "0",
        }

    @patch('asteroidpy.configuration.save_config')
    def test_initialize(self, mock_save_config):
        # Re-initialize config for this specific test to ensure it starts clean
        self.config = configparser.ConfigParser()
        configuration.initialize(self.config)
        self.assertTrue(self.config.has_section('General'))
        self.assertTrue(self.config.has_section('Observatory'))
        self.assertEqual(self.config['General']['lang'], 'en')
        self.assertEqual(self.config['Observatory']['mpc_code'], 'XXX')
        mock_save_config.assert_called_once_with(self.config)

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('platform.system', return_value="Linux")
    @patch('asteroidpy.configuration.user_config_dir', return_value='/tmp/test_config_dir')
    def test_save_config(self, mock_user_config_dir, mock_system, mock_open_file, mock_exists, mock_makedirs):
        self.config.write = MagicMock()
        self.config['General'] = {'lang': 'fr'}
        configuration.save_config(self.config)
        mock_exists.assert_called_once()
        mock_makedirs.assert_not_called()
        mock_open_file.assert_called_once()
        self.config.write.assert_called_once_with(mock_open_file())

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('platform.system', return_value="Linux")
    @patch.object(configparser.ConfigParser, 'read')
    @patch('asteroidpy.configuration.initialize')
    @patch('os.walk') # Mock os.walk
    @patch('asteroidpy.configuration.user_config_dir', return_value='/tmp/test_config_dir') # Mock user_config_dir
    def test_load_config_exists(self, mock_user_config_dir, mock_os_walk, mock_initialize, mock_config_read, mock_system, mock_exists, mock_makedirs):
        # Simulate directory exists, and file exists within os.walk
        mock_exists.side_effect = [True] # For the initial os.path.exists(dir_path)
        mock_os_walk.return_value = [('/tmp/test_config_dir', [], ['asteroidpy.ini'])] # Simulate finding the file

        configuration.load_config(self.config)

        mock_makedirs.assert_not_called() # Directory already exists
        mock_config_read.assert_called_once_with('/tmp/test_config_dir/asteroidpy.ini')
        mock_initialize.assert_not_called()

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('platform.system', return_value="Linux")
    @patch.object(configparser.ConfigParser, 'read')
    @patch('asteroidpy.configuration.initialize')
    @patch('os.walk') # Mock os.walk
    @patch('asteroidpy.configuration.user_config_dir', return_value='/tmp/test_config_dir') # Mock user_config_dir
    def test_load_config_not_exists(self, mock_user_config_dir, mock_os_walk, mock_initialize, mock_config_read, mock_system, mock_exists, mock_makedirs):
        # Simulate directory does not exist, and file does not exist within os.walk
        mock_exists.side_effect = [False] # For the initial os.path.exists(dir_path)
        mock_os_walk.return_value = [('/tmp/test_config_dir', [], [])] # Simulate not finding the file

        configuration.load_config(self.config)

        mock_makedirs.assert_called_once_with('/tmp/test_config_dir') # Directory created
        mock_config_read.assert_not_called()
        mock_initialize.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_change_language(self, mock_load_config, mock_save_config):
        configuration.change_language(self.config, "es")
        self.assertEqual(self.config['General']['lang'], 'es')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_change_obs_coords(self, mock_load_config, mock_save_config):
        configuration.change_obs_coords(self.config, "Test Place", 10.0, 20.0)
        self.assertEqual(self.config['Observatory']['place'], 'Test Place')
        self.assertEqual(self.config['Observatory']['latitude'], '10.0')
        self.assertEqual(self.config['Observatory']['longitude'], '20.0')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_change_obs_altitude(self, mock_load_config, mock_save_config):
        configuration.change_obs_altitude(self.config, 500)
        self.assertEqual(self.config['Observatory']['altitude'], '500')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_change_mpc_code(self, mock_load_config, mock_save_config):
        configuration.change_mpc_code(self.config, "ABC")
        self.assertEqual(self.config['Observatory']['mpc_code'], 'ABC')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_change_obs_name(self, mock_load_config, mock_save_config):
        configuration.change_obs_name(self.config, "My Obs")
        self.assertEqual(self.config['Observatory']['obs_name'], 'My Obs')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_change_observer_name(self, mock_load_config, mock_save_config):
        configuration.change_observer_name(self.config, "John Doe")
        self.assertEqual(self.config['Observatory']['observer_name'], 'John Doe')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('asteroidpy.configuration.save_config')
    @patch('asteroidpy.configuration.load_config')
    def test_virtual_horizon_configuration(self, mock_load_config, mock_save_config):
        horizon = {"nord": "10", "south": "20", "east": "30", "west": "40"}
        configuration.virtual_horizon_configuration(self.config, horizon)
        self.assertEqual(self.config['Observatory']['nord_altitude'], '10')
        self.assertEqual(self.config['Observatory']['south_altitude'], '20')
        self.assertEqual(self.config['Observatory']['east_altitude'], '30')
        self.assertEqual(self.config['Observatory']['west_altitude'], '40')
        mock_load_config.assert_called_once_with(self.config)
        mock_save_config.assert_called_once_with(self.config)

    @patch('astroquery.mpc.MPC.get_observatory_location')
    def test_get_observatory_coordinates(self, mock_get_observatory_location):
        mock_get_observatory_location.return_value = (
            Angle('10d'), 10.0, 20.0, 'Test Obs'
        )
        lon, lat, alt, name = configuration.get_observatory_coordinates("XXX")
        self.assertAlmostEqual(lon, 10.0)
        self.assertAlmostEqual(lat, 90.0 - 26.56505117707799)
        self.assertAlmostEqual(alt, 22.3606797749979)
        self.assertEqual(name, 'Test Obs')

    @patch('asteroidpy.configuration.load_config')
    def test_print_obs_config(self, mock_load_config):
        # Set up config with some values
        self.config['Observatory']['place'] = 'Test Place'
        self.config['Observatory']['latitude'] = '10.0'
        self.config['Observatory']['longitude'] = '20.0'
        self.config['Observatory']['altitude'] = '500.0'
        self.config['Observatory']['observer_name'] = 'Test Observer'
        self.config['Observatory']['obs_name'] = 'Test Observatory'
        self.config['Observatory']['mpc_code'] = 'YYY'

        # Capture stdout
        import sys
        from io import StringIO
        captured_output = StringIO()
        sys.stdout = captured_output

        configuration.print_obs_config(self.config)

        sys.stdout = sys.__stdout__ # Reset stdout

        output = captured_output.getvalue()
        self.assertIn("Località: Test Place", output)
        self.assertIn("Latitudine: 10.0", output)
        self.assertIn("Longitudine: 20.0", output)
        self.assertIn("Altitudine: 500.0", output)
        self.assertIn("Osservatore: Test Observer", output)
        self.assertIn("Nome Osservatorio: Test Observatory", output)
        self.assertIn("Codice MPC: YYY", output)

if __name__ == '__main__':
    unittest.main()