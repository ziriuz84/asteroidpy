"""Observation scheduling menus (weather, target lists, NEOcp, ephemerides, twilight)."""

from __future__ import annotations

import datetime
from configparser import ConfigParser
from typing import List

import asteroidpy.configuration as configuration
import asteroidpy.scheduling as scheduling

from ._input import get_float, get_integer, prompt_int_in_range, prompt_line
from ._intl import translate


def local_coordinates(config: ConfigParser) -> List[str]:
    configuration.load_config(config)
    latitude = config["Observatory"]["latitude"]
    longitude = config["Observatory"]["longitude"]
    return [latitude, longitude]


def select_specific_time() -> datetime.datetime:
    print(translate("Provide me with the observation start time parameters (UTC)"))
    while True:
        day = get_integer(translate("Day -> "))
        month = get_integer(translate("Month -> "))
        year = get_integer(translate("Year -> "))
        hour = get_integer(translate("Hour -> "))
        minutes = get_integer(translate("Minutes -> "))
        seconds = get_integer(translate("Seconds -> "))
        try:
            return datetime.datetime(year, month, day, hour, minutes, seconds)
        except ValueError:
            print(
                translate(
                    "Invalid date or time (check day/month ranges and hour 0–23); "
                    "please try again."
                )
            )


def observing_target_list_menu(config: ConfigParser) -> None:
    authenticity_token, used_fallback = scheduling.resolve_whatsup_authenticity_token()
    if used_fallback:
        print(
            translate(
                "Could not load a fresh MPC form token from the What's Observable page; "
                "using an embedded fallback. The request might fail."
            )
        )

    coordinates = local_coordinates(config)
    select_raw = prompt_line(
        translate("Do you want to know the asteroids visible right now? [y/N]")
    )
    yn = select_raw.strip().lower()
    if yn in {"s", "y", "yes"}:
        utc_now = datetime.datetime.now(datetime.UTC)
        observation_time = datetime.datetime(
            utc_now.year,
            utc_now.month,
            utc_now.day,
            utc_now.hour,
            utc_now.minute,
            utc_now.second,
        )
    else:
        observation_time = select_specific_time()
    duration = get_integer(translate("Duration of observation (hours, max 12) -> "))
    solar_elongation = get_integer(translate("Minimal solar elongation -> "))
    lunar_elongation = get_integer(translate("Minimal lunar elongation -> "))
    minimal_height = get_integer(translate("Minimal altitude-> "))
    max_objects = get_integer(translate("Maximum number of objects -> "))
    object_request = prompt_int_in_range(
        translate(
            "Select type of object\n1 - Asteroids\n2 - NEAs\n3 - Comets\nChoice -> "
        ),
        1,
        3,
    )
    if object_request == 2:
        object_type = "neo"
    elif object_request == 3:
        object_type = "cmt"
    else:
        object_type = "mp"
    payload = {
        "utf8": "%E2%9C%93",
        "authenticity_token": authenticity_token,
        "latitude": coordinates[0],
        "longitude": coordinates[1],
        "year": observation_time.year,
        "month": observation_time.month,
        "day": observation_time.day,
        "hour": observation_time.hour,
        "minute": observation_time.minute,
        "duration": duration,
        "max_objects": max_objects,
        "min_alt": minimal_height,
        "solar_elong": solar_elongation,
        "lunar_elong": lunar_elongation,
        "object_type": object_type,
        "submit": "Submit",
    }
    target_list = scheduling.observing_target_list(config, payload)
    browser_view = prompt_line(translate("Do you want to view in Browser? (y/N) -> "))
    if browser_view.strip().lower() in {"y", "yes"}:
        target_list.show_in_browser(jsviewer=True)
    else:
        print(target_list)
    print("\n\n\n\n")


def neocp_confirmation_menu(config: ConfigParser) -> None:
    min_score = get_integer(translate("Minimum score -> "))
    max_magnitude = get_float(translate("Maximum magnitude -> "))
    min_altitude = get_integer(translate("Minimum altitude -> "))
    browser_view = prompt_line(translate("Do you want to view in Browser? (y/N) -> "))
    neocp = scheduling.neocp_confirmation(
        config, min_score, max_magnitude, min_altitude
    )
    if browser_view.strip().lower() in {"y", "yes"}:
        neocp.show_in_browser(jsviewer=True)
    else:
        print(neocp)
    print("\n\n\n\n")


def twilight_sun_moon_menu(config: ConfigParser) -> None:
    result_times = scheduling.twilight_times(config)
    tfmt = "%H:%M:%S"
    print(
        translate("Civil twilight: {m} – {e}").format(
            m=result_times["CivilM"].strftime(tfmt),
            e=result_times["CivilE"].strftime(tfmt),
        )
    )
    print(
        translate("Nautical twilight: {m} – {e}").format(
            m=result_times["NautiM"].strftime(tfmt),
            e=result_times["NautiE"].strftime(tfmt),
        )
    )
    print(
        translate("Astronomical twilight: {m} – {e}").format(
            m=result_times["AstroM"].strftime(tfmt),
            e=result_times["AstroE"].strftime(tfmt),
        )
    )
    print("\n")
    ephemeris = scheduling.sun_moon_ephemeris(config)
    print(translate("Sunrise: {t}").format(t=ephemeris["Sunrise"].strftime(tfmt)))
    print(translate("Sunset: {t}").format(t=ephemeris["Sunset"].strftime(tfmt)))
    print(translate("Moonrise: {t}").format(t=ephemeris["Moonrise"].strftime(tfmt)))
    print(translate("Moonset: {t}").format(t=ephemeris["Moonset"].strftime(tfmt)))
    print(translate("Moon illumination: {f}").format(f=ephemeris["MoonIll"]))
    print("\n\n\n\n")


def print_scheduling_menu() -> None:
    print(translate("Observation scheduling"))
    print("==============================\n")
    print(translate("""Choose a submenu
    1 - Weather forecast
    2 - Observing target List
    3 - NEOcp list
    4 - Object Ephemeris
    5 - Twilight Times
    0 - Back to main menu\n"""))


def object_ephemeris_menu(config: ConfigParser) -> None:
    object_name = prompt_line(translate("Object Name -> "))
    print(translate("""Stepping
    m - 1 minute
    h - 1 hour
    d - 1 day
    w - 1 week
    """))
    while True:
        step = prompt_line(translate("Choice -> ")).strip().lower()
        if step in {"m", "h", "d", "w"}:
            break
        print(translate("Invalid choice — enter m, h, d, or w."))
    ephemeris_table = scheduling.object_ephemeris(config, object_name, step)
    print(ephemeris_table)


def scheduling_menu(config: ConfigParser) -> None:
    choice = -1
    while choice != 0:
        print_scheduling_menu()
        choice = prompt_int_in_range(translate("choice -> "), 0, 5)
        print("\n\n\n\n\n")
        if choice == 1:
            scheduling.weather(config)
        elif choice == 2:
            observing_target_list_menu(config)
        elif choice == 3:
            neocp_confirmation_menu(config)
        elif choice == 4:
            object_ephemeris_menu(config)
        elif choice == 5:
            twilight_sun_moon_menu(config)
