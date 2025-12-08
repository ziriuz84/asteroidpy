import datetime
import gettext
import os
from configparser import ConfigParser
import asteroidpy.configuration as configuration
import asteroidpy.scheduling as scheduling
from typing import List, Dict, Union, Any, Tuple
from astroquery.mpc import MPC


def setup_gettext(config: ConfigParser) -> None:
    """Initialize gettext based on configured language and install _ globally.

    Looks up the language from the user's configuration file and installs
    the appropriate translator using the `locales` directory at the project root.
    """
    # Ensure configuration is loaded so we read the latest language
    configuration.load_config(config)
    lang = config.get("General", "lang", fallback="en")
    # Compute path to locales directory (project_root/locales)
    locale_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "locales")
    )
    # Install translator; fallback keeps UI working even if .mo is missing
    translator = gettext.translation(
        "base", localedir=locale_dir, languages=[lang], fallback=True
    )
    translator.install()


def get_integer(message: str) -> int:
    """Prompt user for an integer input with validation.

    Continuously prompts the user until a valid integer is entered.
    Displays an error message if the input cannot be converted to an integer.

    Parameters
    ----------
    message : str
        The prompt message to display to the user.

    Returns
    -------
    int
        The integer value entered by the user.

    Notes
    -----
    This function will loop indefinitely until a valid integer is provided.
    """
    while True:
        try:
            userInt = int(input(message))
            return userInt
        except ValueError:
            print("You must enter an integer")


def get_float(message: str) -> float:
    """Prompt user for a float input with validation.

    Continuously prompts the user until a valid floating-point number is entered.
    Displays an error message if the input cannot be converted to a float.

    Parameters
    ----------
    message : str
        The prompt message to display to the user.

    Returns
    -------
    float
        The floating-point value entered by the user.

    Notes
    -----
    This function will loop indefinitely until a valid float is provided.
    """
    while True:
        try:
            userFloat = float(input(message))
            return userFloat
        except ValueError:
            print("You must enter a number")


def local_coords(config: ConfigParser) -> List[str]:
    """Get local geographical coordinates from configuration.

    Retrieves the observatory's latitude and longitude from the configuration
    file and returns them as a list of strings.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object containing the observatory configuration.

    Returns
    -------
    list of str
        A list containing [latitude, longitude] as strings.
    """
    configuration.load_config(config)
    lat = config["Observatory"]["latitude"]
    long = config["Observatory"]["longitude"]
    return [lat, long]


def select_specific_time() -> datetime.datetime:
    """Prompt user to input a specific observation start time.

    Interactively collects date and time components (day, month, year, hour,
    minutes, seconds) from the user and constructs a datetime object in UTC.

    Returns
    -------
    datetime.datetime
        A datetime object representing the observation start time in UTC.

    Notes
    -----
    All time components are collected via user input prompts. The function
    assumes UTC timezone.
    """
    print(_("Provide me with the observation start time parameters (UTC)"))
    day = get_integer(_("Day -> "))
    month = get_integer(_("Month -> "))
    year = get_integer(_("Year -> "))
    hour = get_integer(_("Hour -> "))
    minutes = get_integer(_("Minutes -> "))
    seconds = get_integer(_("Seconds -> "))
    time = datetime.datetime(year, month, day, hour, minutes, seconds)
    return time


def WIP() -> None:
    """Display a work in progress message.

    Prints a localized "Work in Progress" message followed by blank lines
    for visual separation in the interface.

    Returns
    -------
    None
        This function does not return a value.
    """
    print(_("Work in Progress"))
    print("\n\n\n\n\n\n\n\n")


def change_obs_coords_menu(config: ConfigParser) -> None:
    """Interactive menu to change observatory coordinates.

    Prompts the user for locality name, latitude, and longitude, then updates
    the configuration file with the new values.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.
    """
    place = input(_("Locality -> "))
    latitude = get_float(_("Latitude -> "))
    longitude = get_float(_("Longitude -> "))
    configuration.change_obs_coords(config, place, latitude, longitude)


