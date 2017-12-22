# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import argparse


class Error(Exception):
    """all captain errors will inherit from this base class"""
    pass


class ParseError(Error):
    """raised when a captain script encounters a parse error"""
    pass


class ArgError(argparse.ArgumentTypeError):
    pass

