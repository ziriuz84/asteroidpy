"""Launch the Textual-based full-screen terminal UI for AsteroidPY.

Loads layout and widget rules from ``style.tcss`` (same package directory).
The parsed :class:`~configparser.ConfigParser` lives on ``app.config`` so
screens can reuse the caller's mutable configuration across the stack.
"""

from __future__ import annotations

from configparser import ConfigParser

from textual.app import App

from ._tui_screens import MainMenuScreen


class AsteroidApp(App[None]):
    """Root Textual app carrying the shared observatory/program configuration."""

    #: Path to stylesheet next to this module (see ``CSS_PATH`` in Textual's ``App``).
    CSS_PATH = "style.tcss"

    #: Window / terminal title shown by the environment when supported.
    TITLE = "AsteroidPY"

    #: Quit from any nested screen unless a child binds the same chord differently.
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(self, config: ConfigParser) -> None:
        """Attach the CLI-loaded config bundle for downstream screens."""
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        """Seed the navigation stack at the translated main menu."""
        self.push_screen(MainMenuScreen())


def run_textual_interface(config: ConfigParser) -> None:
    """Block until the user exits; ``config`` is read/written by menu actions."""
    AsteroidApp(config).run()
