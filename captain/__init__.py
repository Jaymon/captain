# -*- coding: utf-8 -*-

from .interface import Application
from .interface import Command
from .decorators import arg
from .reflection import Argument
from . import exception
from .exception import Stop, Error


__version__ = "6.0.0"


def application(*args, **kwargs):
    """Factory method to create and call the Application in order to answer
    CLI requests

    :example:
        from captain import application

        if __name__ == "__main__":
            application()
    """
    Application(*args, **kwargs)()

