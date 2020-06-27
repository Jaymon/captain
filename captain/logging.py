# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import io

from logging import *
from .compat import *


class InlineStream(io.IOBase):
    @property
    def stream(self):
        """NOTE -- I do this round about way for testing, if I set the stream
        directly then testdata.capture can't capture the stream"""
        return getattr(sys, self.name)

    def __init__(self, name):
        self.name = name
        #self.stream = stream

    def write(self, v):
        # strip off the last newline
        if v[-1] == "\n":
            v = v[:-1]
        ret = self.stream.write(v)
        self.stream.flush()
        return ret
        #return sys.stdout.write(v)

    def __getattr__(self, k):
        return getattr(self.stream, k)


# configure our special loggers
log_formatter = Formatter('%(message)s')
#log_handler = StreamHandler(stream=sys.stdout)
#log_handler.setFormatter(log_formatter)


stderr = getLogger('{}.stderr'.format(__name__))
if len(stderr.handlers) == 0:
    stderr.propagate = False
    stderr.setLevel(DEBUG)
    #errlh = StreamHandler(stream=InlineStream(sys.stderr))
    errlh = StreamHandler(stream=InlineStream("stderr"))
    errlh.setFormatter(log_formatter)
    stderr.addHandler(errlh)


stdout = getLogger('{}.stdout'.format(__name__))
if len(stdout.handlers) == 0:
    stdout.propagate = False
    stdout.setLevel(DEBUG)
    #outlh = StreamHandler(stream=InlineStream(sys.stdout))
    outlh = StreamHandler(stream=InlineStream("stdout"))
    outlh.setFormatter(log_formatter)
    stdout.addHandler(outlh)


# istdout = getLogger('{}.istdout'.format(__name__))
# if len(istdout.handlers) == 0:
#     istdout.propagate = False
#     istdout.setLevel(DEBUG)
#     log_handler = StreamHandler(stream=InlineStream(sys.stdout))
#     log_handler.setFormatter(log_formatter)
#     istdout.addHandler(log_handler)
# 


class LevelFilter(object):
    def __init__(self, levels):
        self.levels = set(levels.upper())
        self.__level = NOTSET

    def filter(self, logRecord):
        #pout.v(logRecord.levelname[0], self.levels)
        return logRecord.levelname[0].upper() not in self.levels
        #print(logRecord.levelname[0].upper())
        #print(self.levels)
        #return logRecord.levelname[0].upper() in self.levels


class QuietFilter(String):
    """see --quiet flag help for what this does"""
    def __new__(cls, levels, **kwargs):
        #print("QuietFilter.levels: ", levels)
        #pout.v("QuietFilter.levels: {}".format(levels))
        levels = levels or ""
        loggers = dict(Logger.manager.loggerDict)
        if "root" not in loggers:
            loggers["root"] = getLogger()

        level_filter = LevelFilter(levels)

        for logger_name, logger in loggers.items():
            for handler in getattr(logger, "handlers", []):
                handler.addFilter(level_filter)

        return super(QuietFilter, cls).__new__(cls, levels)

