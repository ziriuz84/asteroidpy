import unittest
import datetime
import configparser
import asyncio
import respx
import io
from unittest.mock import patch, Mock
from httpx import Response
from astropy.time import Time
from astropy.table import QTable
from asteroidpy import scheduling

class TestScheduling(unittest.TestCase):

    def setUp(self):
        self.config = configparser.ConfigParser()
        self.config.read('/home/sirio/Projects/side/asteroidpy/tests/config.ini')
        if not self.config.has_section('Observatory'):
            self.config.add_section('Observatory')
        self.config.set('Observatory', 'obs_name', 'Test Observatory')

    def test_weather_time(self):
        time_init = "2025072910"
        deltaT = 3
        expected_time = "29/07 13:00"
        self.assertEqual(scheduling.weather_time(time_init, deltaT), expected_time)

    def test_skycoord_format(self):
        ra_coord = "10 20 30"
        dec_coord = "+10 20 30"
        self.assertEqual(scheduling.skycoord_format(ra_coord, "ra"), "10h20m30s")
        self.assertEqual(scheduling.skycoord_format(dec_coord, "dec"), "+10d20m30s")

    def test_is_visible(self):
        time = Time('2025-07-29T22:00:00')
        # Coordinates that should be visible (high in the south)
        visible_coords = ['18 00 00', '+45 00 00']
        # Coordinates that should NOT be visible (below horizon)
        non_visible_coords = ['06 00 00', '-45 00 00']
        self.assertTrue(scheduling.is_visible(self.config, visible_coords, time))
        self.assertFalse(scheduling.is_visible(self.config, non_visible_coords, time))

    @respx.mock
    def test_httpx_get_json(self):
        url = "http://test.com"
        payload = {"key": "value"}
        mock_response = {"message": "success"}
        respx.get(url).mock(return_value=Response(200, json=mock_response))
        result, status_code = asyncio.run(scheduling.httpx_get(url, payload, "json"))
        self.assertEqual(status_code, 200)
        self.assertEqual(result, mock_response)

    @respx.mock
    def test_httpx_get_text(self):
        url = "http://test.com"
        payload = {"key": "value"}
        mock_response = "Success"
        respx.get(url).mock(return_value=Response(200, text=mock_response))
        result, status_code = asyncio.run(scheduling.httpx_get(url, payload, "text"))
        self.assertEqual(status_code, 200)
        self.assertEqual(result, mock_response)

    @respx.mock
    def test_httpx_post_json(self):
        url = "http://test.com"
        payload = {"key": "value"}
        mock_response = {"message": "success"}
        respx.post(url).mock(return_value=Response(200, json=mock_response))
        result, status_code = asyncio.run(scheduling.httpx_post(url, payload, "json"))
        self.assertEqual(status_code, 200)
        self.assertEqual(result, mock_response)

    @respx.mock
    def test_httpx_post_text(self):
        url = "http://test.com"
        payload = {"key": "value"}
        mock_response = "Success"
        respx.post(url).mock(return_value=Response(200, text=mock_response))
        result, status_code = asyncio.run(scheduling.httpx_post(url, payload, "text"))
        self.assertEqual(status_code, 200)
        self.assertEqual(result, mock_response)

    @patch('requests.get')
    def test_weather(self, mock_get):
        mock_response = {
            "init": "2025072910",
            "dataseries": [
                {
                    "timepoint": 3,
                    "cloudcover": 1,
                    "seeing": 2,
                    "transparency": 3,
                    "lifted_index": -1,
                    "temp2m": 25,
                    "rh2m": 10,
                    "wind10m": {"direction": "N", "speed": 4},
                    "prec_type": "none"
                }
            ]
        }
        mock_get.return_value.json.return_value = mock_response
        captured_output = io.StringIO()
        import sys
        original_stdout = sys.stdout
        sys.stdout = captured_output
        scheduling.weather(self.config)
        sys.stdout = original_stdout
        output = captured_output.getvalue()
        self.assertIn("29/07 13:00", output)
        self.assertIn("0%-6%", output)
        self.assertIn('0.5"-0.75"', output)

    @patch('requests.post')
    def test_observing_target_list_scraper(self, mock_post):
        mock_html = '''
        <html><body>
            <table></table><table></table><table></table>
            <table>
                <tr><th>h1</th><th>h2</th></tr>
                <tr><td>r1c1</td><td>r1c2</td></tr>
                <tr><td>r2c1</td><td>r2c2</td></tr>
            </table>
        </body></html>
        '''
        mock_post.return_value = Mock(content=mock_html)
        data = scheduling.observing_target_list_scraper("http://dummy.url", {})
        self.assertEqual(len(data), 3) # header row + 2 data rows
        self.assertEqual(data[1], ['r1c1', 'r1c2'])
        self.assertEqual(data[2], ['r2c1', 'r2c2'])

    @patch('asteroidpy.scheduling.observing_target_list_scraper')
    @patch('asteroidpy.scheduling.is_visible')
    def test_observing_target_list(self, mock_is_visible, mock_scraper):
        mock_scraper.return_value = [
            ['Obj1', '15.0', '1.0', '20.0', '2025-07-29T22:00:00z', '18 00 00', '+45 00 00', '30'],
            ['Obj2', '16.0', '2.0', '21.0', '2025-07-29T23:00:00z', '06 00 00', '-45 00 00', '10']
        ]
        mock_is_visible.side_effect = [True, False]
        results = scheduling.observing_target_list(self.config, {})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Designation'], 'Obj1')

    @patch('asteroidpy.scheduling.httpx_get')
    @patch('asteroidpy.scheduling.is_visible')
    def test_neocp_confirmation(self, mock_is_visible, mock_httpx_get):
        mock_httpx_get.return_value = ([
            {
                "Temp_Desig": "P21E2tB", "Score": 80, "R.A.": "270.0", "Decl.": "-30.0",
                "V": 18.0, "NObs": 10, "Arc": 1.0, "Not_Seen_dys": 0.5
            },
            {
                "Temp_Desig": "P21E2tC", "Score": 70, "R.A.": "90.0", "Decl.": "-50.0",
                "V": 19.0, "NObs": 5, "Arc": 2.0, "Not_Seen_dys": 1.0
            }
        ], 200)
        mock_is_visible.side_effect = [True, False]
        table = scheduling.neocp_confirmation(self.config, 75, 20)
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]['Temp_Desig'], 'P21E2tB')

    def test_twilight_times(self):
        result = scheduling.twilight_times(self.config)
        self.assertIn('AstroM', result)
        self.assertIsInstance(result['AstroM'], Time)

    def test_sun_moon_ephemeris(self):
        result = scheduling.sun_moon_ephemeris(self.config)
        self.assertIn('Sunrise', result)
        self.assertIsInstance(result['Sunrise'], Time)
        self.assertIn('MoonIll', result)
        self.assertIsInstance(result['MoonIll'], float)

if __name__ == '__main__':
    unittest.main()