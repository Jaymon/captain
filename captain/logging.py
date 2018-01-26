# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys

from logging import *


class InlineStream(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, v):
        v = v.strip("\n")
        return self.stream.write(v)

    def __getattr__(self, k):
        return getattr(self.stream, k)


# configure our special loggers
log_formatter = Formatter('%(message)s')
log_handler = StreamHandler(stream=sys.stdout)
log_handler.setFormatter(log_formatter)

stderr = getLogger('captain.echo.stderr')
if len(stderr.handlers) == 0:
    stderr.propagate = False
    stderr.setLevel(DEBUG)
    stderr.addHandler(log_handler)

stdout = getLogger('captain.echo.stdout')
if len(stdout.handlers) == 0:
    stdout.propagate = False
    stdout.setLevel(DEBUG)
    stdout.addHandler(log_handler)

istdout = getLogger('captain.echo.istdout')
if len(istdout.handlers) == 0:
    istdout.propagate = False
    istdout.setLevel(DEBUG)
    log_handler = StreamHandler(stream=InlineStream(sys.stdout))
    log_handler.setFormatter(log_formatter)
    istdout.addHandler(log_handler)


class LevelFilter(object):
    def __init__(self, levels):
        self.levels = set(levels.upper())
        self.__level = NOTSET
    def filter(self, logRecord):
        #pout.v(logRecord.levelname[0], self.levels)
        return logRecord.levelname[0].upper() not in self.levels


def inject_quiet(levels):
    """see --quiet flag help for what this does"""
    loggers = list(Logger.manager.loggerDict.items())
    loggers.append(("root", getLogger()))
    level_filter = LevelFilter(levels)

    for logger_name, logger in loggers:
        for handler in getattr(logger, "handlers", []):
            handler.addFilter(level_filter)

