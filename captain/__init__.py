# -*- coding: utf-8 -*-

from .interface import Application
from .interface import Command # extend this to create commands/subcommands in your scripts
from .decorators import arg, args
from . import exception
from .exception import Stop, Error


__version__ = "4.5.0"


#handle = Captain().handle # invoke this at the end of your script

