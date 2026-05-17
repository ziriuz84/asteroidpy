"""Configuration persistence: INI file with platformdirs + legacy HOME migration."""

from __future__ import annotations

import logging
import math
import os
import shutil
import tempfile
from configparser import ConfigParser, Error as ConfigParserError
from pathlib import Path
from typing import Callable, Dict, Mapping, MutableMapping, TextIO, Tuple, TypedDict, Union

import platformdirs
from astroquery.mpc import MPC

logger = logging.getLogger(__name__)

APP_NAME = "asteroidpy"
CONFIG_FILENAME = ".asteroidpy"


class VirtualHorizonDegrees(TypedDict):
    """Per-direction minimum altitude thresholds in degrees as strings."""

    nord: str
    east: str
    south: str
    west: str


SECTION_DEFAULTS: Dict[str, Dict[str, str]] = {
    "General": {"lang": "en"},
    "Observatory": {
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
    },
}


def canonical_config_path() -> Path:
    """INI path under `user_config_dir` (e.g. ``~/.config/asteroidpy`` on Linux)."""

    root = Path(platformdirs.user_config_dir(APP_NAME, appauthor=False))
    return root / CONFIG_FILENAME


def legacy_config_path() -> Path:
    """Historical path: ``${HOME}/.asteroidpy`` (migration source only)."""

    return Path(os.path.expanduser("~")) / CONFIG_FILENAME


def _copy_if_needed(src: Path, dest: Path) -> bool:
    """Copy ``src`` to ``dest`` if ``src`` is a readable file. Return True if copied."""

    try:
        if not src.is_file():
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except OSError as exc:
        logger.debug(
            "Could not migrate legacy config from %s to %s: %s", src, dest, exc
        )
        return False
    logger.debug(
        "Copied legacy AsteroidPy config %s → %s (migrate to standard location).",
        src,
        dest,
    )
    return True


def _migrate_legacy_configuration() -> None:
    canon = canonical_config_path()
    if canon.exists():
        return
    _copy_if_needed(legacy_config_path(), canon)


def _read_config_file(parser: ConfigParser, path: Path) -> bool:
    """Read INI file into *parser*. Return False when missing, empty or unreadable."""

    try:
        parser.read(path, encoding="utf-8")
    except ConfigParserError:
        return False
    except UnicodeDecodeError:
        return False
    except OSError as exc:
        logger.debug("Config read failed for %s: %s", path, exc)
        return False
    # ConfigParser accepts non-INI text without raising but may yield no sections
    return bool(parser.sections())


def merge_missing_defaults(config: ConfigParser) -> None:
    """Ensure all known sections/options exist; fill missing entries from defaults."""

    for section_name, defaults in SECTION_DEFAULTS.items():
        if not config.has_section(section_name):
            config[section_name] = {}
        section: MutableMapping[str, str] = config[section_name]
        for opt, val in defaults.items():
            if not config.has_option(section_name, opt):
                section[opt] = val


def _invalidate_config(config: ConfigParser) -> None:
    for sec in list(config.sections()):
        config.remove_section(sec)


