"""Configuration persistence: INI file with platformdirs + legacy HOME migration."""

from __future__ import annotations

import logging
import math
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping, MutableMapping
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from pathlib import Path
from typing import TextIO, TypedDict

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


#: Placeholder printed in place of latitude, longitude and altitude when the
#: observatory summary is redacted.
REDACTED_PLACEHOLDER = "***REDACTED***"

#: ``(option, default label, sensitive)`` for every ``[Observatory]`` field shown by
#: :func:`observatory_summary_lines` and :func:`print_obs_config`, in display order.
#: Labels are msgid-style English: callers needing a localized UI pass translated
#: labels, the Textual one via ``asteroidpy.interface._intl.translate``.
OBSERVATORY_FIELD_LABELS: tuple[tuple[str, str, bool], ...] = (
    ("place", "Locality", False),
    ("latitude", "Latitude", True),
    ("longitude", "Longitude", True),
    ("altitude", "Altitude", True),
    ("observer_name", "Observer name", False),
    ("obs_name", "Observatory name", False),
    ("mpc_code", "MPC code", False),
)

#: Default value of every known INI section/option, applied by
#: :func:`merge_missing_defaults` so partial or older config files stay usable.
SECTION_DEFAULTS: dict[str, dict[str, str]] = {
    "General": {"lang": "en"},
    "Planner": {
        "max_nights": "5",
        "w_cloud": "0.4",
        "w_seeing": "0.25",
        "w_transparency": "0.15",
        "w_moon": "0.2",
    },
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
    """Persist the ``[General] lang`` UI language code (for example ``"it"``)."""

    load_config(config)
    config["General"]["lang"] = lang
    save_config(config)


def change_obs_coords(
    config: ConfigParser, place: str, lat: float, longitude: float
) -> None:
    """Persist observatory ``place``, ``latitude`` and ``longitude`` (decimal degrees)."""

    load_config(config)
    config["Observatory"]["place"] = place
    config["Observatory"]["latitude"] = str(lat)
    config["Observatory"]["longitude"] = str(longitude)
    save_config(config)


def change_obs_altitude(config: ConfigParser, alt: int) -> None:
    """Persist the observatory ``altitude`` in metres."""

    load_config(config)
    config["Observatory"]["altitude"] = str(alt)
    save_config(config)


def change_mpc_code(config: ConfigParser, code: str) -> None:
    """Persist the MPC observatory code used for MPC queries."""

    load_config(config)
    config["Observatory"]["mpc_code"] = str(code)
    save_config(config)


def get_observatory_coordinates(code: str) -> tuple[float, float, float, str]:
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
    """Persist the observatory site name shown in reports and headers."""

    load_config(config)
    config["Observatory"]["obs_name"] = str(name)
    save_config(config)


def change_observer_name(config: ConfigParser, name: str) -> None:
    """Persist the observer name shown in reports and headers."""

    load_config(config)
    config["Observatory"]["observer_name"] = str(name)
    save_config(config)


def observatory_summary_lines(
    config: ConfigParser,
    *,
    show_sensitive: bool = True,
    labels: Mapping[str, str] | None = None,
) -> list[str]:
    """Return the ``[Observatory]`` fields as ready-to-display ``label: value`` lines.

    *show_sensitive* defaults to ``True`` because this is the human-readable view:
    the interactive UI shows latitude, longitude and altitude in clear, since the
    user entered them and there is no log to leak them into. Pass ``False`` — or use
    :func:`print_obs_config`, the log-oriented entry point — to redact them.

    *labels* maps ``[Observatory]`` option names to display labels; options absent
    from the mapping fall back to the msgid-style defaults in
    :data:`OBSERVATORY_FIELD_LABELS`. This module is gettext-free by design, so the
    Textual UI passes labels already run through
    ``asteroidpy.interface._intl.translate``.
    """

    load_config(config)
    if not config.has_section("Observatory"):
        return []

    obs = config["Observatory"]
    chosen = labels or {}
    lines: list[str] = []
    for option, default_label, sensitive in OBSERVATORY_FIELD_LABELS:
        if not config.has_option("Observatory", option):
            continue
        label = chosen.get(option, default_label)
        value = obs[option]
        if sensitive and not show_sensitive:
            value = REDACTED_PLACEHOLDER
        lines.append(f"{label}: {value}")
    return lines


def print_obs_config(
    config: ConfigParser,
    show_sensitive: bool = False,
    *,
    labels: Mapping[str, str] | None = None,
) -> None:
    """Print the ``[Observatory]`` section to stdout, redacting sensitive fields.

    Coordinates and altitude are redacted unless *show_sensitive* is true, so the
    default output is safe to paste into public logs. For an unredacted, display-ready
    summary prefer :func:`observatory_summary_lines`.
    """

    for line in observatory_summary_lines(
        config, show_sensitive=show_sensitive, labels=labels
    ):
        print(line)


def virtual_horizon_configuration(
    config: ConfigParser,
    horizon: Mapping[str, str] | VirtualHorizonDegrees,
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