def change_obs_altitude_menu(config: ConfigParser) -> None:
    """Interactive menu to change observatory altitude.

    Prompts the user for the observatory altitude in meters and updates
    the configuration file.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.
    """
    altitude = get_integer(_("Altitude -> "))
    configuration.change_obs_altitude(config, altitude)


def change_observer_name_menu(config: ConfigParser) -> None:
    """Interactive menu to change observer name.

    Prompts the user for the observer's name and updates the configuration file.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.
    """
    name = input(_("Observer name -> "))
    configuration.change_observer_name(config, name)


def change_obs_name_menu(config: ConfigParser) -> None:
    """Interactive menu to change observatory name.

    Prompts the user for the observatory name and updates the configuration file.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.
    """
    name = input(_("Observatory name -> "))
    configuration.change_obs_name(config, name)


def change_mpc_code_menu(config: ConfigParser) -> None:
    """Interactive menu to change MPC observatory code.

    Prompts the user for the MPC code and optionally updates the observatory
    coordinates and name from the MPC database if the user confirms.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    After entering the MPC code, the user is prompted whether to update
    coordinates from the MPC database. If confirmed, the observatory name,
    latitude, and longitude are automatically updated.
    """
    code = input(_("MPC Code -> "))
    configuration.change_mpc_code(config, code)
    update_coordinates = input(_("Update coordinates? (y/N) -> "))
    if update_coordinates in ["y", "Y", "s", "S"]:
        location = configuration.get_observatory_coordinates(code)
        configuration.change_obs_coords(config, location[3], location[1], location[0])
        configuration.change_obs_name(config, location[3])


def print_observatory_config_menu() -> None:
    """Print the observatory configuration menu options.

    Displays a localized menu with options to configure various observatory
    settings including coordinates, altitude, names, MPC code, and virtual horizon.

    Returns
    -------
    None
        This function does not return a value.
    """
    print(
        _(
            """Choose an option
    1 - Change coordinates
    2 - Change altitude
    3 - Change the name of the observer
    4 - Change the name of the observatory
    5 - Change the MPC code
    6 - Change Virtual Horizon
    0 - Back to configuration menu"""
        )
    )


def observatory_config_menu(config: ConfigParser) -> None:
    """Main observatory configuration menu loop.

    Displays the observatory configuration menu and current settings, then
    handles user input to navigate to various configuration submenus.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The menu loops until the user selects option 0 to return to the main
    configuration menu. Available options:
    - 1: Change coordinates
    - 2: Change altitude
    - 3: Change observer name
    - 4: Change observatory name
    - 5: Change MPC code
    - 6: Change virtual horizon
    - 0: Back to configuration menu
    """
    choice = 99
    while choice != 0:
        print(_("Configuration -> Observatory"))
        print("==============================\n")
        configuration.print_obs_config(config)
        print_observatory_config_menu()
        choice = get_integer(_("choice -> "))
        print("\n\n\n\n\n")
        if choice == 1:
            change_obs_coords_menu(config)
        if choice == 2:
            change_obs_altitude_menu(config)
        if choice == 3:
            change_observer_name_menu(config)
        if choice == 4:
            change_obs_name_menu(config)
        if choice == 5:
            change_mpc_code_menu(config)
        if choice == 6:
            change_horizon(config)


