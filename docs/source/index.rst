.. AsteroidPy documentation master file, created by
   sphinx-quickstart on Sun May 22 09:25:09 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to AsteroidPy's documentation!
======================================

AsteroidPy is a Python command-line application for observing minor planets:
ephemerides, MPC “What's Observable” target lists, weather (7Timer), NEO
Confirmation Page views, twilight and Sun/Moon summaries, a ranked best-night
planner, and a configurable virtual horizon. The primary experience is an
interactive terminal UI built with `Textual`_, layered on shared gettext and
configuration helpers.

Features
--------

* **Weather Forecast**: Astronomical forecasts (seeing, clouds, transparency) via 7Timer, over a horizon of 6–168 hours (72 by default) and in °C or °F
* **Observation Scheduling**: Plan observing sessions with target lists
* **NEOcp Candidates**: List and filter near-Earth object candidates
* **Object Ephemeris**: Retrieve detailed ephemeris data for any object, from 1 to 10000 points
* **Twilight Times**: Calculate civil, nautical, and astronomical twilight
* **Sun/Moon Ephemeris**: Get sunrise, sunset, moonrise, and moonset times
* **Best Upcoming Night**: Rank upcoming astronomical nights by observing quality
* **Virtual Horizon**: Simulate horizon obstructions for visibility calculations (0–90° per cardinal direction)
* **Response Cache**: Keep recent MPC and 7Timer answers on disk with a per-source
  time-to-live, so a repeated run needs no network

Requirements
------------

* **Python** 3.11 or later (supported: 3.11, 3.12, 3.13 and 3.14)
* **pip** (or another Python package manager)

AsteroidPy runs on Linux, macOS, and Windows. On Windows, use Windows Terminal
or another modern terminal for the Textual UI.

The 3.11 floor comes from the dependency stack rather than the application code:
``astropy`` 7 and later require Python 3.11+, and ``platformdirs`` and ``requests``
require 3.10. Pinning the floor at 3.11 means every supported interpreter resolves
the same versions of the scientific stack.

Quick Start
-----------

Install AsteroidPy::

    pip install asteroidpy

Run the application with the ``asteroidpy`` console script::

    asteroidpy

The main menu offers **Configuration** (general settings and observatory
details) and **Observation scheduling** (weather, target lists, NEOcp,
ephemeris, twilight, best night).

.. _keyboard-navigation:

Keyboard Navigation
-------------------

Every screen is fully drivable from the keyboard; the mouse is optional.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Key
     - Action
   * - ``Up`` / ``Down``
     - Move the focus to the previous/next widget, exactly like
       ``Shift+Tab`` / ``Tab``
   * - ``Tab`` / ``Shift+Tab``
     - Move the focus forward/backward
   * - ``0``-``9``
     - Activate the menu entry carrying that number in its label (e.g.
       ``1 - Configuration``, ``0 - Back to main menu``)
   * - ``Escape``
     - Go back to the previous screen
   * - ``Ctrl+Q``
     - Quit, from the main menu

The numbers are always visible in the button labels, so the shortcut for a
screen is readable without leaving it. A digit with no matching entry — or one
whose entry is disabled while a background query runs — is simply ignored.

Arrow keys also work while filling in a form, and typing digits into a text
field is never intercepted: input widgets consume printable characters before
the shortcut is considered.

Configuration
-------------

Settings live in a single INI file named ``.asteroidpy`` inside the
application configuration directory returned by
`platformdirs <https://github.com/platformdirs/platformdirs>`_ — for example
``~/.config/asteroidpy/`` on Linux, ``~/Library/Application Support/asteroidpy/``
on macOS, and ``%LOCALAPPDATA%\asteroidpy\`` on Windows. Legacy installs with a
copy at ``~/.asteroidpy`` are migrated automatically on first run.

The file has three sections:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Section
     - Options
   * - ``[General]``
     - ``lang`` — interface language (``en``, ``it``, ``de``, ``fr``, ``es``, ``pt``)
   * - ``[Planner]``
     - ``max_nights`` — how many nights the best-night planner ranks;
       ``w_cloud``, ``w_seeing``, ``w_transparency``, ``w_moon`` — relative
       weights, normalized to sum to 1. Clouds, seeing, transparency and Moon
       illumination are the only inputs to the score.
   * - ``[Observatory]``
     - ``place``, ``latitude``, ``longitude``, ``altitude`` — site description;
       ``obs_name``, ``observer_name`` — labels for reports;
       ``mpc_code`` — MPC observatory code;
       ``nord_altitude``, ``east_altitude``, ``south_altitude``,
       ``west_altitude`` — virtual horizon minima in degrees

Missing options are filled from the defaults declared in
:data:`asteroidpy.configuration.SECTION_DEFAULTS` on every load, so a partial
or older file stays usable. Every section is editable from the in-app
**Configuration** menu, ``[Planner]`` included: the planner screen validates the
weights with the same rules as the loader, shows the values that will really be
applied (the weights divided by their sum) and previews the score of the next few
nights without saving.

Response cache
--------------

Requests that do not go through astroquery are cached on disk by
:mod:`asteroidpy.cache`, so a repeated run is answered without touching the
network and a temporary outage shows the last known answer instead of an empty
table. The cache lives in the platform **cache** directory returned by
``platformdirs.user_cache_dir`` — for example ``~/.cache/asteroidpy/http/`` on
Linux, ``~/Library/Caches/asteroidpy/http/`` on macOS and
``%LOCALAPPDATA%\\asteroidpy\\http\\`` on Windows — deliberately not beside the
INI file, so discarding the settings never discards data.

Each source has its own lifetime, because they do not go stale at the same rate:

.. list-table::
   :header-rows: 1
   :widths: 46 14 40

   * - Source
     - Lifetime
     - Why
   * - MPC What's Observable form token
     - 15 minutes
     - A Rails authenticity token is perishable
   * - MPC NEOcp feed and confirm ephemerides
     - 15 minutes
     - A live feed: the point is what is new right now
   * - MPC What's Observable target table
     - 15 minutes
     - Describes the sky at a single instant
   * - 7Timer weather forecast
     - 3 hours
     - 7Timer ``astro`` itself refreshes twice a day

:func:`asteroidpy.scheduling.object_ephemeris` and
:func:`asteroidpy.configuration.get_observatory_coordinates` are not cached here:
astroquery already stores those responses for a week.

Empty the cache with **Configuration → General → Clear cache**, or bypass it by
setting ``ASTEROIDPY_NO_CACHE=1`` — useful when comparing two runs or filing a
bug report. A cached entry is always replaced once its lifetime has passed, and a
file that is unreadable or corrupt counts as a miss rather than breaking the
application.

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

API Reference
-------------

See :doc:`modules` for the package overview and autogenerated references for each submodule.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Textual: https://textual.textualize.io/
