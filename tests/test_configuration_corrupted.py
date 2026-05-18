import os
from configparser import ConfigParser

import platformdirs

import asteroidpy.configuration as cfg


def test_load_config_initializes_when_file_corrupted(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda p: str(fake_home) if p == "~" else os.path.expanduser(p),
    )
    monkeypatch.setattr(
        platformdirs,
        "user_config_dir",
        lambda app_name, appauthor=False, **_kw: os.path.join(
            str(fake_home), ".config", app_name
        ),
    )

    canon = fake_home / ".config" / cfg.APP_NAME / cfg.CONFIG_FILENAME
    canon.parent.mkdir(parents=True, exist_ok=True)
    canon.write_text("not an INI file\nkey = value\n", encoding="utf-8")

    config = ConfigParser()
    cfg.load_config(config)

    assert config.has_section("General")
    assert config.has_section("Observatory")

    text = canon.read_text(encoding="utf-8")
    assert "[General]" in text
    assert "[Observatory]" in text
