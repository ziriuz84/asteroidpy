asteroidpy package
==================

AsteroidPy is organized into several modules, each handling a specific aspect
of the application:

* :mod:`asteroidpy.configuration`: Configuration management and observatory settings
* :mod:`asteroidpy.interface`: User interface and menu system
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

The interface module provides the interactive command-line user interface,
including menus, input validation, and user interaction functions.

.. automodule:: asteroidpy.interface
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

Key Functions
~~~~~~~~~~~~~

* :func:`interface`: Main interface entry point
* :func:`main_menu`: Main application menu loop
* :func:`config_menu`: Configuration menu
* :func:`scheduling_menu`: Observation scheduling menu
* :func:`setup_gettext`: Initialize internationalization

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

* :func:`observing_target_list`: Generate list of visible objects from MPC
* :func:`neocp_confirmation`: Get NEOcp candidate list
* :func:`object_ephemeris`: Retrieve ephemeris for a specific object
* :func:`twilight_times`: Calculate twilight times
* :func:`sun_moon_ephemeris`: Get Sun and Moon ephemeris
* :func:`weather`: Display weather forecast
* :func:`is_visible`: Check if object is above virtual horizon

Module contents
---------------

.. automodule:: asteroidpy
    :members:
    :undoc-members:
    :show-inheritance:
