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

The configuration module handles all settings related to the observatory location,
observer information, and application preferences.

.. automodule:: asteroidpy.configuration
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

* :func:`load_config`: Load configuration from file or initialize defaults
* :func:`save_config`: Save current configuration to disk
* :func:`initialize`: Initialize configuration with default values
* :func:`get_observatory_coordinates`: Retrieve observatory coordinates from MPC database

asteroidpy.interface module
-----------------------------

The ``interface`` package boots GNU gettext from the persisted config and
launches :func:`~asteroidpy.interface.interface`, which runs the Textual
full-screen terminal UI. Legacy ``print``/``input`` helpers remain for scripting
or tooling.

Layout (private submodules; import only if you extend the UI):

* ``_tui_app`` — root Textual ``App`` subclass and ``style.tcss`` path
* ``_tui_screens`` — ``Screen`` definitions for menus, forms, and result views
* ``style.tcss`` — layout rules for centered panels, logs, and labelled inputs

.. automodule:: asteroidpy.interface
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

* :func:`~asteroidpy.interface.interface`: Spin up gettext and start the Textual application
* :func:`~asteroidpy.interface.main_menu`: Legacy text loop (not invoked by ``interface()`` today)
* :func:`~asteroidpy.interface.setup_gettext`: Prime gettext from the active config

Configuration and scheduling legacy menus live in ``interface._config_menus`` and
``interface._schedule_menus``; import them explicitly if you embed those flows
outside the default entry point.

asteroidpy.scheduling module
-----------------------------

The scheduling module handles observation planning, ephemeris calculations,
weather forecasts, and visibility calculations.

.. automodule:: asteroidpy.scheduling
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

* :func:`observing_target_list`: Build a ``QTable`` from the MPC POST payload
* :func:`neocp_confirmation`: Blocking NEOcp candidate table
* :func:`async_neocp_confirmation`: ``asyncio``-friendly NEOcp fetch for Textual
* :func:`object_ephemeris`: Ephemeris table for a named object
* :func:`twilight_times`: Civil/nautical/astronomical twilight datetimes
* :func:`sun_moon_ephemeris`: Sun/Moon rise/set + illumination dict
* :func:`weather_forecast_report`: Plain-text 7Timer report (used by the TUI)
* :func:`weather`: Legacy helper that prints the forecast to stdout
* :func:`resolve_whatsup_authenticity_token`: Scrape (and cache) form tokens for What's Observable
* :func:`is_visible`: Virtual-horizon visibility check

Module contents
---------------

.. automodule:: asteroidpy
    :members:
    :undoc-members:
    :show-inheritance:
