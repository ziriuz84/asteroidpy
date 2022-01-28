#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from asteroidpy import interface
import configparser

config = configparser.ConfigParser()

def main():
    interface.interface(config)
