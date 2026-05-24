"""Textual screens replacing legacy ``print`` / ``input`` menus.

Layout rules load from ``style.tcss`` via the root application in ``_tui_app``.

Behaviour notes for maintainers:

* **Observatory summary** — :class:`ObservatoryScreen` refreshes the read-only
  summary on mount and on :class:`~textual.events.ScreenResume` so edits from
  pushed child screens are visible after ``pop_screen``.
* **Locale catalogs** — :func:`_collect_language_codes_and_catalog_warnings`
  lists languages with a compiled ``base.mo``; ``.po``-only trees produce
  backlog strings shown from :class:`LanguageScreen` via ``app.notify`` (no
  ``warnings.warn`` on stderr).
* **MPC What's Observable** — :class:`ObservingTargetListScreen` clamps numeric
  form fields to safe ranges before building the POST payload (see module-level
  ``_MPC_*`` constants).
"""

from __future__ import annotations

import asyncio
import datetime
import io
import os
from configparser import ConfigParser
from contextlib import redirect_stdout
from typing import Any, List, Tuple, cast

from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
)
from textual.worker import WorkerFailed

import asteroidpy.configuration as configuration
import asteroidpy.scheduling as scheduling
from asteroidpy.version import __version__

from ._i18n import setup_gettext
from ._intl import translate


def _app_config(screen: Screen) -> ConfigParser:
    """Return the mutable :class:`~configparser.ConfigParser` held on ``screen.app``.

    Expects ``AsteroidApp`` (or compatible) with ``.config``.
    """
    return cast(ConfigParser, getattr(screen.app, "config"))


def _refresh_main_menu_after_locale(screen: Screen) -> None:
    """Drop nested screens after a locale change so labels pick up gettext."""
    app = screen.app
    # Do not unwind to the bare ``_default`` shell: popping until ``len == 1`` removes
    # ``MainMenuScreen`` too, and ``switch_screen`` on ``_default`` raises IndexError on
    # empty ``_result_callbacks``. Pop until we're on the existing main menu, drop it,
    # then mount a fresh translated instance under the shell.
    while not isinstance(app.screen, MainMenuScreen):
        if len(app.screen_stack) <= 1:
            break
        app.pop_screen()
    if isinstance(app.screen, MainMenuScreen):
        app.pop_screen()
    app.push_screen(MainMenuScreen())


def _observatory_summary(config: ConfigParser) -> str:
    """Capture ``configuration.print_obs_config`` stdout as plain text."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        configuration.print_obs_config(config)
    return buf.getvalue().strip()


_MPC_WHATSUP_DURATION_H_MIN = 1
_MPC_WHATSUP_DURATION_H_MAX = 12
_MPC_ELONGATION_DEG_MIN = 0
_MPC_ELONGATION_DEG_MAX = 180
_MPC_MIN_ALT_DEG_MIN = 0
_MPC_MIN_ALT_DEG_MAX = 90
_MPC_MAX_OBJECTS_MIN = 1
_MPC_MAX_OBJECTS_MAX = 1000


def _collect_language_codes_and_catalog_warnings() -> Tuple[List[str], List[str]]:
    """Return installed UI language codes plus optional catalog backlog messages.

    First element: subdirectory names under ``locales/`` whose ``LC_MESSAGES``
    folder contains ``base.mo`` (selectable in :class:`LanguageScreen`). ``en`` is
    prepended when absent.

    Second element: one user-facing message (already passed through ``translate()`` from
    ``._intl``) per locale that has ``base.po`` but no compiled ``base.mo``. Those strings are
    meant for Textual notifications (see ``LanguageScreen.on_mount``), not ``warnings.warn``.

    Ensures ``en`` appears when no ``locales`` tree exists or it is unreadable.
    """
    locale_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "locales")
    )
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

    available_langs: List[str] = []
    backlog: List[str] = []
    for code in candidates:
        lc_dir = os.path.join(locale_dir, code, "LC_MESSAGES")
        mo_path = os.path.join(lc_dir, "base.mo")
        po_path = os.path.join(lc_dir, "base.po")
        if os.path.exists(mo_path):
            available_langs.append(code)
        elif os.path.exists(po_path):
            backlog.append(
                translate(
                    "Locale '{code}' has base.po but no compiled base.mo; "
                    "translation may not be available until catalogs are compiled."
                ).format(code=code)
            )

    if "en" not in available_langs:
        available_langs.insert(0, "en")

    return available_langs, backlog


class MainMenuScreen(Screen):
    """Top-level menu: configuration, scheduling, or exit."""

    BINDINGS = [Binding("ctrl+q", "quit", "Quit")]

    def compose(self) -> Any:
        yield Header(show_clock=True)
        yield Footer()
        yield Vertical(
            Label(
                f"{translate('Welcome to AsteroidPY')} v{__version__}",
                id="welcome",
            ),
            Button(translate("1 - Configuration"), id="cfg"),
            Button(translate("2 - Observation scheduling"), id="sch"),
            Button(translate("0 - Exit"), id="exit", variant="error"),
            id="panel",
        )

    def action_quit(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cfg":
            self.app.push_screen(ConfigRootScreen())
        elif event.button.id == "sch":
            self.app.push_screen(SchedulingRootScreen())
        elif event.button.id == "exit":
            self.app.exit()


class ConfigRootScreen(Screen):
    """Configuration branch: general options or observatory details."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Configuration")),
            Button(translate("1 - General"), id="general"),
            Button(translate("2 - Observatory"), id="obs"),
            Button(translate("0 - Back to main menu"), id="back"),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "general":
            self.app.push_screen(GeneralConfigScreen())
        elif event.button.id == "obs":
            self.app.push_screen(ObservatoryScreen())
        elif event.button.id == "back":
            self.app.pop_screen()


