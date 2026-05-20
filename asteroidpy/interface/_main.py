"""Main menu and application UI entry."""

from __future__ import annotations

from configparser import ConfigParser

from asteroidpy.version import __version__

from ._config_menus import config_menu
from ._i18n import setup_gettext
from ._input import prompt_int_in_range
from ._intl import translate
from ._schedule_menus import scheduling_menu
from ._tui_app import run_textual_interface


def main_menu(config: ConfigParser) -> None:
    choice = -1
    while choice != 0:
        print(f"{translate('Welcome to AsteroidPY')} v. {__version__}")
        print("==============================")
        print("\n")
        print(translate("Choose a submenu"))
        print(translate("1 - Configuration"))
        print(translate("2 - Observation scheduling"))
        print(translate("0 - Exit"))
        choice = prompt_int_in_range(translate("choice -> "), 0, 2)
        print("\n\n\n\n\n")
        if choice == 1:
            config_menu(config)
        elif choice == 2:
            scheduling_menu(config)


def interface(config: ConfigParser) -> None:
    setup_gettext(config)
    run_textual_interface(config)
