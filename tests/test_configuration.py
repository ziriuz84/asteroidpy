import os
from configparser import ConfigParser
import builtins
import types
import io
import pytest

# Module under test
import asteroidpy.configuration as cfg


@pytest.fixture()
def tmp_home(monkeypatch, tmp_path):
    """Provide an isolated fake HOME and the path to the config file."""
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)

    original_expanduser = os.path.expanduser

    def fake_expanduser(path: str) -> str:
        return str(fake_home) if path == "~" else original_expanduser(path)

    monkeypatch.setattr(os.path, "expanduser", fake_expanduser)

    return fake_home


@pytest.fixture()
def fresh_config() -> ConfigParser:
    return ConfigParser()


def read_config_file(path: os.PathLike) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_config_file(path: os.PathLike, contents: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(contents)


def config_file_path(home: os.PathLike) -> os.PathLike:
    return os.fspath(home / ".asteroidpy")


def create_minimal_config_text(**overrides) -> str:
    # Values must be strings for ConfigParser compatibility
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


def test_save_config_writes_file(tmp_home, fresh_config):
    # Prepare a config with string values only
    fresh_config["General"] = {"lang": "en"}
    fresh_config["Observatory"] = {
        "place": "",
        "latitude": "0.0",
        "longitude": "0.0",
        "altitude": "0.0",
        "obs_name": "",
        "observer_name": "",
        "mpc_code": "XXX",
    }

    cfg.save_config(fresh_config)

    path = config_file_path(tmp_home)
    assert os.path.exists(path)
    text = read_config_file(path)
    assert "[General]" in text and "[Observatory]" in text


def test_change_language_updates_file(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text(lang="en"))
    cfg.change_language(fresh_config, "it")

    new_text = read_config_file(config_file_path(tmp_home))
    assert "lang = it" in new_text


def test_change_obs_coords_updates_file(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text(place="Old", latitude="1.0", longitude="2.0"))

    cfg.change_obs_coords(fresh_config, place="NewPlace", lat=45.1, long=9.2)

    new_text = read_config_file(config_file_path(tmp_home))
    assert "place = NewPlace" in new_text
    assert "latitude = 45.1" in new_text
    assert "longitude = 9.2" in new_text


def test_change_obs_altitude_updates_file(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text(altitude="0.0"))

    cfg.change_obs_altitude(fresh_config, alt=123)

    new_text = read_config_file(config_file_path(tmp_home))
    assert "altitude = 123" in new_text


def test_change_mpc_code_updates_file(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text(mpc_code="XXX"))

    cfg.change_mpc_code(fresh_config, code="C10")

    new_text = read_config_file(config_file_path(tmp_home))
    assert "mpc_code = C10" in new_text


def test_change_obs_name_updates_file(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text(obs_name=""))

    cfg.change_obs_name(fresh_config, name="AstroObs")

    new_text = read_config_file(config_file_path(tmp_home))
    assert "obs_name = AstroObs" in new_text


def test_change_observer_name_updates_file(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text(observer_name=""))

    cfg.change_observer_name(fresh_config, name="Jane Doe")

    new_text = read_config_file(config_file_path(tmp_home))
    assert "observer_name = Jane Doe" in new_text


def test_virtual_horizon_configuration_writes_values(tmp_home, fresh_config):
    write_config_file(config_file_path(tmp_home), create_minimal_config_text())

    horizon = {"nord": "10", "south": "12", "east": "8", "west": "9"}
    cfg.virtual_horizon_configuration(fresh_config, horizon)

    new_text = read_config_file(config_file_path(tmp_home))
    assert "nord_altitude = 10" in new_text
    assert "south_altitude = 12" in new_text
    assert "east_altitude = 8" in new_text
    assert "west_altitude = 9" in new_text


def test_print_obs_config_outputs_expected(tmp_home, fresh_config, capsys):
    write_config_file(
        config_file_path(tmp_home),
        create_minimal_config_text(
            place="City", latitude="45.0", longitude="9.0", altitude="100.0",
            obs_name="MainObs", observer_name="John", mpc_code="A12"
        ),
    )

    cfg.print_obs_config(fresh_config)

    stdout = capsys.readouterr().out
    # Italian labels on purpose
    assert "Località: City" in stdout
    assert "Latitudine: 45.0" in stdout
    assert "Longitudine: 9.0" in stdout
    assert "Altitudine: 100.0" in stdout
    assert "Osservatore: John" in stdout
    assert "Nome Osservatorio: MainObs" in stdout
    assert "Codice MPC: A12" in stdout


def test_load_config_reads_existing_file(tmp_home, fresh_config, monkeypatch):
    # Pre-create file
    cfg_path = config_file_path(tmp_home)
    write_config_file(cfg_path, create_minimal_config_text(lang="en"))

    # Make os.walk yield an entry that contains .asteroidpy among files
    def fake_walk(_dir_path):
        yield ("/irrelevant", [], [".asteroidpy"])  # triggers read + break

    monkeypatch.setattr(os, "walk", fake_walk)

    cfg.load_config(fresh_config)
    assert fresh_config.get("General", "lang") == "en"


def test_load_config_initializes_when_missing(tmp_home, fresh_config, monkeypatch):
    # Stub initialize to avoid depending on its internal implementation
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

    monkeypatch.setattr(cfg, "initialize", fake_initialize)

    # os.walk that never finds the file; ensure at least 3 iterations so initialize is invoked
    def fake_walk(_dir_path):
        yield ("/a", ["b"], [])
        yield ("/a/b", ["c"], [])
        yield ("/a/b/c", [], [])  # at i==2 this triggers initialize

    monkeypatch.setattr(os, "walk", fake_walk)

    cfg.load_config(fresh_config)

    assert called["count"] >= 1
    # And the file should exist now
    assert os.path.exists(config_file_path(tmp_home))