def change_language(config: ConfigParser) -> None:
    """Interactive menu to change the interface language.

    Discovers available languages from the locales directory, displays them
    to the user, and updates the configuration with the selected language.
    Re-initializes gettext so the language change takes effect immediately.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    Only languages with compiled .mo files are shown. If a language has only
    a .po file, a warning is issued. English is always available as a fallback.
    The language change is applied immediately to the current session.
    """
    # Discover available languages by scanning the locales directory
    locale_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "locales")
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

    import warnings

    # Only include languages that have a compiled base.mo.
    available_langs = []
    for code in candidates:
        lc_dir = os.path.join(locale_dir, code, "LC_MESSAGES")
        mo_path = os.path.join(lc_dir, "base.mo")
        po_path = os.path.join(lc_dir, "base.po")
        if os.path.exists(mo_path):
            available_langs.append(code)
        elif os.path.exists(po_path):
            warnings.warn(
                f"Locale '{code}' has a base.po but no compiled base.mo. Translation may not be available until compiled."
            )

    # Provide native names for known languages; fall back to the code itself
    native_names = {
        "en": "English",
        "it": "Italiano",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "pt": "Português",
    }

    # Ensure English is always present as a fallback option
    if "en" not in available_langs:
        available_langs.insert(0, "en")

    print(_("Select a language"))
    for index, code in enumerate(available_langs, start=1):
        print(f"{index} - {native_names.get(code, code)}")

    # Read and validate choice
    choice = get_integer(_("Language -> "))
    while choice < 1 or choice > len(available_langs):
        print(
            _(
                "Invalid choice. Please enter a number between 1 and {max_choice}."
            ).format(max_choice=len(available_langs))
        )
        choice = get_integer(_("Language -> "))

    lang = available_langs[choice - 1]
    configuration.change_language(config, lang)
    # Re-initialize gettext so language takes effect immediately
    setup_gettext(config)


def general_config_menu(config: ConfigParser) -> None:
    """Main general configuration menu loop.

    Displays the general configuration menu and handles user input to navigate
    to various general configuration submenus (e.g., language settings).

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The menu loops until the user selects option 0 to return to the main
    configuration menu. Available options:
    - 1: Language settings
    - 0: Back to configuration menu
    """
    choice = 99
    while choice != 0:
        print(_("Configuration -> General"))
        print("==============================")
        print("\n")
        print(_("Choose a submenu"))
        print(_("1 - Language"))
        print(_("0 - Back to configuration menu"))
        choice = get_integer(_("choice -> "))
        print("\n\n\n\n\n")
        if choice == 1:
            change_language(config)


def config_menu(config: ConfigParser) -> None:
    """Main configuration menu loop.

    Displays the main configuration menu and handles user input to navigate
    to general or observatory configuration submenus.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The menu loops until the user selects option 0 to return to the main menu.
    Available options:
    - 1: General configuration
    - 2: Observatory configuration
    - 0: Back to main menu

    Warning
    -------
    This function uses `eval()` on user input, which is a security risk.
    Consider replacing with `get_integer()` for safer input handling.
    """
    choice = 99
    while choice != 0:
        print(_("Configuration"))
        print("==============================")
        print("\n")
        print(_("Choose a submenu"))
        print(_("1 - General"))
        print(_("2 - Observatory"))
        print(_("0 - Back to main menu"))
        choice = eval(input(_("choice -> ")))
        print("\n\n\n\n\n")
        if choice == 1:
            general_config_menu(config)
        if choice == 2:
            observatory_config_menu(config)


def observing_target_list_menu(config: ConfigParser) -> None:
    """Interactive menu to generate and display observing target list.

    Prompts the user for observation parameters (time, duration, constraints)
    and object type, then queries the Minor Planet Center for visible objects.
    Displays the results either in the terminal or in a browser.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The function collects the following parameters from the user:
    - Observation time (current time or specific time)
    - Duration of observation
    - Minimum solar elongation
    - Minimum lunar elongation
    - Minimum altitude
    - Maximum number of objects
    - Object type (Asteroids, NEAs, or Comets)

    Results are filtered by the virtual horizon configuration and can be
    displayed in a browser for better visualization.
    """
    authenticity_token = "W5eBzzw9Clj4tJVzkz0z%2F2EK18jvSS%2BffHxZpAshylg%3D"
    coordinates = local_coords(config)
    select_time = input(_("Do you want to know the asteroids visible right now? [y/N]"))
    if select_time == "s" or select_time == "y":
        time = datetime.datetime.utcnow()
    else:
        time = select_specific_time()
    duration = get_integer(_("Duration of observation -> "))
    solar_elongation = get_integer(_("Minimal solar elongation -> "))
    lunar_elongation = get_integer(_("Minimal lunar elongation -> "))
    minimal_height = get_integer(_("Minimal altitude-> "))
    max_objects = get_integer(_("Maximum number of objects -> "))
    object_request = get_integer(
        _("Select type of object\n1 - Asteroids\n2 - NEAs\n3 - Comets\nChoice -> ")
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
        "year": time.year,
        "month": time.month,
        "day": time.day,
        "hour": time.hour,
        "minute": time.minute,
        "duration": duration,
        "max_objects": max_objects,
        "min_alt": minimal_height,
        "solar_elong": solar_elongation,
        "lunar_elong": lunar_elongation,
        "object_type": object_type,
        "submit": "Submit",
    }
    target_list = scheduling.observing_target_list(config, payload)
    browser_view = input(_("Do you want to view in Browser? (y/N) -> "))
    if browser_view in ["y", "Y"]:
        target_list.show_in_browser(jsviewer=True)
    else:
        print(target_list)
    print("\n\n\n\n")


