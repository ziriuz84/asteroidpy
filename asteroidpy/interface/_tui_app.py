"""Textual TUI entry point for AsteroidPY."""

from __future__ import annotations

from configparser import ConfigParser

from textual.app import App

from ._tui_screens import MainMenuScreen


class AsteroidApp(App[None]):
    """Root Textual application holding shared ``ConfigParser`` state."""

    TITLE = "AsteroidPY"

    BINDINGS = [("ctrl+q", "quit", "Quit")]

    CSS = """
    Screen {
        align: center middle;
    }
    #panel {
        width: 88%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    RichLog {
        height: 22;
        border: solid $accent;
        margin-top: 1;
    }
    ScrollableContainer RichLog {
        height: 1fr;
        min-height: 12;
    }
    Horizontal.input-row {
        height: auto;
        margin-bottom: 1;
    }
    Horizontal.input-row Label {
        width: 28;
        content-align: left middle;
    }
    Horizontal.input-row Input {
        width: 1fr;
    }
    """

    def __init__(self, config: ConfigParser) -> None:
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())


def run_textual_interface(config: ConfigParser) -> None:
    AsteroidApp(config).run()
