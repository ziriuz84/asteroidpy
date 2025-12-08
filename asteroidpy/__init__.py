#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AsteroidPy - A tool for asteroid observation scheduling and analysis.

AsteroidPy is a Python application designed to help astronomers schedule
and manage asteroid observations. It integrates with the Minor Planet Center
and other astronomical data sources to provide:

- Weather forecasts for observatory locations
- Observation scheduling with target lists
- NEOcp (Near Earth Object Confirmation Page) candidate listings
- Object ephemeris calculations
- Twilight and Sun/Moon ephemeris
- Virtual horizon visibility calculations

The application provides an interactive command-line interface with support
for multiple languages and comprehensive observatory configuration options.
"""
import configparser
import cProfile
import pstats
from configparser import ConfigParser

import asteroidpy.interface as interface

PROFILE = False

config: ConfigParser = configparser.ConfigParser()

def main() -> None:
    """Main entry point for the AsteroidPy application.

    Initializes the configuration and launches the user interface. Optionally
    enables profiling if the PROFILE flag is set to True.

    Returns
    -------
    None
        This function does not return a value.

    Notes
    -----
    If PROFILE is True, the function runs with cProfile enabled and saves
    profiling statistics to 'asteroidpy.prof'. Otherwise, it directly
    launches the interface.
    """
    if PROFILE:
        profiler = cProfile.Profile()
        profiler.enable()
        interface.interface(config)
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats("ncalls")
        stats.dump_stats("asteroidpy.prof")
    else:
        interface.interface(config)