def neocp_confirmation_menu(config: ConfigParser) -> None:
    """Interactive menu to display NEOcp (Near Earth Object Confirmation Page) list.

    Prompts the user for filtering criteria (minimum score, maximum magnitude,
    minimum altitude) and displays NEO candidates that meet the criteria and
    are visible from the configured observatory location.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The function queries the Minor Planet Center's NEOcp database and filters
    results based on user-specified criteria. Results can be displayed in the
    terminal or in a browser for better visualization.
    """
    min_score = get_integer(_("Minimum score -> "))
    max_magnitude = get_float(_("Maximum magnitude -> "))
    min_altitude = get_integer(_("Minimum altitude -> "))
    browser_view = input(_("Do you want to view in Browser? (y/N) -> "))
    neocp = scheduling.neocp_confirmation(
        config, min_score, max_magnitude, min_altitude
    )
    # titles=['Designation', 'Score', 'R.A.', 'Dec.', 'Alt.', 'V', 'NObs', 'Arc', 'Not Seen Days']
    if browser_view in ["y", "Y"]:
        neocp.show_in_browser(jsviewer=True)
    else:
        print(neocp)
    print("\n\n\n\n")
    # print(neocp)


def twilight_sun_moon_menu(config: ConfigParser) -> None:
    """Display twilight times and sun/moon ephemeris information.

    Calculates and displays civil, nautical, and astronomical twilight times
    for the configured observatory location, as well as sunrise, sunset,
    moonrise, moonset, and moon illumination.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    All times are calculated for the next occurrence from the current UTC time.
    Times are displayed in HH:MM:SS format.
    """
    result_times = scheduling.twilight_times(config)
    print(
        _(
            f"Civil Twilight: {result_times['CivilM'].strftime('%H:%M:%S')} - {result_times['CivilE'].strftime('%H:%M:%S')}"
        )
    )
    print(
        _(
            f"Nautical Twilight: {result_times['NautiM'].strftime('%H:%M:%S')} - {result_times['NautiE'].strftime('%H:%M:%S')}"
        )
    )
    print(
        _(
            f"Astronomical Twilight: {result_times['AstroM'].strftime('%H:%M:%S')} - {result_times['AstroE'].strftime('%H:%M:%S')}"
        )
    )
    print("\n")
    ephemeris = scheduling.sun_moon_ephemeris(config)
    print(_(f"Sunrise: {ephemeris['Sunrise'].strftime('%H:%M:%S')}"))
    print(_(f"Sunset: {ephemeris['Sunset'].strftime('%H:%M:%S')}"))
    print(_(f"Moonrise: {ephemeris['Moonrise'].strftime('%H:%M:%S')}"))
    print(_(f"Moonset: {ephemeris['Moonset'].strftime('%H:%M:%S')}"))
    print(_(f"Moon Illumination: {ephemeris['MoonIll']}"))
    print("\n\n\n\n")


def print_scheduling_menu() -> None:
    """Print the observation scheduling menu options.

    Displays a localized menu with options for various observation scheduling
    and planning features.

    Returns
    -------
    None
        This function does not return a value.
    """
    print(_("Observation scheduling"))
    print("==============================\n")
    print(
        _(
            """Choose a submenu
    1 - Weather forecast
    2 - Observing target List
    3 - NEOcp list
    4 - Object Ephemeris
    5 - Twilight Times
    0 - Back to main menu\n"""
        )
    )


