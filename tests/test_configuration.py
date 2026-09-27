import os
from configparser import ConfigParser

import platformdirs
import pytest

import asteroidpy.configuration as cfg


@pytest.fixture()
def tmp_home(monkeypatch, tmp_path):
    """Isolated HOME and platformdirs-style config layout under tmp_path."""

    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)

    original_expanduser = os.path.expanduser

    def fake_expanduser(path: str) -> str:
        return str(fake_home) if path == "~" else original_expanduser(path)

    monkeypatch.setattr(os.path, "expanduser", fake_expanduser)
    monkeypatch.setattr(
        platformdirs,
        "user_config_dir",
        lambda app_name, appauthor=False, **_kw: os.path.join(
            str(fake_home), ".config", app_name
        ),
    )

    return fake_home


@pytest.fixture()
def fresh_config() -> ConfigParser:
    return ConfigParser()


def config_file_canonical(home: os.PathLike) -> str:
    return os.fspath(
        home / ".config" / cfg.APP_NAME / cfg.CONFIG_FILENAME,
    )


def config_file_legacy(home: os.PathLike) -> str:
    return os.fspath(home / cfg.CONFIG_FILENAME)


def read_config_file(path: os.PathLike) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_config_file(path: os.PathLike, contents: str) -> None:
    p = os.fspath(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
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


def test_save_config_writes_file(tmp_home, fresh_config):
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

    path = config_file_canonical(tmp_home)
    assert os.path.exists(path)
    text = read_config_file(path)
    assert "[General]" in text and "[Observatory]" in text


def test_change_language_updates_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home), create_minimal_config_text(lang="en")
    )
    cfg.change_language(fresh_config, "it")

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "lang = it" in new_text


def test_change_obs_coords_updates_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(place="Old", latitude="1.0", longitude="2.0"),
    )

    cfg.change_obs_coords(fresh_config, place="NewPlace", lat=45.1, longitude=9.2)

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "place = NewPlace" in new_text
    assert "latitude = 45.1" in new_text
    assert "longitude = 9.2" in new_text


def test_change_obs_altitude_updates_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(altitude="0.0"),
    )

    cfg.change_obs_altitude(fresh_config, alt=123)

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "altitude = 123" in new_text


def test_change_mpc_code_updates_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(mpc_code="XXX"),
    )

    cfg.change_mpc_code(fresh_config, code="C10")

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "mpc_code = C10" in new_text


def test_change_obs_name_updates_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home), create_minimal_config_text(obs_name="")
    )

    cfg.change_obs_name(fresh_config, name="AstroObs")

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "obs_name = AstroObs" in new_text


def test_change_observer_name_updates_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(observer_name=""),
    )

    cfg.change_observer_name(fresh_config, name="Jane Doe")

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "observer_name = Jane Doe" in new_text


def test_virtual_horizon_configuration_writes_values(tmp_home, fresh_config):
    write_config_file(config_file_canonical(tmp_home), create_minimal_config_text())

    horizon = {"nord": "10", "south": "12", "east": "8", "west": "9"}
    cfg.virtual_horizon_configuration(fresh_config, horizon)

    new_text = read_config_file(config_file_canonical(tmp_home))
    assert "nord_altitude = 10" in new_text
    assert "south_altitude = 12" in new_text
    assert "east_altitude = 8" in new_text
    assert "west_altitude = 9" in new_text


def test_virtual_horizon_configuration_missing_key_raises(tmp_home, fresh_config):
    write_config_file(config_file_canonical(tmp_home), create_minimal_config_text())

    with pytest.raises(KeyError, match="nord"):
        cfg.virtual_horizon_configuration(
            fresh_config,
            {"east": "1", "south": "1", "west": "1"},
        )


