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
                    _pathfinder_node=n,
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

    def _create_command(self, node: Pathfinder) -> Command:
        """Internal method to this class. Creates the command instance that
        will be ran"""
        node_value = node.value
        command_class = node_value["command_class"]
        return command_class(
            application=self,
            parser=node_value["parser"],
        )

    async def call(self, *args, **kwargs) -> int:
        """Run Command with `args` and `kwargs` instead of an `argv` list

        :example:
            # call the "foo bar" command from self
            self.call("foo", "bar", che=<VALUE>)

            # call the Default top level command
            self.call()

        :arguments *args: These should contain the subparsers you want to call
        :keywords **kwargs: passed through to the found (sub)command
        """
        args = list(args)
        parser = self.parser
        subparser = parser._subparsers
        while subparser and args:
            action = subparser._group_actions[0]

            if args[0] in action._name_parser_map:
                k = args.pop(0)
                parser = action._name_parser_map[k]
                subparser = parser._subparsers

            else:
                break

        command = self._create_command(parser._defaults["_pathfinder_node"])
        return await command.run(*args, **kwargs)

    async def run(self, argv: list[str]|None = None) -> int:
        """Actually run captain with the given argv

        :param argv: list, sys.argv, basically the passed in arguments, if
            these are passed in then it is assumed they won't contain the
            script name, if not passed in then sys.argv[1:] will be used
        :returns: int, the return code you want the script to exit with
        """
        parsed = self.parser.parse_args(argv)
        command = self._create_command(parsed._pathfinder_node)
        args, kwargs = await command.get_parsed_params(parsed)
        return await command.run(*args, **kwargs)

    def __call__(self, argv: list[str]|None = None):
        ret_code = asyncio.run(self.run(argv))
        sys.exit(ret_code)