def scheduling_menu(config: ConfigParser) -> None:
    """Main observation scheduling menu loop.

    Displays the scheduling menu and handles user input to navigate to various
    scheduling and planning features.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The menu loops until the user selects option 0 to return to the main menu.
    Available options:
    - 1: Weather forecast
    - 2: Observing target list
    - 3: NEOcp list
    - 4: Object ephemeris
    - 5: Twilight times
    - 0: Back to main menu
    """
    choice = 99
    while choice != 0:
        print_scheduling_menu()
        choice = get_integer(_("choice -> "))
        print("\n\n\n\n\n")
        if choice == 1:
            scheduling.weather(config)
        if choice == 2:
            observing_target_list_menu(config)
        if choice == 3:
            neocp_confirmation_menu(config)
        if choice == 4:
            object_ephemeris_menu(config)
        if choice == 5:
            twilight_sun_moon_menu(config)


def main_menu(config: ConfigParser) -> None:
    """Main application menu loop.

    Displays the main menu and handles user input to navigate to configuration
    or observation scheduling features.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    The menu loops until the user selects option 0 to exit the application.
    Available options:
    - 1: Configuration
    - 2: Observation scheduling
    - 0: Exit
    """
    choice = 99
    while choice != 0:
        print(_("Welcome to AsteroidPY v. 0.1"))
        print("==============================")
        print("\n")
        print(_("Choose a submenu"))
        print(_("1 - Configuration"))
        print(_("2 - Observation scheduling"))
        print(_("0 - Exit"))
        choice = get_integer(_("choice -> "))
        print("\n\n\n\n\n")
        if choice == 1:
            config_menu(config)
        if choice == 2:
            scheduling_menu(config)


def interface(config: ConfigParser) -> None:
    """Main interface entry point for the application.

    Initializes internationalization (gettext) based on the configured language
    and launches the main menu.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    This is the primary entry point for the interactive user interface.
    It sets up localization before displaying any UI elements to ensure
    all text is properly translated.
    """
    # Initialize gettext before printing any UI strings
    setup_gettext(config)
    main_menu(config)


def print_change_horizon_menu() -> Dict[str, str]:
    """Interactive menu to configure virtual horizon altitudes.

    Prompts the user for minimum altitude thresholds in each cardinal direction
    (north, south, east, west) used to simulate obstructions.

    Returns
    -------
    dict of str
        Dictionary with keys 'nord', 'south', 'east', 'west' containing
        the altitude thresholds as strings.
    """
    horizon = {}
    horizon["nord"] = input(_("Nord Altitude -> "))
    horizon["south"] = input(_("South Altitude -> "))
    horizon["east"] = input(_("East Altitude -> "))
    horizon["west"] = input(_("West Altitude -> "))
    return horizon


def change_horizon(config: ConfigParser) -> None:
    """Interactive menu to change virtual horizon configuration.

    Prompts the user for virtual horizon altitude thresholds and updates
    the configuration file.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.
    """
    horizon = print_change_horizon_menu()
    configuration.virtual_horizon_configuration(config, horizon)


def object_ephemeris_menu(config: ConfigParser) -> None:
    """Interactive menu to retrieve and display object ephemeris.

    Prompts the user for an object name and time step, then queries the
    Minor Planet Center for ephemeris data and displays the results.

    Parameters
    ----------
    config : ConfigParser
        The ConfigParser object with configuration options.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    Available time step options:
    - 'm': 1 minute
    - 'h': 1 hour
    - 'd': 1 day
    - 'w': 1 week

    The ephemeris includes 30 data points with information about position,
    magnitude, altitude, and motion.
    """
    object_name = input(_("Object Name -> "))
    print(
        _(
            """Stepping
    m - 1 minute
    h - 1 hour
    d - 1 day
    w - 1 week
    """
        )
    )
    step = input(_("Choice -> "))
    ephemeris = scheduling.object_ephemeris(config, object_name, step)
    print(ephemeris)