class GeneralConfigScreen(Screen):
    """General settings submenu (currently language selection)."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Configuration -> General")),
            Button(translate("1 - Language"), id="lang"),
            Button(translate("0 - Back to configuration menu"), id="back"),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lang":
            self.app.push_screen(LanguageScreen())
        elif event.button.id == "back":
            self.app.pop_screen()


class LanguageScreen(Screen):
    """Pick UI language from installed gettext catalogs and refresh gettext.

    On mount, surfaces one notification per locale directory that has ``base.po`` but
    no compiled ``base.mo`` (see :func:`_collect_language_codes_and_catalog_warnings`).
    """

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        codes, self._locale_catalog_warnings = (
            _collect_language_codes_and_catalog_warnings()
        )
        native_names = {
            "en": "English",
            "it": "Italiano",
            "de": "Deutsch",
            "fr": "Français",
            "es": "Español",
            "pt": "Português",
        }
        current = _app_config(self).get("General", "lang", fallback="en")
        buttons = [
            Button(
                native_names.get(code, code),
                id=f"pick-{code}",
                variant="primary" if code == current else "default",
            )
            for code in codes
        ]
        yield Vertical(
            Label(translate("Select a language")),
            *buttons,
            Button(translate("0 - Back"), id="back"),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_mount(self) -> None:
        for msg in self._locale_catalog_warnings:
            self.app.notify(msg, severity="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "back":
            self.app.pop_screen()
            return
        if bid.startswith("pick-"):
            lang = bid.partition("-")[2]
            configuration.change_language(_app_config(self), lang)
            setup_gettext(_app_config(self))
            self.app.notify(translate("Language updated."))
            _refresh_main_menu_after_locale(self)


class ObservatoryScreen(Screen):
    """Read-only observatory summary plus shortcuts to editable fields.

    The summary text is recomputed when the screen mounts and whenever it becomes
    active again (``ScreenResume``) so values changed on pushed edit screens stay in sync.
    """

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        cfg = _app_config(self)
        summary = _observatory_summary(cfg) or translate("(No observatory section)")
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Configuration -> Observatory")),
            Static(summary, id="obs_summary"),
            Button(translate("1 - Change coordinates"), id="c_coords"),
            Button(translate("2 - Change altitude"), id="c_alt"),
            Button(translate("3 - Change the name of the observer"), id="c_observer"),
            Button(translate("4 - Change the name of the observatory"), id="c_obsname"),
            Button(translate("5 - Change the MPC code"), id="c_mpc"),
            Button(translate("6 - Change Virtual Horizon"), id="c_horizon"),
            Button(translate("0 - Back to configuration menu"), id="back"),
            id="panel",
        )

    def on_mount(self) -> None:
        self._refresh_observatory_summary()

    def on_screen_resume(self, _event: ScreenResume) -> None:
        self._refresh_observatory_summary()

    def _refresh_observatory_summary(self) -> None:
        cfg = _app_config(self)
        summary = _observatory_summary(cfg) or translate("(No observatory section)")
        self.query_one("#obs_summary", Static).update(summary)

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        pushed = {
            "c_coords": ObservatoryCoordsScreen,
            "c_alt": ObservatoryAltitudeScreen,
            "c_observer": ObservatoryObserverScreen,
            "c_obsname": ObservatoryObservatoryNameScreen,
            "c_mpc": ObservatoryMpcScreen,
            "c_horizon": ObservatoryHorizonScreen,
        }
        bid = event.button.id or ""
        if bid == "back":
            self.app.pop_screen()
        elif bid in pushed:
            self.app.push_screen(pushed[bid]())


class ObservatoryCoordsScreen(Screen):
    """Edit locality name and latitude/longitude in the config.

    Fields load existing ``Observatory`` values on mount so partial edits do not blank untouched keys.
    """

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Change coordinates")),
            Horizontal(
                Label(translate("Locality -> ")),
                Input(placeholder="", id="place"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("Latitude -> ")),
                Input(placeholder="", id="latitude"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("Longitude -> ")),
                Input(placeholder="", id="longitude"),
                classes="input-row",
            ),
            Horizontal(
                Button(translate("Save"), id="save", variant="primary"),
                Button(translate("Cancel"), id="cancel"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_mount(self) -> None:
        cfg = _app_config(self)
        place = lat_s = lon_s = ""
        if cfg.has_section("Observatory"):
            obs = cfg["Observatory"]
            place = (obs.get("place") or "").strip()
            lat_s = (obs.get("latitude") or "").strip()
            lon_s = (obs.get("longitude") or "").strip()
        self.query_one("#place", Input).value = place
        self.query_one("#latitude", Input).value = lat_s
        self.query_one("#longitude", Input).value = lon_s

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id != "save":
            return
        place = self.query_one("#place", Input).value.strip()
        try:
            lat = float(self.query_one("#latitude", Input).value.strip())
            lon = float(self.query_one("#longitude", Input).value.strip())
        except ValueError:
            self.app.notify(translate("You must enter a number."), severity="warning")
            return
        configuration.change_obs_coords(_app_config(self), place, lat, lon)
        self.app.pop_screen()


class ObservatoryAltitudeScreen(Screen):
    """Set observatory altitude (meters) as an integer."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Change altitude")),
            Horizontal(
                Label(translate("Altitude -> ")),
                Input(placeholder="", id="altitude"),
                classes="input-row",
            ),
            Horizontal(
                Button(translate("Save"), id="save", variant="primary"),
                Button(translate("Cancel"), id="cancel"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id != "save":
            return
        try:
            alt = int(self.query_one("#altitude", Input).value.strip())
        except ValueError:
            self.app.notify(translate("You must enter an integer."), severity="warning")
            return
        configuration.change_obs_altitude(_app_config(self), alt)
        self.app.pop_screen()


class ObservatoryObserverScreen(Screen):
    """Change the observer name stored in configuration."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Change observer")),
            Horizontal(
                Label(translate("Observer name -> ")),
                Input(placeholder="", id="name"),
                classes="input-row",
            ),
            Horizontal(
                Button(translate("Save"), id="save", variant="primary"),
                Button(translate("Cancel"), id="cancel"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id != "save":
            return
        name = self.query_one("#name", Input).value.strip()
        configuration.change_observer_name(_app_config(self), name)
        self.app.pop_screen()


class ObservatoryObservatoryNameScreen(Screen):
    """Rename the observatory/site string in configuration."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Change observatory name")),
            Horizontal(
                Label(translate("Observatory name -> ")),
                Input(placeholder="", id="name"),
                classes="input-row",
            ),
            Horizontal(
                Button(translate("Save"), id="save", variant="primary"),
                Button(translate("Cancel"), id="cancel"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id != "save":
            return
        name = self.query_one("#name", Input).value.strip()
        configuration.change_obs_name(_app_config(self), name)
        self.app.pop_screen()


class ObservatoryMpcScreen(Screen):
    """Assign MPC observatory code; optionally pull coords/name from MPC data."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Change MPC code")),
            Horizontal(
                Label(translate("MPC Code -> ")),
                Input(placeholder="", id="code"),
                classes="input-row",
            ),
            Checkbox(
                translate("Update coordinates?"),
                id="upd_coords",
            ),
            Horizontal(
                Button(translate("Save"), id="save", variant="primary"),
                Button(translate("Cancel"), id="cancel"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id != "save":
            return
        code = self.query_one("#code", Input).value.strip()
        configuration.change_mpc_code(_app_config(self), code)
        if self.query_one("#upd_coords", Checkbox).value:
            try:
                location = configuration.get_observatory_coordinates(code)
                configuration.change_obs_coords(
                    _app_config(self), location[3], location[1], location[0]
                )
                configuration.change_obs_name(_app_config(self), location[3])
            except Exception:
                self.app.notify(
                    translate(
                        "Could not fetch observatory coordinates from the MPC "
                        "(check the code and your network connection)."
                    ),
                    severity="warning",
                )
        self.app.pop_screen()


class ObservatoryHorizonScreen(Screen):
    """Configure cardinal virtual-horizon strings (north/south/east/west)."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Virtual horizon")),
            Horizontal(
                Label(translate("Nord Altitude -> ")),
                Input(placeholder="", id="nord"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("South Altitude -> ")),
                Input(placeholder="", id="south"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("East Altitude -> ")),
                Input(placeholder="", id="east"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("West Altitude -> ")),
                Input(placeholder="", id="west"),
                classes="input-row",
            ),
            Horizontal(
                Button(translate("Save"), id="save", variant="primary"),
                Button(translate("Cancel"), id="cancel"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id != "save":
            return
        horizon = {
            "nord": self.query_one("#nord", Input).value.strip(),
            "south": self.query_one("#south", Input).value.strip(),
            "east": self.query_one("#east", Input).value.strip(),
            "west": self.query_one("#west", Input).value.strip(),
        }
        configuration.virtual_horizon_configuration(_app_config(self), horizon)
        self.app.pop_screen()


class SchedulingRootScreen(Screen):
    """Hub for forecasting, MPC lists, ephemerides, twilight computations."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Observation scheduling")),
            Button(translate("1 - Weather forecast"), id="w"),
            Button(translate("2 - Observing target List"), id="targets"),
            Button(translate("3 - NEOcp list"), id="neocp"),
            Button(translate("4 - Object Ephemeris"), id="eph"),
            Button(translate("5 - Twilight Times"), id="twilight"),
            Button(translate("0 - Back to main menu"), id="back"),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        pushed = {
            "w": WeatherScreen,
            "targets": ObservingTargetListScreen,
            "neocp": NeocpScreen,
            "eph": EphemerisScreen,
            "twilight": TwilightScreen,
        }
        bid = event.button.id or ""
        if bid == "back":
            self.app.pop_screen()
        elif bid in pushed:
            self.app.push_screen(pushed[bid]())


class WeatherScreen(Screen):
    """Runs ``weather_forecast_report`` off the UI thread into a Rich log."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Weather forecast")),
            Button(translate("Fetch forecast"), id="run", variant="primary"),
            RichLog(id="log", wrap=True, highlight=True),
            Button(translate("0 - Back"), id="back"),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "run":
            await self._do_fetch()

    async def _do_fetch(self) -> None:
        """Load forecast text asynchronously so the worker cannot block repaint."""
        log = self.query_one("#log", RichLog)
        btn = self.query_one("#run", Button)
        log.clear()
        btn.disabled = True
        try:
            report = await asyncio.to_thread(
                scheduling.weather_forecast_report,
                _app_config(self),
            )
            log.write(report)
        finally:
            btn.disabled = False


