asteroidpy package
==================

AsteroidPy is organized into several modules, each handling a specific aspect
of the application:

* :mod:`asteroidpy.configuration`: Configuration management and observatory settings
* :mod:`asteroidpy.interface`: gettext setup, legacy ``print``/``input`` helpers, Textual screens
* :mod:`asteroidpy.scheduling`: Observation scheduling and ephemeris calculations

Submodules
----------

asteroidpy.configuration module
--------------------------------

.. currentmodule:: asteroidpy.configuration

The configuration module handles all settings related to the observatory location,
observer information, and application preferences. It owns the INI file location
(``platformdirs`` user config dir, with automatic migration from the legacy
``~/.asteroidpy``) and the atomic write used to persist changes.

.. automodule:: asteroidpy.configuration
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

Persistence:

* :func:`load_config`: Load configuration from file or initialize defaults
* :func:`save_config`: Save current configuration to disk
* :func:`initialize`: Initialize configuration with default values
* :func:`merge_missing_defaults`: Fill absent sections/options from :data:`SECTION_DEFAULTS`

Paths:

* :func:`canonical_config_path`: Current INI path under the platform config dir
* :func:`legacy_config_path`: Historical ``~/.asteroidpy`` path (migration source only)

Observatory:

* :func:`get_observatory_coordinates`: Retrieve observatory coordinates from MPC database
* :func:`change_obs_coords`: Persist place, latitude and longitude
* :func:`change_obs_altitude`: Persist site altitude
* :func:`change_mpc_code`: Persist the MPC observatory code
* :func:`change_obs_name`: Persist the observatory site name
* :func:`change_observer_name`: Persist the observer name
* :func:`observatory_summary_lines`: Observatory fields as display-ready ``label: value`` lines, translated labels optional
* :func:`print_obs_config`: Print the observatory section, redacting coordinates by default
* :func:`virtual_horizon_configuration`: Persist per-direction virtual horizon minima

Localization:

* :func:`change_language`: Persist the ``[General] lang`` interface language

asteroidpy.interface module
-----------------------------

.. currentmodule:: asteroidpy.interface

The ``interface`` package boots GNU gettext from the persisted config and
launches :func:`interface`, which runs the Textual
full-screen terminal UI. Legacy ``print``/``input`` helpers remain for scripting
or tooling.

Layout (private submodules; import only if you extend the UI):

* ``_main`` — :func:`interface` and the legacy
  :func:`main_menu` text loop
* ``_i18n`` — packaged ``locales/`` lookup and :func:`setup_gettext`
* ``_intl`` — ``translate``, a thin wrapper over the gettext-installed ``builtins._``,
  and ``observatory_labels``, the localized ``[Observatory]`` labels both frontends pass
  to :func:`~asteroidpy.configuration.observatory_summary_lines` and
  :func:`~asteroidpy.configuration.print_obs_config`
* ``_input`` — EOF-safe ``prompt_line`` / ``get_integer`` / ``get_float`` / ``prompt_int_in_range``
* ``_tui_app`` — root Textual ``App`` subclass and ``style.tcss`` path
* ``_tui_screens`` — ``Screen`` definitions for menus, forms, and result views
  (refreshes the observatory summary when resuming from child editors, showing
  latitude, longitude and altitude in clear via
  :func:`~asteroidpy.configuration.observatory_summary_lines`, clamps MPC What's
  Observable numeric fields before POST, notifies when a locale has ``base.po``
  but no compiled ``base.mo``—compile with ``msgfmt`` as below)
* ``style.tcss`` — layout rules for centered panels, logs, and labelled inputs

.. automodule:: asteroidpy.interface
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

* :func:`interface`: Spin up gettext and start the Textual application
* :func:`main_menu`: Legacy text loop (not invoked by ``interface()`` today)
* :func:`setup_gettext`: Prime gettext from the active config

Configuration and scheduling legacy menus live in ``interface._config_menus`` and
``interface._schedule_menus``; import them explicitly if you embed those flows
outside the default entry point.

asteroidpy.scheduling module
-----------------------------

.. currentmodule:: asteroidpy.scheduling

