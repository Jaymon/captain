import sys

from datatypes.logging import *


# configure our special loggers
log_formatter = Formatter('%(message)s')
modname = __name__.split(".")[0]


stderr = getLogger('stderr.{}'.format(modname))
if len(stderr.handlers) == 0:
    stderr.propagate = False
    stderr.setLevel(DEBUG)
    errlh = StreamHandler(stream=sys.stderr)
    errlh.terminator = ""
    errlh.setFormatter(log_formatter)
    stderr.addHandler(errlh)


stdout = getLogger('stdout.{}'.format(modname))
if len(stdout.handlers) == 0:
    stdout.propagate = False
    stdout.setLevel(DEBUG)
    outlh = StreamHandler(stream=sys.stdout)
    outlh.terminator = ""
    outlh.setFormatter(log_formatter)
    stdout.addHandler(outlh)


class LevelFilter(object):
    def __init__(self, levels):
        self.levels = set(levels.upper())
        self.__level = NOTSET

    def filter(self, logRecord):
        return logRecord.levelname[0].upper() not in self.levels


class QuietFilter(str):
    """see --quiet flag help for what this does"""
    @classmethod
    def reset(cls):
        """This will go through and remove all the filters that this class
        added to all the logging handlers

        This is mainly for testing
        """
        # https://docs.python.org/3/library/logging.html#handler-objects
        for l, handler in get_handlers():
            for f in list(handler.filters):
                if isinstance(f, LevelFilter):
                    handler.removeFilter(f)

    def __new__(cls, levels, **kwargs):
        levels = levels or ""
        level_filter = LevelFilter(levels)
        for l, handler in get_handlers():
            handler.addFilter(level_filter)

        return super().__new__(cls, levels)

