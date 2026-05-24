"""User-facing UI package: Textual terminal app, gettext, and legacy text menus.

The exported function ``interface`` loads gettext from the active config and
starts the Textual application (``asteroidpy.interface._tui_app``). ``main_menu``
plus the procedural helpers in ``_config_menus`` and ``_schedule_menus`` keep the
older ``print``/prompt workflows for tooling that imports them explicitly.
"""

from __future__ import annotations

from ._i18n import setup_gettext
from ._main import interface, main_menu

__all__ = ["interface", "main_menu", "setup_gettext"]