The scheduling module handles observation planning, ephemeris calculations,
weather forecasts, twilight and Sun/Moon data, and best-night ranking.

.. automodule:: asteroidpy.scheduling
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

Weather:

* :func:`weather_forecast_raw`: Raw 7Timer ``astro`` JSON payload
* :func:`weather_forecast_report`: Plain-text 7Timer report (used by the TUI), with an optional hour horizon and temperature unit
* :func:`validated_ephemeris_points`: Check a requested ephemeris point count
* :func:`weather_temperature`: Render a Celsius value in the requested unit
* :func:`weather`: Legacy helper that prints the forecast to stdout
* :func:`weather_time`: Shift a 7Timer ``timeinit`` stamp by ``deltaT`` hours

MPC data:

* :func:`observing_target_list`: Build a ``QTable`` from the MPC POST payload
* :func:`observing_target_list_scraper`: POST the What's Observable form and scrape rows
* :func:`resolve_whatsup_authenticity_token`: Scrape (and cache) form tokens for What's Observable
* :func:`neocp_confirmation`: Blocking NEOcp candidate table
* :func:`async_neocp_confirmation`: ``asyncio``-friendly NEOcp fetch for Textual
* :func:`get_neocp_ephemeris`: Scrape MPC confirmation ephemerides for named NEOcp objects
* :func:`fetch_neocp_json_and_ephemeris`: Fetch NEOcp JSON and confirm ephemerides in one run
* :func:`object_ephemeris`: Ephemeris table for a named object, with a validated point count

Time, coordinates and visibility:

* :func:`twilight_times`: Civil/nautical/astronomical twilight datetimes
* :func:`sun_moon_ephemeris`: Sun/Moon rise/set + illumination dict
* :func:`earth_location_from_config`: Build an ``EarthLocation`` from ``[Observatory]``
* :func:`mpc_whatsup_table_cell_to_time`: Parse an MPC table time cell into UTC ``Time``
* :func:`skycoord_format`: Format an RA/Dec cell pair for display
* :func:`is_visible`: Virtual-horizon visibility check

Networking:

* :func:`httpx_get`: Async HTTP GET returning parsed body and status code
* :func:`httpx_post`: Async HTTP POST returning parsed body and status code

Best-night planner:

* :func:`astronomical_night`: ``(evening, morning)`` astronomical twilight for a night
* :func:`best_nights`: Ranked upcoming nights with per-night quality scores
* :func:`best_nights_report`: Plain-text ranking table (used by the TUI)
* :func:`planner_settings`: Read ``[Planner]`` tolerantly, falling back to the defaults
* :func:`parse_planner_max_nights`: Strict ``max_nights`` parser used by the editor
* :func:`parse_planner_weights`: Strict ``[Planner]`` weight parser, normalized to 1
* :func:`normalize_planner_weights`: Validate weights and divide them by their sum
* :exc:`PlannerValueError`: Why a planner value was rejected, and which options to blame

Module constants:

* :data:`SEVENTIMER_API_URL`: 7Timer endpoint queried for forecasts
* :data:`DEFAULT_PLANNER_WEIGHTS`: Fallback planner weights (also see ``[Planner]``)
* :data:`DEFAULT_PLANNER_MAX_NIGHTS`: Fallback number of ranked nights
* :data:`PLANNER_WEIGHT_OPTIONS`: ``[Planner]`` option holding each factor's weight
* :data:`CLOUDCOVER_MIDPOINT_PCT`: 7Timer ``cloudcover`` code to percent midpoint
* :data:`MPC_WHATSUP_INDEX_URL`: MPC "What's Observable" form endpoint
* :data:`DEFAULT_EPHEMERIS_POINTS`: Ephemeris points requested by default
* :data:`DEFAULT_WEATHER_HOURS`: Forecast horizon in hours used by the weather screen

asteroidpy package contents
---------------------------

The top-level package exposes the ``asteroidpy`` console-script entry point,
:func:`~asteroidpy.main`, which loads the configuration and launches the
interface (optionally under ``cProfile``).

.. automodule:: asteroidpy
    :members:
    :undoc-members:
    :show-inheritance:
