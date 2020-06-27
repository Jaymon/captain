# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys

from .interface import Captain
from .interface import Command # extend this to create commands/subcommands in your scripts
from .decorators import arg, args
from . import exception
from .exception import Stop, Error


__version__ = "4.0.0"


handle = Captain.get_instance().handle # call this at the end of your script