def test_print_obs_config_redacts_sensitive_by_default(tmp_home, fresh_config, capsys):
    write_config_file(
        config_file_canonical(tmp_home),
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

    cfg.print_obs_config(fresh_config)

    stdout = capsys.readouterr().out
    assert "Locality: City" in stdout
    assert "Latitude: ***REDACTED***" in stdout
    assert "Longitude: ***REDACTED***" in stdout
    assert "Altitude: ***REDACTED***" in stdout
    assert "Observer name: John" in stdout
    assert "Observatory name: MainObs" in stdout
    assert "MPC code: A12" in stdout


def test_print_obs_config_shows_values_when_show_sensitive_true(
    tmp_home, fresh_config, capsys
):
    write_config_file(
        config_file_canonical(tmp_home),
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

    cfg.print_obs_config(fresh_config, show_sensitive=True)

    stdout = capsys.readouterr().out
    assert "Locality: City" in stdout
    assert "Latitude: 45.0" in stdout
    assert "Longitude: 9.0" in stdout
    assert "Altitude: 100.0" in stdout
    assert "Observer name: John" in stdout
    assert "Observatory name: MainObs" in stdout
    assert "MPC code: A12" in stdout


def test_print_obs_config_accepts_translated_labels(tmp_home, fresh_config, capsys):
    write_config_file(
        config_file_canonical(tmp_home), create_minimal_config_text(place="City")
    )

    cfg.print_obs_config(
        fresh_config,
        show_sensitive=True,
        labels={"place": "Località", "latitude": "Lat"},
    )

    stdout = capsys.readouterr().out
    assert "Località: City" in stdout
    assert "Lat: 0.0" in stdout
    # Options missing from *labels* keep the msgid-style default.
    assert "Observatory name: " in stdout


def test_print_obs_config_accepts_positional_show_sensitive(
    tmp_home, fresh_config, capsys
):
    """``show_sensitive`` stayed positional-or-keyword for existing callers."""
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(latitude="45.0"),
    )

    cfg.print_obs_config(fresh_config, True)

    assert "Latitude: 45.0" in capsys.readouterr().out


def test_observatory_summary_lines_shows_sensitive_by_default(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(
            place="City", latitude="45.0", longitude="9.0", altitude="100.0"
        ),
    )

    lines = cfg.observatory_summary_lines(fresh_config)

    assert "Latitude: 45.0" in lines
    assert "Longitude: 9.0" in lines
    assert "Altitude: 100.0" in lines


def test_observatory_summary_lines_redacts_when_not_show_sensitive(
    tmp_home, fresh_config
):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(
            place="City", latitude="45.0", longitude="9.0", altitude="100.0"
        ),
    )

    lines = cfg.observatory_summary_lines(fresh_config, show_sensitive=False)

    assert "Locality: City" in lines
    assert "Latitude: ***REDACTED***" in lines
    assert "Longitude: ***REDACTED***" in lines
    assert "Altitude: ***REDACTED***" in lines


def test_observatory_summary_lines_field_order_and_labels(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(
            place="City", latitude="45.0", obs_name="MainObs", mpc_code="A12"
        ),
    )

    lines = cfg.observatory_summary_lines(fresh_config)

    assert [line.split(":", 1)[0] for line in lines] == [
        default_label
        for _option, default_label, _sensitive in cfg.OBSERVATORY_FIELD_LABELS
    ]


def test_observatory_summary_lines_uses_supplied_labels(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(
            place="City", latitude="45.0", obs_name="MainObs", mpc_code="A12"
        ),
    )

    lines = cfg.observatory_summary_lines(
        fresh_config,
        labels={
            "place": "Località",
            "latitude": "Latitudine",
            "obs_name": "Nome Osservatorio",
            "mpc_code": "Codice MPC",
        },
    )

    assert "Località: City" in lines
    assert "Latitudine: 45.0" in lines
    assert "Nome Osservatorio: MainObs" in lines
    assert "Codice MPC: A12" in lines
    # Options missing from *labels* keep the msgid-style default.
    assert "Observer name: " in lines


def test_observatory_summary_lines_fills_missing_observatory_defaults(
    tmp_home, fresh_config
):
    """A config file without ``[Observatory]`` still yields the default summary."""
    write_config_file(config_file_canonical(tmp_home), "[General]\nlang = en\n")

    lines = cfg.observatory_summary_lines(fresh_config, show_sensitive=False)

    assert "Locality: " in lines
    assert f"Latitude: {cfg.REDACTED_PLACEHOLDER}" in lines


def test_tui_observatory_summary_renders_coordinates(tmp_home, fresh_config):
    """The Observatory screen shows the real values, not the redacted log dump."""
    pytest.importorskip("textual")
    from asteroidpy.interface._tui_screens import _observatory_summary

    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(
            place="City", latitude="45.0", longitude="9.0", altitude="100.0"
        ),
    )

    summary = _observatory_summary(fresh_config)

    assert "45.0" in summary
    assert "9.0" in summary
    assert "100.0" in summary
    assert cfg.REDACTED_PLACEHOLDER not in summary


def test_load_config_reads_existing_file(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(lang="en"),
    )

    cfg.load_config(fresh_config)
    assert fresh_config.get("General", "lang") == "en"


def test_load_config_merges_missing_defaults(tmp_home, fresh_config):
    write_config_file(
        config_file_canonical(tmp_home),
        create_minimal_config_text(),
    )
    cfg.load_config(fresh_config)
    assert fresh_config.get("Observatory", "nord_altitude") == "0"


def test_load_config_migrates_legacy_to_canonical(tmp_home, fresh_config):
    leg = config_file_legacy(tmp_home)
    write_config_file(leg, create_minimal_config_text(lang="it"))

    canon = config_file_canonical(tmp_home)
    assert not os.path.exists(canon)

    cfg.load_config(fresh_config)

    assert fresh_config.get("General", "lang") == "it"
    assert os.path.exists(canon)
    merged = read_config_file(canon)
    assert "[General]" in merged and "lang = it" in merged


def test_load_config_initializes_when_missing(tmp_home, fresh_config, monkeypatch):
    called = {"count": 0}

    def fake_initialize(conf: ConfigParser):
        called["count"] += 1
        for sec in list(conf.sections()):
            conf.remove_section(sec)
        for sec, defaults in cfg.SECTION_DEFAULTS.items():
            conf[sec] = dict(defaults)

        cfg.save_config(conf)

    monkeypatch.setattr(cfg, "initialize", fake_initialize)

    cfg.load_config(fresh_config)

    assert called["count"] >= 1
    assert os.path.exists(config_file_canonical(tmp_home))
