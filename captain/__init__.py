# -*- coding: utf-8 -*-

from .interface import Application
from .interface import Command # extend this to create commands/subcommands in your scripts
from .decorators import arg, args
from . import exception
from .exception import Stop, Error


__version__ = "5.0.0"


def application(*args, **kwargs):
    """Factory method to create the Application in order to answer requests

    :Example:
        from captain import application
        if __name__ == "__main__":
            application()

    :returns: Application
    """
    return Application(*args, **kwargs)

