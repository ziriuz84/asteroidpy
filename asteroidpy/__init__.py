#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import cProfile
import pstats

import asteroidpy.interface

PROFILE = True

config = configparser.ConfigParser()


def main():
    """Main function"""
    if PROFILE:
        profiler = cProfile.Profile()
        profiler.enable()
        interface.interface(config)
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats("ncalls")
        stats.dump_stats("asteroidpy.prof")
    else:
        interface.interface(config)
