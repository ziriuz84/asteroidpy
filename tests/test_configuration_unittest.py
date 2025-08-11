import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from configparser import ConfigParser
from unittest.mock import patch

import importlib.util

# Load the configuration module directly from its file path to avoid
# importing the whole package (and optional deps like httpx)
_ROOT = os.path.dirname(os.path.dirname(__file__))
_CONFIG_PATH = os.path.join(_ROOT, "asteroidpy", "configuration.py")
_SPEC = importlib.util.spec_from_file_location("asteroidpy.configuration", _CONFIG_PATH)
cfg = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(cfg)


def config_file_path(home_dir: str) -> str:
    return os.path.join(home_dir, ".asteroidpy")


def read_config_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_config_file(path: str, contents: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(contents)


def create_minimal_config_text(**overrides) -> str:
    general_lang = overrides.get("lang", "en")
    place = overrides.get("place", "")
    latitude = overrides.get("latitude", "0.0")
    longitude = overrides.get("longitude", "0.0")
    altitude = overrides.get("altitude", "0.0")
    obs_name = overrides.get("obs_name", "")
    observer_name = overrides.get("observer_name", "")
    mpc_code = overrides.get("mpc_code", "XXX")

    return (
        "[General]\n"
        f"lang = {general_lang}\n\n"
        "[Observatory]\n"
        f"place = {place}\n"
        f"latitude = {latitude}\n"
        f"longitude = {longitude}\n"
        f"altitude = {altitude}\n"
        f"obs_name = {obs_name}\n"
        f"observer_name = {observer_name}\n"
        f"mpc_code = {mpc_code}\n"
    )


class ConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.fake_home = os.path.join(self.tmpdir_obj.name, "home")
        os.makedirs(self.fake_home, exist_ok=True)

        self.expanduser_patcher = patch(
            "os.path.expanduser",
            side_effect=lambda p: self.fake_home if p == "~" else os.path.expanduser(p),
        )
        self.expanduser_patcher.start()

    def tearDown(self) -> None:
        self.expanduser_patcher.stop()
        self.tmpdir_obj.cleanup()

    def new_config(self) -> ConfigParser:
        return ConfigParser()

    def test_save_config_writes_file(self):
        config = self.new_config()
        config["General"] = {"lang": "en"}
        config["Observatory"] = {
            "place": "",
            "latitude": "0.0",
            "longitude": "0.0",
            "altitude": "0.0",
            "obs_name": "",
            "observer_name": "",
            "mpc_code": "XXX",
        }

        cfg.save_config(config)

        path = config_file_path(self.fake_home)
        self.assertTrue(os.path.exists(path))
        text = read_config_file(path)
        self.assertIn("[General]", text)
        self.assertIn("[Observatory]", text)

    def test_change_language_updates_file(self):
        write_config_file(config_file_path(self.fake_home), create_minimal_config_text(lang="en"))

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            cfg.change_language(self.new_config(), "it")

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("lang = it", new_text)

    def test_change_obs_coords_updates_file(self):
        write_config_file(
            config_file_path(self.fake_home),
            create_minimal_config_text(place="Old", latitude="1.0", longitude="2.0"),
        )

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            cfg.change_obs_coords(self.new_config(), place="NewPlace", lat=45.1, long=9.2)

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("place = NewPlace", new_text)
        self.assertIn("latitude = 45.1", new_text)
        self.assertIn("longitude = 9.2", new_text)

    def test_change_obs_altitude_updates_file(self):
        write_config_file(config_file_path(self.fake_home), create_minimal_config_text(altitude="0.0"))

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            cfg.change_obs_altitude(self.new_config(), alt=123)

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("altitude = 123", new_text)

    def test_change_mpc_code_updates_file(self):
        write_config_file(config_file_path(self.fake_home), create_minimal_config_text(mpc_code="XXX"))

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            cfg.change_mpc_code(self.new_config(), code="C10")

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("mpc_code = C10", new_text)

    def test_change_obs_name_updates_file(self):
        write_config_file(config_file_path(self.fake_home), create_minimal_config_text(obs_name=""))

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            cfg.change_obs_name(self.new_config(), name="AstroObs")

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("obs_name = AstroObs", new_text)

    def test_change_observer_name_updates_file(self):
        write_config_file(
            config_file_path(self.fake_home), create_minimal_config_text(observer_name="")
        )

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            cfg.change_observer_name(self.new_config(), name="Jane Doe")

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("observer_name = Jane Doe", new_text)

    def test_virtual_horizon_configuration_writes_values(self):
        write_config_file(config_file_path(self.fake_home), create_minimal_config_text())

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            horizon = {"nord": "10", "south": "12", "east": "8", "west": "9"}
            cfg.virtual_horizon_configuration(self.new_config(), horizon)

        new_text = read_config_file(config_file_path(self.fake_home))
        self.assertIn("nord_altitude = 10", new_text)
        self.assertIn("south_altitude = 12", new_text)
        self.assertIn("east_altitude = 8", new_text)
        self.assertIn("west_altitude = 9", new_text)

    def test_print_obs_config_outputs_expected(self):
        write_config_file(
            config_file_path(self.fake_home),
            create_minimal_config_text(
                place="City",
                latitude="45.0",
                longitude="9.0",
                altitude="100.0",
                obs_name="MainObs",
                observer_name="John",
                mpc_code="A12",
            ),
        )

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            buf = io.StringIO()
            with redirect_stdout(buf):
                cfg.print_obs_config(self.new_config())
            stdout = buf.getvalue()

        self.assertIn("Località: City", stdout)
        self.assertIn("Latitudine: 45.0", stdout)
        self.assertIn("Longitudine: 9.0", stdout)
        self.assertIn("Altitudine: 100.0", stdout)
        self.assertIn("Osservatore: John", stdout)
        self.assertIn("Nome Osservatorio: MainObs", stdout)
        self.assertIn("Codice MPC: A12", stdout)

    def test_load_config_reads_existing_file(self):
        write_config_file(config_file_path(self.fake_home), create_minimal_config_text(lang="en"))

        with patch("os.walk", return_value=[("/irrelevant", [], [".asteroidpy"])]) :
            conf = self.new_config()
            cfg.load_config(conf)
            self.assertEqual(conf.get("General", "lang"), "en")

    def test_load_config_initializes_when_missing(self):
        called = {"count": 0}

        def fake_initialize(conf: ConfigParser):
            called["count"] += 1
            conf["General"] = {"lang": "en"}
            conf["Observatory"] = {
                "place": "",
                "latitude": "0.0",
                "longitude": "0.0",
                "altitude": "0.0",
                "obs_name": "",
                "observer_name": "",
                "mpc_code": "XXX",
            }
            cfg.save_config(conf)

        with patch.object(cfg, "initialize", side_effect=fake_initialize):
            def fake_walk(_dir_path):
                yield ("/a", ["b"], [])
                yield ("/a/b", ["c"], [])
                yield ("/a/b/c", [], [])  # triggers initialize at i == 2

            with patch("os.walk", side_effect=fake_walk):
                conf = self.new_config()
                cfg.load_config(conf)

        self.assertGreaterEqual(called["count"], 1)
        self.assertTrue(os.path.exists(config_file_path(self.fake_home)))


if __name__ == "__main__":
    unittest.main()
