import os
from configparser import ConfigParser
import pytest

import asteroidpy.configuration as cfg


def test_load_config_initializes_when_file_corrupted(tmp_path, monkeypatch):
    # Fake HOME
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda p: str(fake_home) if p == "~" else os.path.expanduser(p),
    )

    cfg_path = fake_home / ".asteroidpy"
    # Write invalid INI content (no section headers)
    cfg_path.write_text("not an INI file\nkey = value\n", encoding="utf-8")

    config = ConfigParser()
    cfg.load_config(config)

    # After fallback to initialize, config should have default sections
    assert config.has_section("General")
    assert config.has_section("Observatory")

    # And the file should have been (re)written with valid INI sections
    text = cfg_path.read_text(encoding="utf-8")
    assert "[General]" in text
    assert "[Observatory]" in text
