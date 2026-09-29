"""Application UI entry point."""

from __future__ import annotations

from configparser import ConfigParser

from ._i18n import setup_gettext
from ._tui_app import run_textual_interface


def interface(config: ConfigParser) -> None:
    """Start gettext from ``config``, then open the interactive Textual TUI."""
    setup_gettext(config)
    run_textual_interface(config)