def _atomic_replace(path: Path, writer: Callable[[TextIO], None]) -> None:
    """Write INI atomically via temp file + os.replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{CONFIG_FILENAME}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except OSError:
        if tmp_path.is_file():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def save_config(config: ConfigParser) -> None:
    """Save configuration to disk (canonical path, atomic replace)."""

    def _writer(handle: TextIO) -> None:
        config.write(handle)

    _atomic_replace(canonical_config_path(), _writer)


def initialize(config: ConfigParser) -> None:
    """Reset configuration to built-in defaults and persist."""

    _invalidate_config(config)
    for sec, opts in SECTION_DEFAULTS.items():
        config[sec] = dict(opts)
    save_config(config)


def load_config(config: ConfigParser) -> None:
    """Load from canonical path, migrating ``~/.asteroidpy`` once if needed."""

    _migrate_legacy_configuration()

    canon = canonical_config_path()
    legacy = legacy_config_path()

    if canon.exists():
        ok = _read_config_file(config, canon)
        if ok:
            merge_missing_defaults(config)
            return
        initialize(config)
        return

    if legacy.exists():
        ok = _read_config_file(config, legacy)
        if ok:
            merge_missing_defaults(config)
            save_config(config)
            return
        initialize(config)
        return

    initialize(config)


def change_language(config: ConfigParser, lang: str) -> None:
    load_config(config)
    config["General"]["lang"] = lang
    save_config(config)


def change_obs_coords(
    config: ConfigParser, place: str, lat: float, longitude: float
) -> None:
    load_config(config)
    config["Observatory"]["place"] = place
    config["Observatory"]["latitude"] = str(lat)
    config["Observatory"]["longitude"] = str(longitude)
    save_config(config)


def change_obs_altitude(config: ConfigParser, alt: int) -> None:
    load_config(config)
    config["Observatory"]["altitude"] = str(alt)
    save_config(config)


def change_mpc_code(config: ConfigParser, code: str) -> None:
    load_config(config)
    config["Observatory"]["mpc_code"] = str(code)
    save_config(config)


def get_observatory_coordinates(code: str) -> Tuple[float, float, float, str]:
    """Look up MPC observatory longitude, latitude (deg), nominal altitude (0), and name.

    Raises exceptions from astroquery/network or ``ValueError`` for invalid codes.

    Latitude is reconstructed from MPC parallax coefficients ``rho*sin(phi')`` and
    ``rho*cos(phi')``; elevation is defaulted to sea level because the MPC list
    usually omits altitude.
    """

    result = MPC.get_observatory_location(code.strip())
    longitude_angle, cos_phi, sin_phi, name = result
    longitude_deg = float(longitude_angle.to_value("deg"))
    latitude_rad = math.atan2(float(sin_phi), float(cos_phi))
    latitude_deg = math.degrees(latitude_rad)
    altitude = 0.0
    return longitude_deg, latitude_deg, altitude, str(name)


def change_obs_name(config: ConfigParser, name: str) -> None:
    load_config(config)
    config["Observatory"]["obs_name"] = str(name)
    save_config(config)


def change_observer_name(config: ConfigParser, name: str) -> None:
    load_config(config)
    config["Observatory"]["observer_name"] = str(name)
    save_config(config)


def print_obs_config(config: ConfigParser, show_sensitive: bool = False) -> None:
    load_config(config)
    if not config.has_section("Observatory"):
        return
    if config.has_option("Observatory", "place"):
        print("Località: %s" % config["Observatory"]["place"])
    if config.has_option("Observatory", "latitude"):
        print(
            "Latitudine: %s"
            % (
                config["Observatory"]["latitude"]
                if show_sensitive
                else "***REDACTED***"
            )
        )
    if config.has_option("Observatory", "longitude"):
        print(
            "Longitudine: %s"
            % (
                config["Observatory"]["longitude"]
                if show_sensitive
                else "***REDACTED***"
            )
        )
    if config.has_option("Observatory", "altitude"):
        print(
            "Altitudine: %s"
            % (
                config["Observatory"]["altitude"]
                if show_sensitive
                else "***REDACTED***"
            )
        )
    if config.has_option("Observatory", "observer_name"):
        print("Osservatore: %s" % config["Observatory"]["observer_name"])
    if config.has_option("Observatory", "obs_name"):
        print("Nome Osservatorio: %s" % config["Observatory"]["obs_name"])
    if config.has_option("Observatory", "mpc_code"):
        print("Codice MPC: %s" % config["Observatory"]["mpc_code"])


def virtual_horizon_configuration(
    config: ConfigParser,
    horizon: Union[Mapping[str, str], VirtualHorizonDegrees],
) -> None:
    """Persist virtual horizon minima; ``horizon`` keys map to ``*_altitude`` entries.

    Use keys ``nord``, ``east``, ``south``, ``west`` (degrees). These correspond to
    the north / east / south / west altitude sectors and are stored as
    ``nord_altitude``, ``east_altitude``, ``south_altitude``, ``west_altitude``.
    """

    required = frozenset(VirtualHorizonDegrees.__annotations__.keys())
    missing = sorted(required - frozenset(horizon.keys()))
    if missing:
        raise KeyError(
            "horizon dict must contain keys nord, east, south, west; missing: "
            + ", ".join(missing)
        )

    load_config(config)
    config["Observatory"]["nord_altitude"] = str(horizon["nord"])
    config["Observatory"]["south_altitude"] = str(horizon["south"])
    config["Observatory"]["east_altitude"] = str(horizon["east"])
    config["Observatory"]["west_altitude"] = str(horizon["west"])
    save_config(config)
