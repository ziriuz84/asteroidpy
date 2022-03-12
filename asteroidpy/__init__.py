#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asteroidpy.interface
import configparser
import cProfile, pstats

PROFILE = True

config = configparser.ConfigParser()

def main():
    if (PROFILE):
        profiler = cProfile.Profile()
        profiler.enable()
        interface.interface(config)
        profiler.disable()
        stats= pstats.Stats(profiler).sort_stats('ncalls')
        stats.dump_stats('asteroidpy.prof')
    else:
        interface.interface(config)

