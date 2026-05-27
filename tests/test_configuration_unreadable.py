from configparser import ConfigParser
from unittest.mock import patch

import platformdirs

import asteroidpy.configuration as cfg


def test_load_config_initializes_when_file_unreadable(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        platformdirs,
        "user_config_dir",
        lambda app_name, appauthor=False, **_kw: str(
            fake_home / ".config" / app_name
        ),
    )

    canon = fake_home / ".config" / cfg.APP_NAME / cfg.CONFIG_FILENAME
    canon.parent.mkdir(parents=True, exist_ok=True)
    canon.write_text("[General]\nlang = en\n", encoding="utf-8")

    config = ConfigParser()
    with patch.object(cfg, "_read_config_file", return_value=False):
        cfg.load_config(config)

    assert config.has_section("General")
    assert config.has_section("Observatory")
