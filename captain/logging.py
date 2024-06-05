# -*- coding: utf-8 -*-
import sys
import io

from logging import *
from .compat import *


class InlineStream(io.IOBase):
    """A default python logger always adds a newline, this stream, when passed
    to a StreamHandler will strip that added newline"""
    @property
    def stream(self):
        """NOTE -- I do this round about way for testing, if I set the stream
        directly then testdata.capture can't capture the stream"""
        return getattr(sys, self.name)

    def __init__(self, name):
        """
        :param name: string, values are either "stdout" or "stderr"
        """
        self.name = name
        #self.stream = stream

    def write(self, v):
        # strip off the last newline
        if v[-1] == "\n":
            v = v[:-1]
        ret = self.stream.write(v)

        try:
            self.stream.flush()

        except AttributeError:
            # our wrapped stream doesn't support the full io protocol, flush
            # isn't mandatory though so no need to propagate the error
            pass

        return ret
        #return sys.stdout.write(v)

    def __getattr__(self, k):
        return getattr(self.stream, k)


# configure our special loggers
log_formatter = Formatter('%(message)s')
modname = __name__.split(".")[0]


stderr = getLogger('stderr.{}'.format(modname))
if len(stderr.handlers) == 0:
    stderr.propagate = False
    stderr.setLevel(DEBUG)
    errlh = StreamHandler(stream=InlineStream("stderr"))
    errlh.setFormatter(log_formatter)
    stderr.addHandler(errlh)


stdout = getLogger('stdout.{}'.format(modname))
if len(stdout.handlers) == 0:
    stdout.propagate = False
    stdout.setLevel(DEBUG)
    outlh = StreamHandler(stream=InlineStream("stdout"))
    outlh.setFormatter(log_formatter)
    stdout.addHandler(outlh)


class LevelFilter(object):
    def __init__(self, levels):
        self.levels = set(levels.upper())
        self.__level = NOTSET

    def filter(self, logRecord):
        return logRecord.levelname[0].upper() not in self.levels


class QuietFilter(String):
    """see --quiet flag help for what this does"""
    @classmethod
    def reset(cls):
        """This will go through and remove all the filters that this class
        added to all the logging handlers

        This is mainly for testing
        """
        loggers = Logger.manager.loggerDict
        for logger_name, logger in loggers.items():
            # https://docs.python.org/3/library/logging.html#handler-objects
            for handler in getattr(logger, "handlers", []):
                for f in list(handler.filters):
                    if isinstance(f, LevelFilter):
                        handler.removeFilter(f)

    def __new__(cls, levels, **kwargs):
        levels = levels or ""
        loggers = Logger.manager.loggerDict
        if "root" not in loggers:
            loggers["root"] = getLogger()

        level_filter = LevelFilter(levels)

        for logger_name, logger in loggers.items():
            for handler in getattr(logger, "handlers", []):
                handler.addFilter(level_filter)

        return super().__new__(cls, levels)

