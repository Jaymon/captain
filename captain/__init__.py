# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import logging

from .interface import Captain
from .interface import Command # extend this to create commands/subcommands in your scripts
from .decorators import arg, args
from . import exception
from .exception import Stop, Error


__version__ = "4.0.0"


# get rid of "No handler found" warnings (cribbed from requests)
logging.getLogger(__name__).addHandler(logging.NullHandler())


handle = Captain.get_instance().handle # invoke this at the end of your script

