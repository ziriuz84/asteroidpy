asteroidpy package
==================

AsteroidPy is organized into several modules, each handling a specific aspect
of the application:

* :mod:`asteroidpy.configuration`: Configuration management and observatory settings
* :mod:`asteroidpy.interface`: gettext setup and the Textual screens
* :mod:`asteroidpy.scheduling`: Observation scheduling and ephemeris calculations
* :mod:`asteroidpy.cache`: Persistent response cache with a per-source time-to-live
* :mod:`asteroidpy.errors`: Typed errors carrying the reason a data source was unusable

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
full-screen terminal UI.

Layout (private submodules; import only if you extend the UI):

* ``_main`` — :func:`interface`, the entry point of the Textual app
* ``_i18n`` — packaged ``locales/`` lookup and :func:`setup_gettext`
* ``_intl`` — ``translate``, a thin wrapper over the gettext-installed ``builtins._``,
  and ``observatory_labels``, the localized ``[Observatory]`` labels the screens pass
  to :func:`~asteroidpy.configuration.observatory_summary_lines` and
  :func:`~asteroidpy.configuration.print_obs_config`
* ``_tui_app`` — root Textual ``App`` subclass and ``style.tcss`` path
* ``_tui_screens`` — ``Screen`` definitions for menus, forms, and result views
  (every screen derives from the shared ``MenuScreen``, which binds the arrow
  keys to Textual's focus actions and the digits to the numbered buttons, as
  described in :ref:`keyboard-navigation`; refreshes the observatory summary
  when resuming from child editors, showing
  latitude, longitude and altitude in clear via
  :func:`~asteroidpy.configuration.observatory_summary_lines`, clamps MPC What's
  Observable numeric fields before POST, offers ``2 - Clear cache`` under
  **General** to empty the :mod:`asteroidpy.cache` responses, notifies when a
  locale has ``base.po`` but no compiled ``base.mo``—compile with ``msgfmt`` as
  below)
* ``style.tcss`` — layout rules for centered panels, logs, and labelled inputs

.. automodule:: asteroidpy.interface
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

* :func:`interface`: Spin up gettext and start the Textual application
* :func:`setup_gettext`: Prime gettext from the active config

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
* :func:`resolve_whatsup_authenticity_token`: Scrape a fresh form token for What's Observable, or raise :exc:`~asteroidpy.errors.DataSourceError` (no embedded fallback)
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

Every request above that does not go through astroquery is wrapped in
:func:`asteroidpy.cache.fetch_cached`, keyed by endpoint plus request parameters.
:func:`object_ephemeris` and
:func:`asteroidpy.configuration.get_observatory_coordinates` keep astroquery's own
cache instead, which already stores them for a week.

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
* :data:`MPC_WHATSUP_SOURCE`: Source name used in :exc:`~asteroidpy.errors.DataSourceError`
* :data:`DEFAULT_EPHEMERIS_POINTS`: Ephemeris points requested by default
* :data:`DEFAULT_WEATHER_HOURS`: Forecast horizon in hours used by the weather screen

asteroidpy.errors module
------------------------

.. currentmodule:: asteroidpy.errors

The errors module carries the reason a remote source could not be used, so the
screens can tell "the MPC answered something unusable" from "no object found"
instead of showing an empty table.

.. automodule:: asteroidpy.errors
    :members:
    :undoc-members:
    :show-inheritance:

Key Classes
~~~~~~~~~~~

* :exc:`DataSourceError`: Unusable data source, with ``source``, ``reason`` and ``detail``
* :data:`REASON_HTTP_STATUS`: The source answered with an unexpected HTTP status
* :data:`REASON_NETWORK_ERROR`: The source could not be reached (timeout, DNS, TLS)
* :data:`REASON_TOKEN_NOT_FOUND`: The page no longer carries the expected token
* :data:`REASON_MALFORMED_RESPONSE`: The body could not be parsed

asteroidpy.cache module
-----------------------

.. currentmodule:: asteroidpy.cache

The cache module stores remote responses on disk, one JSON file per key, and
decides whether a stored answer may be used. Every request that does not go
through astroquery is wrapped in :func:`fetch_cached`, so a repeated run is
answered from disk and a network failure falls back to the last known answer
rather than to an empty table.

Entries live in the platform *cache* directory
(:func:`cache_root`), never beside the configuration file. The four outcomes —
``hit``, ``miss``, ``failover`` and ``disabled`` — are returned as a
:class:`FetchResult` together with the age of the entry served.

.. automodule:: asteroidpy.cache
    :members:
    :undoc-members:
    :show-inheritance:

Key Functions
~~~~~~~~~~~~~

* :func:`fetch_cached`: Serve a payload from disk, refetching per TTL
* :func:`fetch_cached_async`: The same, for a coroutine request
* :func:`cache_key`: sha256 file name identifying one request
* :func:`read`: Payload and age of a stored entry, or ``None`` on a miss
* :func:`write`: Store a payload atomically
* :func:`clear`: Remove every stored response
* :func:`cache_root`: Directory holding the response files
* :func:`is_enabled`: Whether the cache is switched on

Key Classes and Types
~~~~~~~~~~~~~~~~~~~~~

* :class:`FetchResult`: Payload, ``status`` (``hit``/``miss``/``failover``/``disabled``) and entry age
* :data:`CacheStatus`: The four outcomes of a cached fetch
* :data:`FailoverOn`: Exception types or a predicate selecting what may fail over

Module constants:

* :data:`CACHE_SUBDIR`: Sub-directory of the platform cache dir used
* :data:`CACHE_SCHEMA`: On-disk entry format version
* :data:`NO_CACHE_ENV_VAR`: Environment variable that switches the cache off
* :data:`TTL_TOKEN_SEC`: Lifetime of the What's Observable form token
* :data:`TTL_WEATHER_SEC`: Lifetime of a 7Timer forecast
* :data:`TTL_NEOCP_JSON_SEC`: Lifetime of the NEOcp live feed
* :data:`TTL_NEOCP_EPHEM_SEC`: Lifetime of the confirm ephemerides
* :data:`TTL_TARGET_LIST_SEC`: Lifetime of a What's Observable target table

asteroidpy package contents
---------------------------

The top-level package exposes the ``asteroidpy`` console-script entry point,
:func:`~asteroidpy.main`, which loads the configuration and launches the
interface (optionally under ``cProfile``).

.. automodule:: asteroidpy
    :members:
    :undoc-members:
    :show-inheritance:
