#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asteroidpy.interface as interface
import configparser
import cProfile, pstats
from configparser import ConfigParser

PROFILE = True

config: ConfigParser = configparser.ConfigParser()

def main() -> None:
    """Main function"""
    if (PROFILE):
        profiler = cProfile.Profile()
        profiler.enable()
        interface.interface(config)
        profiler.disable()
        stats= pstats.Stats(profiler).sort_stats('ncalls')
        stats.dump_stats('asteroidpy.prof')
    else:
        interface.interface(config)

