# -*- coding: utf-8 -*-
import sys
import asyncio

from datatypes import Dirpath

from .compat import *
#from .parse import Router
from .parse import ArgumentParser, QuietAction
from .reflection import Pathfinder
from .call import Command
from .config import environ


class Application(object):
    """The application is the entry point into running a Command child, this
    tries to have a similar interface for CLI as ASGI/WSGI

    :example:
        # __main__.py
        from captain import Application

        application = Application()

        if __name__ == "__main__":
            application()
    """
    command_class = Command
    """The base Comamnd class that will be used to retrieve the
    .command_classes class variable"""

    parser_class = ArgumentParser

    pathfinder_class = Pathfinder

    #router_class = Router
    """The router class that converts the passed in arg strings into a
    callable command class"""

#    def create_router(self):
#         return self.router_class(
#             command_class=self.command_class,
#             command_prefixes=self.command_prefixes,
#         )

    def __init__(self, command_prefixes=None, paths=None, **kwargs):
        """Create the application interface that binds the CLI comamnd string
        to the captain commands

        :param command_prefixes: list[str]|str, a command prefix is a module
            path where Command definitions can be found
        """
        self.parser_class = kwargs.get("parser_class", self.parser_class)
        self.command_class = kwargs.get("command_class", self.command_class)
        self.pathfinder_class = kwargs.get(
            "pathfinder_class",
            self.pathfinder_class,
        )

        self.command_modules = self._find_modules(
            prefixes=command_prefixes,
            paths=paths,
            **kwargs,
        )

        self.pathfinder = self._create_pathfinder(**kwargs)
        self.parser = self._create_parser(**kwargs)

    def _find_modules(self, prefixes, paths, **kwargs):
        if prefixes is None:
            prefixes = environ.get_command_prefixes()

        else:
            if isinstance(prefixes, str):
                prefixes = environ.split_value(prefixes)

        if not paths and not self.command_class.command_classes:
            paths = [Dirpath.cwd()]

        return self.pathfinder_class.find_modules(
            prefixes,
            paths,
            kwargs.get("autodiscover_name", environ.AUTODISCOVER_NAME),
        )

    def _create_pathfinder(self, **kwargs) -> Pathfinder:
        """Internal method. Create the tree that will be used to resolve a
        requested path to a found controller

        :returns: DictTree, basically a dictionary of dictionaries where each
            key represents a part of a path, the final key will contain the
            controller class that can answer a request
        """
        pathfinder = self.pathfinder_class(
            list(self.command_modules.keys()),
            command_class=self.command_class,
        )

        for command_class in self.command_class.command_classes.values():
            if not command_class.is_private():
                pathfinder.add_class(command_class)

        return pathfinder

    def _create_parser(self, **kwargs) -> ArgumentParser:
        """This creates and returns the root parser

        It goes through subcommands and creates all the downstream parsers.
        When this command is done, every node in `.pathfinder` will have
        a parser set
        """
        common_parser = self._create_common_parser(**kwargs)

        for keys, n in self.pathfinder.nodes():
            value = n.value
            parser = value["parser"]
            subcommand = keys[-1] if keys else ""
            if not parser:
                if parent_n := n.parent:
                    subparsers = parent_n.value["subparsers"]
                    if not subparsers:
                        subparsers = parent_n.value["parser"].add_subparsers()
                        parent_n.value["subparsers"] = subparsers

                    parser = subparsers.add_parser(
                        subcommand,
                        parents=[common_parser],
                        help=value["description"],
                        description=value["description"],
                        conflict_handler="resolve",
                        aliases=value["aliases"],
                    )

                else:
                    parser = self.parser_class(
                        description=value["description"],
                        parents=[common_parser],
                        conflict_handler="resolve",
                    )

                if value["version"]:
                    parser.add_argument(
                        "--version", "-V",
                        action='version',
                        version="%(prog)s {}".format(value["version"])
                    )

                parser.set_defaults(
                    _command_class=value["command_class"],
                    _parser=parser,
                    _parser_node=n,
                    #_application=self,
                )
                value["parser"] = parser

        return self.pathfinder.value["parser"]

    def _create_common_parser(self, **kwargs) -> ArgumentParser:
        """Creates the common Parser that all other parsers will use as a base

        This is useful to make sure there are certain flags that can be passed
        both before and after the subcommand. By default, if you had something
        like a `--version` flag, you could do:

            $ script.py --version

        But not:

            $ script.py SUBCOMMAND --version

        This fixes that problem by creating this common instance and using it
        as a base, the subcommand will inherit the common flags/arguments also,
        so the flags will work the same way on the left or right side of the
        SUBCOMMAND

        :keyword version: str, optional, the version of the script
        :keyword quiet: bool, default is True, pass in False if you don't
            want the default quiet functionality to be active
        """
        parser = self.parser_class(add_help=False)
        # !!! you can't have a normal group and mutually exclusive group

        version = kwargs.get("version", "")
        if not version:
            if m := sys.modules.get("__main__"):
                version = getattr(m, "__version__", "")

        if version:
            parser.add_argument(
                "--version", "-V",
                action='version',
                version="%(prog)s {}".format(version)
            )

        quiet = kwargs.get("quiet", True)
        if quiet:
            # https://docs.python.org/3/library/argparse.html#mutual-exclusion
            me_group = parser.add_mutually_exclusive_group()

            me_group.add_argument(
                "--quiet", "-Q",
                action=QuietAction,
            )

            me_group.add_argument(
                "-q",
                action=QuietAction,
            )

        return parser

#     def create_command(self, argv=None) -> Command:
#         """This command is used by the Application instance to get the
#         command that will ultimately handle the request
# 
#         :param argv: list[str], a list of argument strings, if this isn't
#             passed in then it will use sys.argv
#         :returns: Command
#         """
#         parsed = self.parser.parse_args(argv)
#         return parsed._command_class(parsed)

    async def run(self, argv: list[str]|None = None) -> int:
        """Actually run captain with the given argv

        :param argv: list, sys.argv, basically the passed in arguments, if
            these are passed in then it is assumed they won't contain the
            script name, if not passed in then sys.argv[1:] will be used
        :returns: int, the return code you want the script to exit with
        """
        parsed = self.parser.parse_args(argv)
        command = parsed._command_class(
            parsed=parsed,
            application=self,
            parser=self.parser,
        )
        args, kwargs = await command.get_parsed_params(parsed)
        return await command.run(*args, **kwargs)

    def __call__(self, argv: list[str]|None = None):
        ret_code = asyncio.run(self.run(argv))
        sys.exit(ret_code)

