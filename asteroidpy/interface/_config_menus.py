"""Configuration-related interactive menus (observatory, general, language, horizon)."""

from __future__ import annotations

import os
import warnings
from configparser import ConfigParser
from typing import Dict

import asteroidpy.configuration as configuration

from ._i18n import get_locale_dir
from ._input import get_float, get_integer, prompt_int_in_range, prompt_line
from ._intl import translate


def change_obs_coords_menu(config: ConfigParser) -> None:
    place = prompt_line(translate("Locality -> "))
    latitude = get_float(translate("Latitude -> "))
    longitude = get_float(translate("Longitude -> "))
    configuration.change_obs_coords(config, place, latitude, longitude)


def change_obs_altitude_menu(config: ConfigParser) -> None:
    altitude = get_integer(translate("Altitude -> "))
    configuration.change_obs_altitude(config, altitude)


def change_observer_name_menu(config: ConfigParser) -> None:
    name = prompt_line(translate("Observer name -> "))
    configuration.change_observer_name(config, name)


def change_obs_name_menu(config: ConfigParser) -> None:
    name = prompt_line(translate("Observatory name -> "))
    configuration.change_obs_name(config, name)


def change_mpc_code_menu(config: ConfigParser) -> None:
    code = prompt_line(translate("MPC Code -> "))
    configuration.change_mpc_code(config, code)
    update_raw = prompt_line(translate("Update coordinates? (y/N) -> "))
    if update_raw.strip().lower() in {"y", "s", "yes"}:
        try:
            location = configuration.get_observatory_coordinates(code)
            configuration.change_obs_coords(
                config, location[3], location[1], location[0]
            )
            configuration.change_obs_name(config, location[3])
        except Exception:
            print(
                translate(
                    "Could not fetch observatory coordinates from the MPC "
                    "(check the code and your network connection)."
                )
            )


def print_observatory_config_menu() -> None:
    print(translate("""Choose an option
    1 - Change coordinates
    2 - Change altitude
    3 - Change the name of the observer
    4 - Change the name of the observatory
    5 - Change the MPC code
    6 - Change Virtual Horizon
    0 - Back to configuration menu"""))


def observatory_config_menu(config: ConfigParser) -> None:
    choice = -1
    while choice != 0:
        print(translate("Configuration -> Observatory"))
        print("==============================\n")
        configuration.print_obs_config(config)
        print_observatory_config_menu()
        choice = prompt_int_in_range(translate("choice -> "), 0, 6)
        print("\n\n\n\n\n")
        if choice == 1:
            change_obs_coords_menu(config)
        elif choice == 2:
            change_obs_altitude_menu(config)
        elif choice == 3:
            change_observer_name_menu(config)
        elif choice == 4:
            change_obs_name_menu(config)
        elif choice == 5:
            change_mpc_code_menu(config)
        elif choice == 6:
            change_horizon(config)


def change_language(config: ConfigParser) -> None:
    locale_dir = str(get_locale_dir())
    try:
        candidates = sorted(
            [
                d
                for d in os.listdir(locale_dir)
                if os.path.isdir(os.path.join(locale_dir, d))
            ]
        )
    except FileNotFoundError:
        candidates = ["en"]

    available_langs = []
    for code in candidates:
        lc_dir = os.path.join(locale_dir, code, "LC_MESSAGES")
        mo_path = os.path.join(lc_dir, "base.mo")
        po_path = os.path.join(lc_dir, "base.po")
        if os.path.exists(mo_path):
            available_langs.append(code)
        elif os.path.exists(po_path):
            warnings.warn(
                f"Locale '{code}' has a base.po but no compiled base.mo. "
                "Translation may not be available until compiled."
            )

    native_names = {
        "en": "English",
        "it": "Italiano",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "pt": "Português",
    }

    if "en" not in available_langs:
        available_langs.insert(0, "en")

    print(translate("Select a language"))
    for index, code in enumerate(available_langs, start=1):
        print(f"{index} - {native_names.get(code, code)}")

    choice = prompt_int_in_range(translate("Language -> "), 1, len(available_langs))

    lang = available_langs[choice - 1]
    configuration.change_language(config, lang)
    from ._i18n import setup_gettext

    setup_gettext(config)


def general_config_menu(config: ConfigParser) -> None:
    choice = -1
    while choice != 0:
        print(translate("Configuration -> General"))
        print("==============================")
        print("\n")
        print(translate("Choose a submenu"))
        print(translate("1 - Language"))
        print(translate("0 - Back to configuration menu"))
        choice = prompt_int_in_range(translate("choice -> "), 0, 1)
        print("\n\n\n\n\n")
        if choice == 1:
            change_language(config)


def config_menu(config: ConfigParser) -> None:
    choice = -1
    while choice != 0:
        print(translate("Configuration"))
        print("==============================")
        print("\n")
        print(translate("Choose a submenu"))
        print(translate("1 - General"))
        print(translate("2 - Observatory"))
        print(translate("0 - Back to main menu"))
        choice = prompt_int_in_range(translate("choice -> "), 0, 2)
        print("\n\n\n\n\n")
        if choice == 1:
            general_config_menu(config)
        elif choice == 2:
            observatory_config_menu(config)


def prompt_virtual_horizon_thresholds() -> Dict[str, str]:
    horizon: Dict[str, str] = {}
    horizon["nord"] = prompt_line(translate("Nord Altitude -> "))
    horizon["south"] = prompt_line(translate("South Altitude -> "))
    horizon["east"] = prompt_line(translate("East Altitude -> "))
    horizon["west"] = prompt_line(translate("West Altitude -> "))
    return horizon


def change_horizon(config: ConfigParser) -> None:
    horizon = prompt_virtual_horizon_thresholds()
    configuration.virtual_horizon_configuration(config, horizon)
