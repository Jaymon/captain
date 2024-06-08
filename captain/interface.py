# -*- coding: utf-8 -*-
import sys
import asyncio

from .compat import *
from .parse import Router
from .call import Command, PrintHelpCommand
from .config import environ


class Application(object):
    """The application is the entry point into running a Command child, this
    tries to have a similar interface for CLI as ASGI/WSGI

    :Example:
        # __main__.py
        from captain import Application

        application = Application()

        if __name__ == "__main__":
            application()
    """
    command_class = Command
    """The base Comamnd class that will be used to retrieve the
    .command_classes class variable"""

    command_default_class = PrintHelpCommand
    """The default command class that will be used for undefined subcommands
    """

    router_class = Router
    """The router class that converts the passed in arg strings into a
    callable command class"""

    def create_router(self):
        return self.router_class(
            command_class=self.command_class,
            command_default_class=self.command_default_class,
            command_prefixes=self.command_prefixes,
        )

    def __init__(self, command_prefixes=None):
        """Create the application interface that binds the CLI comamnd string
        to the captain commands

        :param command_prefixes: list[str]|str, a command prefix is a module
            path where Command definitions can be found
        """
        if command_prefixes is None:
            self.command_prefixes = environ.get_command_prefixes()

        else:
            if isinstance(command_prefixes, str):
                command_prefixes = environ.split_value(command_prefixes)

            self.command_prefixes = command_prefixes

        self.router = self.create_router()

    async def run(self, argv=None):
        """Actually run captain with the given argv

        :param argv: list, sys.argv, basically the passed in arguments, if
            these are passed in then it is assumed they won't contain the
            script name, if not passed in then sys.argv[1:] will be used
        :returns: int, the return code you want the script to exit with
        """
        router = self.create_router()
        command = router.create_command(argv)
        return await command.run()

    def __call__(self):
        ret_code = asyncio.run(self.run())
        sys.exit(ret_code)

