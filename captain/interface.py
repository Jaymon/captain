# -*- coding: utf-8 -*-
import sys
import asyncio

from .compat import *
from .parse import Router
from .call import Command
from .config import environ
from . import logging


logger = logging.getLogger(__name__)


class Application(object):
    command_class = Command

    #parser_class = Parser
    router_class = Router

    @property
    def version(self):
        """Check all the modules of all the commands, first __version__ found
        wins"""
        v = ""
        for command_class in self.commands.values():
            m = command_class.module
            if m:
                v = getattr(m, "__version__", "")
                if v:
                    v = String(v)
                    break
        return v

    def create_router(self):
        return self.router_class(
            command_class=self.command_class,
            command_prefixes=self.command_prefixes,
        )


    def xcreate_parser(self):
        """Create our custom parser that will merge the Command.handle method
        signature and the argument decorator configuration

        :returns: parse.ArgumentParser instance, or whatever class is in
            self.parser_class
        """
        subcommand_classes = dict(Command.command_classes)
        command_class = subcommand_classes.pop(
            "default",
            subcommand_classes.pop("main", None)
        )
        return self.parser_class.create_instance(
            command_class,
            subcommand_classes,
            version=self.version,
            quiet=True,
            default_desc="Captain CLI",
        )

    def __init__(self, command_prefixes=None):
        if command_prefixes is None:
            self.command_prefixes = environ.get_command_prefixes()

        else:
            self.command_prefixes = command_prefixes

        self.router = self.create_router()

    async def run(self, argv=None):
        """Actually run captain with the given argv

        :param argv: list, sys.argv, basically the passed in arguments, if
            these are passed in then it is assumed they won't contain the
            script name, if not passed in then sys.argv[1:] will be used
        :returns: int, the return code you want the script to exit with
        """
        if argv is None:
            argv = sys.argv[1:]

        parser = self.create_parser()
        parsed, args, kwargs = parser.parse_handle_args(argv)
        ret_code = parsed._command_instance.run(*args, **kwargs)
        return ret_code

    def __call__(self):
        ret_code = asyncio.run(self.run())
        sys.exit(ret_code)