class ObservingTargetListScreen(Screen):
    """What's Observable-style form with scrollable fields and MPC POST payload.

    Integer fields are clamped to documented ranges (module ``_MPC_*`` constants) before
    the request; the user gets a warning notification when a value is adjusted.
    """

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield ScrollableContainer(
            Vertical(
                Label(translate("Observing target list")),
                Checkbox(
                    translate('Use observation time "now" (UTC)'),
                    id="use_now",
                ),
                Label(translate('Start time (UTC) if not "now"')),
                Horizontal(
                    Label(translate("Day")),
                    Input(placeholder="DD", id="day"),
                    Label(translate("Month")),
                    Input(placeholder="MM", id="month"),
                    Label(translate("Year")),
                    Input(placeholder="YYYY", id="year"),
                    classes="input-row",
                ),
                Horizontal(
                    Label(translate("Hour")),
                    Input(placeholder="0-23", id="hour"),
                    Label(translate("Minutes")),
                    Input(placeholder="0-59", id="minute"),
                    Label(translate("Seconds")),
                    Input(placeholder="0-59", id="second"),
                    classes="input-row",
                ),
                Horizontal(
                    Label(translate("Duration of observation (hours, max 12) -> ")),
                    Input(placeholder="1-12", id="duration"),
                    classes="input-row",
                ),
                Horizontal(
                    Label(translate("Minimal solar elongation -> ")),
                    Input(placeholder="0-180", id="solar_elong"),
                    classes="input-row",
                ),
                Horizontal(
                    Label(translate("Minimal lunar elongation -> ")),
                    Input(placeholder="0-180", id="lunar_elong"),
                    classes="input-row",
                ),
                Horizontal(
                    Label(translate("Minimal altitude-> ")),
                    Input(placeholder="0-90", id="min_alt"),
                    classes="input-row",
                ),
                Horizontal(
                    Label(translate("Maximum number of objects -> ")),
                    Input(placeholder="1-1000", id="max_objects"),
                    classes="input-row",
                ),
                Select(
                    (
                        (translate("Asteroids"), "mp"),
                        (translate("NEAs"), "neo"),
                        (translate("Comets"), "cmt"),
                    ),
                    allow_blank=False,
                    value="mp",
                    id="object_type",
                ),
                Checkbox(
                    translate("Open result in browser"),
                    id="browser",
                ),
                Horizontal(
                    Button(translate("Run"), id="run", variant="primary"),
                    Button(translate("0 - Back"), id="back"),
                ),
                id="inner",
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "run":
            await self._do_run()

    async def _do_run(self) -> None:
        """Resolve token/coords, clamp form integers to MPC-safe ranges, POST, optionally open browser.

        Integer fields (#duration, elongations, min altitude, max objects) are constrained
        against module-level ``_MPC_*`` limits with user notifications when clamping occurs.
        """
        cfg = _app_config(self)
        btn = self.query_one("#run", Button)
        btn.disabled = True
        try:
            authenticity_token, used_fallback = await asyncio.to_thread(
                scheduling.resolve_whatsup_authenticity_token
            )
            if used_fallback:
                self.app.notify(
                    translate(
                        "Could not load a fresh MPC form token from the What's Observable page; "
                        "using an embedded fallback. The request might fail."
                    ),
                    severity="warning",
                )

            coordinates = await asyncio.to_thread(_local_coordinates, cfg)
            use_now = self.query_one("#use_now", Checkbox).value
            if use_now:
                utc_now = datetime.datetime.now(datetime.timezone.utc)
                observation_time = datetime.datetime(
                    utc_now.year,
                    utc_now.month,
                    utc_now.day,
                    utc_now.hour,
                    utc_now.minute,
                    utc_now.second,
                )
            else:
                try:
                    observation_time = _parse_datetime_inputs(self)
                except ValueError:
                    self.app.notify(
                        translate(
                            "Invalid date or time (check day/month ranges and hour 0–23); "
                            "please try again."
                        ),
                        severity="warning",
                    )
                    return

            try:
                raw_duration = int(self.query_one("#duration", Input).value.strip())
                raw_solar_elongation = int(
                    self.query_one("#solar_elong", Input).value.strip()
                )
                raw_lunar_elongation = int(
                    self.query_one("#lunar_elong", Input).value.strip()
                )
                raw_min_alt = int(self.query_one("#min_alt", Input).value.strip())
                raw_max_objects = int(
                    self.query_one("#max_objects", Input).value.strip()
                )
            except ValueError:
                self.app.notify(
                    translate("You must enter an integer."), severity="warning"
                )
                return

            duration = raw_duration
            if (
                duration < _MPC_WHATSUP_DURATION_H_MIN
                or duration > _MPC_WHATSUP_DURATION_H_MAX
            ):
                duration = max(
                    _MPC_WHATSUP_DURATION_H_MIN,
                    min(raw_duration, _MPC_WHATSUP_DURATION_H_MAX),
                )
                self.app.notify(
                    translate(
                        "Duration of observation must be between 1 and 12 hours; "
                        "using {hours} hour(s)."
                    ).format(hours=duration),
                    severity="warning",
                )

            solar_elongation = raw_solar_elongation
            if (
                solar_elongation < _MPC_ELONGATION_DEG_MIN
                or solar_elongation > _MPC_ELONGATION_DEG_MAX
            ):
                solar_elongation = max(
                    _MPC_ELONGATION_DEG_MIN,
                    min(raw_solar_elongation, _MPC_ELONGATION_DEG_MAX),
                )
                self.app.notify(
                    translate(
                        "Minimal solar elongation must be between {low}° and {high}°; "
                        "using {degrees}°."
                    ).format(
                        low=_MPC_ELONGATION_DEG_MIN,
                        high=_MPC_ELONGATION_DEG_MAX,
                        degrees=solar_elongation,
                    ),
                    severity="warning",
                )

            lunar_elongation = raw_lunar_elongation
            if (
                lunar_elongation < _MPC_ELONGATION_DEG_MIN
                or lunar_elongation > _MPC_ELONGATION_DEG_MAX
            ):
                lunar_elongation = max(
                    _MPC_ELONGATION_DEG_MIN,
                    min(raw_lunar_elongation, _MPC_ELONGATION_DEG_MAX),
                )
                self.app.notify(
                    translate(
                        "Minimal lunar elongation must be between {low}° and {high}°; "
                        "using {degrees}°."
                    ).format(
                        low=_MPC_ELONGATION_DEG_MIN,
                        high=_MPC_ELONGATION_DEG_MAX,
                        degrees=lunar_elongation,
                    ),
                    severity="warning",
                )

            minimal_height = raw_min_alt
            if (
                minimal_height < _MPC_MIN_ALT_DEG_MIN
                or minimal_height > _MPC_MIN_ALT_DEG_MAX
            ):
                minimal_height = max(
                    _MPC_MIN_ALT_DEG_MIN,
                    min(raw_min_alt, _MPC_MIN_ALT_DEG_MAX),
                )
                self.app.notify(
                    translate(
                        "Minimal altitude must be between {low}° and {high}°; using {degrees}°."
                    ).format(
                        low=_MPC_MIN_ALT_DEG_MIN,
                        high=_MPC_MIN_ALT_DEG_MAX,
                        degrees=minimal_height,
                    ),
                    severity="warning",
                )

            max_objects = raw_max_objects
            if max_objects < _MPC_MAX_OBJECTS_MIN or max_objects > _MPC_MAX_OBJECTS_MAX:
                max_objects = max(
                    _MPC_MAX_OBJECTS_MIN,
                    min(raw_max_objects, _MPC_MAX_OBJECTS_MAX),
                )
                self.app.notify(
                    translate(
                        "Maximum number of objects must be between {low} and {high}; "
                        "using {value}."
                    ).format(
                        low=_MPC_MAX_OBJECTS_MIN,
                        high=_MPC_MAX_OBJECTS_MAX,
                        value=max_objects,
                    ),
                    severity="warning",
                )

            object_type = cast(str, self.query_one("#object_type", Select).value)

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

            target_list = await asyncio.to_thread(
                scheduling.observing_target_list,
                cfg,
                payload,
            )
            open_browser = self.query_one("#browser", Checkbox).value
            if open_browser:
                await asyncio.to_thread(
                    lambda: target_list.show_in_browser(jsviewer=True)
                )
                msg = translate("Done. Table opened in browser.")
            else:
                msg = str(target_list)
            await _push_result_log_modal(self, msg)
        finally:
            btn.disabled = False


def _local_coordinates(config: ConfigParser) -> List[str]:
    """Return latitude/longitude strings from the observatory section (after reload)."""
    configuration.load_config(config)
    latitude = config["Observatory"]["latitude"]
    longitude = config["Observatory"]["longitude"]
    return [latitude, longitude]


def _parse_datetime_inputs(screen: ObservingTargetListScreen) -> datetime.datetime:
    """UTC start time parsed from `#day`..`#second` widgets (raises ``ValueError``)."""
    day = int(screen.query_one("#day", Input).value.strip())
    month = int(screen.query_one("#month", Input).value.strip())
    year = int(screen.query_one("#year", Input).value.strip())
    hour = int(screen.query_one("#hour", Input).value.strip())
    minutes = int(screen.query_one("#minute", Input).value.strip())
    seconds = int(screen.query_one("#second", Input).value.strip())
    return datetime.datetime(year, month, day, hour, minutes, seconds)


class ResultLogScreen(Screen):
    """Modal-ish screen dumping long plaintext into a scrollable Rich log."""

    BINDINGS = [Binding("escape", "close", "Close")]

    def __init__(self, body: str) -> None:
        """``body`` fills the embedded log immediately after mount."""
        super().__init__()
        self._body = body

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            RichLog(id="log", wrap=True, highlight=True),
            Button(translate("Close"), id="close", variant="primary"),
            id="panel",
        )

    def on_mount(self) -> None:
        self.query_one("#log", RichLog).write(self._body)

    def action_close(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss()


async def _push_result_log_modal(screen: Screen, body: str) -> None:
    """Push :class:`ResultLogScreen` and await dismiss.

    ``App.push_screen_wait`` requires an active Textual worker; message handlers
    (e.g. button presses) run outside that context, so the wait is delegated to
    ``run_worker`` (see ``NoActiveWorker`` in Textual).
    """

    async def _work() -> None:
        await screen.app.push_screen_wait(ResultLogScreen(body))

    worker = screen.run_worker(_work(), exit_on_error=False)
    try:
        await worker.wait()
    except WorkerFailed as exc:
        raise exc.error from exc


class NeocpScreen(Screen):
    """Filter NEOcp confirmation prospects; render table or JS viewer."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("NEOcp confirmation")),
            Horizontal(
                Label(translate("Minimum score -> ")),
                Input(placeholder="", id="min_score"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("Maximum magnitude -> ")),
                Input(placeholder="", id="max_mag"),
                classes="input-row",
            ),
            Horizontal(
                Label(translate("Minimum altitude -> ")),
                Input(placeholder="", id="min_alt"),
                classes="input-row",
            ),
            Checkbox(
                translate("Open result in browser"),
                id="browser",
            ),
            Horizontal(
                Button(translate("Run"), id="run", variant="primary"),
                Button(translate("0 - Back"), id="back"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "run":
            await self._do_run()

    async def _do_run(self) -> None:
        """Validate numeric filters, fetch async MPC table, show result overlay."""
        btn = self.query_one("#run", Button)
        btn.disabled = True
        try:
            try:
                min_score = int(self.query_one("#min_score", Input).value.strip())
                min_altitude = int(self.query_one("#min_alt", Input).value.strip())
                max_magnitude = float(self.query_one("#max_mag", Input).value.strip())
            except ValueError:
                self.app.notify(
                    translate("You must enter valid numeric fields."),
                    severity="warning",
                )
                return

            table = await scheduling.async_neocp_confirmation(
                _app_config(self),
                min_score,
                max_magnitude,
                min_altitude,
            )
            open_browser = self.query_one("#browser", Checkbox).value
            if open_browser:
                await asyncio.to_thread(lambda: table.show_in_browser(jsviewer=True))
                msg = translate("Done. Table opened in browser.")
            else:
                msg = str(table)
            await _push_result_log_modal(self, msg)
        finally:
            btn.disabled = False


class EphemerisScreen(Screen):
    """Planetarium-style stepping ephemeris for a named solar-system object."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Object ephemeris")),
            Horizontal(
                Label(translate("Object Name -> ")),
                Input(placeholder="", id="oname"),
                classes="input-row",
            ),
            Label(translate("""Stepping
    m - 1 minute
    h - 1 hour
    d - 1 day
    w - 1 week
    """)),
            Select(
                (
                    ("m — 1 minute", "m"),
                    ("h — 1 hour", "h"),
                    ("d — 1 day", "d"),
                    ("w — 1 week", "w"),
                ),
                allow_blank=False,
                value="m",
                id="step",
            ),
            Horizontal(
                Button(translate("Run"), id="run", variant="primary"),
                Button(translate("0 - Back"), id="back"),
            ),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "run":
            await self._do_run()

    async def _do_run(self) -> None:
        """Run blocking ephemeris and push the textual table overlay."""
        btn = self.query_one("#run", Button)
        btn.disabled = True
        try:
            name = self.query_one("#oname", Input).value.strip()
            step = cast(str, self.query_one("#step", Select).value)
            if step not in {"m", "h", "d", "w"}:
                self.app.notify(
                    translate("Invalid choice — enter m, h, d, or w."),
                    severity="warning",
                )
                return
            table = await asyncio.to_thread(
                scheduling.object_ephemeris,
                _app_config(self),
                name,
                step,
            )
            await _push_result_log_modal(self, str(table))
        finally:
            btn.disabled = False


