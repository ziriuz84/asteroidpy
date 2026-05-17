"""Interactive command-line UI (menus, i18n, input helpers)."""

from __future__ import annotations

from ._i18n import setup_gettext
from ._main import interface, main_menu

__all__ = ["interface", "main_menu", "setup_gettext"]
