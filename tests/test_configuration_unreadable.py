import os
import stat
from configparser import ConfigParser
import pytest

import asteroidpy.configuration as cfg


def test_load_config_initializes_when_file_unreadable(tmp_path, monkeypatch):
    # Fake HOME
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(fake_home) if p == "~" else os.path.expanduser(p))

    cfg_path = fake_home / ".asteroidpy"
    cfg_path.write_text("[General]\nlang = en\n", encoding="utf-8")

    # Remove read permission
    cfg_path.chmod(stat.S_IWUSR)

    config = ConfigParser()
    cfg.load_config(config)

    # After fallback to initialize, file should be recreated and readable
    assert os.path.exists(cfg_path)
    # The config should contain the default sections from initialize
    assert config.has_section("General")
    assert config.has_section("Observatory")