class TwilightScreen(Screen):
    """Compute twilight windows plus sun/moon rise/set summary for tonight."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> Any:
        yield Header()
        yield Footer()
        yield Vertical(
            Label(translate("Twilight & Sun/Moon")),
            Button(translate("Compute"), id="run", variant="primary"),
            RichLog(id="log", wrap=True, highlight=True),
            Button(translate("0 - Back"), id="back"),
            id="panel",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "run":
            await self._do_run()

    async def _do_run(self) -> None:
        """Gather twilight and ephemerides in one background call, print lines."""
        log = self.query_one("#log", RichLog)
        btn = self.query_one("#run", Button)
        log.clear()
        btn.disabled = True
        try:

            def _twilight_bundle(cfg: ConfigParser) -> Tuple[Any, Any]:
                """Pair twilight and sun/moon results for ``asyncio.to_thread``."""

                return scheduling.twilight_times(cfg), scheduling.sun_moon_ephemeris(
                    cfg
                )

            result_times, ephemeris = await asyncio.to_thread(
                _twilight_bundle,
                _app_config(self),
            )
            tfmt = "%H:%M:%S"
            lines = [
                translate("Civil twilight: {m} – {e}").format(
                    m=result_times["CivilM"].strftime(tfmt),
                    e=result_times["CivilE"].strftime(tfmt),
                ),
                translate("Nautical twilight: {m} – {e}").format(
                    m=result_times["NautiM"].strftime(tfmt),
                    e=result_times["NautiE"].strftime(tfmt),
                ),
                translate("Astronomical twilight: {m} – {e}").format(
                    m=result_times["AstroM"].strftime(tfmt),
                    e=result_times["AstroE"].strftime(tfmt),
                ),
                "",
                translate("Sunrise: {t}").format(t=ephemeris["Sunrise"].strftime(tfmt)),
                translate("Sunset: {t}").format(t=ephemeris["Sunset"].strftime(tfmt)),
                translate("Moonrise: {t}").format(
                    t=ephemeris["Moonrise"].strftime(tfmt)
                ),
                translate("Moonset: {t}").format(t=ephemeris["Moonset"].strftime(tfmt)),
                translate("Moon illumination: {f}").format(f=ephemeris["MoonIll"]),
            ]
            log.write("\n".join(lines))
        finally:
            btn.disabled = False
