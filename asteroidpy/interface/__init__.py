"""User-facing UI package: the Textual terminal app and its gettext setup.

The exported function ``interface`` loads gettext from the active config and
starts the Textual application (``asteroidpy.interface._tui_app``).
"""

from __future__ import annotations

from ._i18n import setup_gettext
from ._main import interface

__all__ = ["interface", "setup_gettext"]
