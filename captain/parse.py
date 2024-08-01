# -*- coding: utf-8 -*-
import argparse
import textwrap
import re
import sys

from datatypes import (
    ArgvParser as UnknownParser,
    NamingConvention,
    Dirpath,
    ReflectModule,
    ReflectPath,
    ReflectName,
    DictTree,
)

from .compat import *
from .call import Command
from .config import environ
from .logging import QuietFilter


class QuietAction(argparse.Action):
    """Unless overridden, every captain command gets quiet flag support, this 
    will turn off/on loggers at different levels:

        D - DEBUG
        I - INFO
        W - WARNING
        E - ERROR
        C - CRITICAL
    """
    OPTIONS = "DIWEC"

    DEST = "<QUIET_INJECT>"

    HELP_QUIET = "".join([
        "Selectively turn off ",
        "[D]ebug, [I]nfo, [W]arning, [E]rror, or [C]ritical, ",
        "(--quiet=DI means suppress Debug and Info), ",
        "use - to invert ",
        "(--quiet=-EW means suppress everything but Error and warning), ",
        "use + to change default ",
        "(--quiet=+D means remove D from default value)",
    ])

    HELP_Q_LOWER = "".join([
        "Turn off ",
        "[D]ebug (-q), [I]nfo (-qq), [W]arning (-qqq), [E]rror (-qqqq), ",
        "and [C]ritical (-qqqqq)",
    ])

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.levels = self.OPTIONS
        kwargs["required"] = False
        if "-q" in option_strings:
            kwargs["nargs"] = 0
            kwargs.pop("default", None)
            kwargs.setdefault("help", self.HELP_Q_LOWER)

        else:
            kwargs["const"] = self.OPTIONS
            kwargs.setdefault("default", environ.QUIET_DEFAULT)
            kwargs.setdefault("help", self.HELP_QUIET)

        super().__init__(option_strings, self.DEST, **kwargs)

    def order(self, options):
        o = []
        for ch in self.OPTIONS:
            if ch in options:
                o.append(ch)
        return "".join(o)

    def __call__(self, parser, namespace, values, option_string=""):
        if option_string.startswith("-q"):
            v = getattr(namespace, self.dest, "")
            if v == "":
                v = self.OPTIONS
            else:
                v = self.order(set(self.OPTIONS) - set(v.upper()))

            v = "-" + v
            values = self.get_value(v)

        else:
            values = self.get_value(values)

        setattr(namespace, self.dest, values)

    def get_value(self, arg_string):
        """Hack only supported by our custom ArgumentParser"""
        if "-q" in self.option_strings:
            arg_string = "-" + arg_string[2:]

        if arg_string.startswith("-"):
            # if we have a subtract then just remove those from being
            # suppressed so -E would only show errors
            arg_string = self.order(
                set(self.OPTIONS) - set(arg_string[1:].upper())
            )

        elif arg_string.startswith("+"):
            # if we have an addition then just remove those from default
            # so if default="D" then +D would leave default=""
            arg_string = self.order(
                set(self.default) - set(arg_string[1:].upper())
            )

        # this will actually configure the logging
        return QuietFilter(arg_string)

    def parse_args(self, parser, arg_strings):
        """This is a hack to allow `--quiet` and `--quiet DI` to work
        correctly, basically it goes through all arg_strings and if it finds
        --quiet it checks the next argument to see if it is some combination
        of DIWEC, if it is then it combines it to `--quiet=ARG` and returns
        the modified arg_strings list

        :param parser: argparse.ArgumentParser instance
        :param arg_strings: list, the raw arguments
        :returns: list, the arg_strings changed if needed
        """
        if "-q" in self.option_strings:
            return arg_strings

        count = len(arg_strings)
        new_args = []
        i = 0
        while i < count:
            arg_string = arg_strings[i]
            if arg_string in self.option_strings:
                if (i + 1) < count:
                    narg_string = arg_strings[i + 1]
                    if narg_string in parser._option_string_actions:
                        # make sure a flag like -D isn't mistaken for a
                        # --quiet value
                        new_args.append(f"{arg_string}={self.const}")

                    elif re.match(rf"^\-?[{self.const}]+$", narg_string):
                        new_args.append(
                            f"{arg_string}={narg_string}"
                        )
                        i += 1

                    else:
                        new_args.append(f"{arg_string}={self.const}")

                else:
                    new_args.append(f"{arg_string}={self.const}")

            else:
                new_args.append(arg_string)

            i += 1

        arg_strings = new_args
        return arg_strings


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """The problem I had was ArgumentDefaultsHelpFormatter would give me the
    default values but it would strip newlines from the text, while
    RawTextHelpFormatter would keep the newlines but not give default values
    and messed up formatting of the arguments, so this gives me defaults and
    also formats most everything

    http://stackoverflow.com/questions/12151306/argparse-way-to-include-default-values-in-help
    https://docs.python.org/2/library/argparse.html#formatter-class

    This is another implementation I found that might handle line wrapping
    better:
        https://gist.github.com/panzi/b4a51b3968f67b9ff4c99459fb9c5b3d
    """
    def _fill_text(self, text, width, indent):
        """Overridden to not get rid of newlines"""
        return "\n".join(self._split_lines(text, width, indent))

    def _metavar_formatter(self, action, default_metavar):
        """Overrides the default formatter in order hide the aliases

        https://github.com/python/cpython/blob/3.11/Lib/argparse.py#L1189

        NOTE -- this relies on knowing how the parent's version of this
        method works and duck types the action to get the desired output
        """
        if isinstance(action, argparse._SubParsersAction._ChoicesPseudoAction):
            fake_action = argparse.Namespace(
                metavar=None,
                choices=None,
            )

        elif isinstance(action, argparse._SubParsersAction):
            choices = set()
            for parser in action.choices.values():
                choices.add(parser._defaults["_parser_name"])

            choices = list(choices)
            choices.sort()

            fake_action = argparse.Namespace(
                metavar=None,
                choices=choices,
            )

        else:
            fake_action = action

        return super()._metavar_formatter(fake_action, default_metavar)

    def _split_lines(self, text, width, indent=""):
        """Overridden to not get rid of newlines

        :param text: str, the text
        :param width: int, how long each line can be
        :param indent: str, not in parent so has to have a default value
        :returns: list[str], the lines no more than width long
        """
        lines = []
        text = textwrap.dedent(text)
        for line in text.splitlines(False):
            if line:
                # https://docs.python.org/2/library/textwrap.html
                lines.extend(textwrap.wrap(
                    line,
                    width,
                    initial_indent=indent,
                    subsequent_indent=indent
                ))

            else:
                lines.append(line)

        return lines


class Router(object):
    """The glue that connects the Application and the passed in arguments
    to the ArgumentParser and the Command instance that will ultimately
    handle the request
    """
    def __init__(self, command_prefixes=None, paths=None, **kwargs):
        self.command_prefixes = command_prefixes or []
        self.paths = paths or []

        self.parser_class = kwargs.get("parser_class", ArgumentParser)
        self.command_class = kwargs.get("command_class", Command)

        self.parser = self.create_parser(**kwargs)

    def create_command(self, argv=None):
        """This command is used by the Application instance to get the
        command that will ultimately handle the reuqest

        :param argv: list[str], a list of argument strings, if this isn't
            passed in then it will use sys.argv
        :returns: Command
        """
        parsed = self.parser.parse_args(argv)
        return parsed._command_class(parsed)

    def create_parsers(self, subcommands, common_parser):
        """Go through subcommands and create all the downstream parsers

        :param subcommands: list[str], the subcommand path to get to the
            final parser. To explain this better, it would be something like
            ["foo", "bar", "che"] meaning on the command line you would have
            to call `<SCRIPT> foo bar che` to reach the `che` parser, but
            `foo` and `bar` need to have parsers also to correctly route to
            `che`
        :param common_parser: argparse.ArgumentParser, the parent parser that
            all the other parser will wrap
        :returns: list[argparse.ArgumentParser]
        """
        parsers = []
        tree = self.pathfinder

        for subcommand in subcommands:
            if subcommand:
                tree = tree[subcommand]

            subcommand_info = tree[""]
            parser = subcommand_info["parser"]
            if not parser:
                version = ""
                desc = ""
                aliases = []
                command_class = subcommand_info["command_class"]
                if command_class:
                    desc = command_class.reflect().get_help(self.command_class)
                    aliases = command_class.aliases
                    version = command_class.version

                if tp := tree.tree_parent:
                    subparsers = tp[""]["subparsers"]
                    if not subparsers:
                        subparsers = tp[""]["parser"].add_subparsers()
                        tp[""]["subparsers"] = subparsers

                    parser = subparsers.add_parser(
                        subcommand,
                        parents=[common_parser],
                        help=desc,
                        description=desc,
                        conflict_handler="resolve",
                        aliases=aliases,
                    )

                else:
                    parser = self.parser_class(
                        description=desc,
                        parents=[common_parser],
                        conflict_handler="resolve",
                    )

                if version:
                    parser.add_argument(
                        "--version", "-V",
                        action='version',
                        version="%(prog)s {}".format(version)
                    )

                parser.set_defaults(
                    _command_class=command_class,
                    _parser_name=subcommand,
                    _parser=parser,
                )
                subcommand_info["parser"] = parser

            parsers.append(parser)

        return parsers

    def create_parser(self, **kwargs):
        """This creates and returns the root parser"""
        self.load_commands(**kwargs)
        self.pathfinder = self.create_pathfinder(**kwargs)

        common_parser = self.create_common_parser(**kwargs)
        for subcommands, subcommand_info in self.pathfinder.leaves():
            self.create_parsers(subcommands, common_parser)

        return self.pathfinder[""]["parser"]

    def create_common_parser(self, **kwargs):
        """Creates the common Parser that all other parsers will use as a base

        This is useful to make sure there are certain flags that can be passed
        both before and after the subcommand. By default, if you had something
        like
        --version, you could do:

            $ script.py --version

        But not:

            $ script.py SUBCOMMAND --version

        This fixes that problem by creating this common instance and using it
        as a base, the subcommand will inherit the common flags/arguments also,
        so the flags will work the same way on the left or right side of the
        SUBCOMMAND

        :param **kwargs:
            - version: str, the version of the script
            - quiet: bool, default is True, pass in False if you don't want the 
              default quiet functionality to be active
        :returns: ArgumentParser
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

    def load_commands(self, **kwargs):
        """All the routing magic happens here"""
        self.command_modules = {}
        seen = set(self.command_modules)

        if self.command_prefixes:
            for command_prefix in self.command_prefixes:
                rm = ReflectModule(command_prefix)
                for m in rm.get_modules():
                    if m.__name__ not in seen:
                        self.command_modules[m.__name__] = m
                        seen.add(m.__name__)

        else:
            if not self.paths:
                if not self.command_class.command_classes:
                    self.paths = [Dirpath.cwd()]

            for path in self.paths:
                rp = ReflectPath(path)
                for m in rp.find_modules(environ.AUTODISCOVER_NAME):
                    if m.__name__ not in seen:
                        rn = ReflectName(m.__name__)
                        command_prefix = rn.absolute_module_name(
                            environ.AUTODISCOVER_NAME
                        )

                        if command_prefix not in seen:
                            self.command_prefixes.append(command_prefix)
                            seen.add(command_prefix)

                        self.command_modules[m.__name__] = m
                        seen.add(m.__name__)

    def create_pathfinder(self, **kwargs):
        """The pathfinder is a DictTree that will always have a "" key to
        represent the command class for that particular tree

        This is used to figure out how routing should happen when you are
        loading a whole bunch of commands modules
        """
        pathfinder = DictTree({
            "": {
                "command_class": None,
                "parser": None,
                "subparsers": None,
            },
        })

        command_classes = self.command_class.command_classes
        for classpath, command_class in command_classes.items():
            rn = ReflectName(classpath)
            subcommands = []

            for command_prefix in self.command_prefixes:
                if classpath.startswith(command_prefix):
                    subcommands = rn.relative_module_parts(command_prefix)
                    break

            if rn.class_name == "Default":
                subcommands.append("")

            else:
                subcommands.extend(rn.class_names)
                subcommands.append("")

            subcommands = [sc.lower() for sc in subcommands]

            pathfinder.set(
                subcommands,
                {
                    "command_class": command_class,
                    "parser": None,
                    "subparsers": None,
                },
            )

            # we want to make sure our datastructure looks the same all the
            # way down the chain
            index = -2
            while scs := subcommands[:index]:
                if "" not in pathfinder.get(scs):
                    scs.append("")
                    pathfinder.set(
                        scs,
                        {
                            "command_class": self.command_class,
                            "parser": None,
                            "subparsers": None,
                        },
                    )

                index -= 1

        return pathfinder


class ArgumentParser(argparse.ArgumentParser):
    """This class is used to create parsers in Router and shouldn't ever be
    used outside of the Router context

    https://github.com/python/cpython/blob/3.11/Lib/argparse.py
    """
    def __init__(self, **kwargs):
        # https://docs.python.org/3/library/argparse.html#conflict-handler
        self.handler_added = False

        kwargs.setdefault("formatter_class", HelpFormatter)
        super().__init__(**kwargs)

    def _get_value(self, action, arg_string):
        """By default, there is no easy way to do something with a value after
        it is set, regardless of it being set by .default, .const, or an actual
        passed in value. This gets around that for custom actions by running
        get_value() if the action has one, it's similar to what we are doing
        _parse_action_args()

        NOTE -- For some reason this only gets called on default if the value
        is a String, I have no idea why, but a custom action using this needs
        to have string default values
        """
        ret = super()._get_value(action, arg_string)
        cb = getattr(action, "get_value", None)
        if cb:
            ret = cb(ret)
        return ret

    def _parse_action_args(self, arg_strings):
        """There is no easy way to customize the parsing by default, so this is
        an attempt to allow customizing, this will go through each action and
        if that action has a parse_args() method it will run it, the signature
        for the handle method is parse_args(parser, arg_strings) return
        arg_string. This gives actions the ability to customize functionality
        and keeps that customization contained to within the action class."""
        seen_flags = set()
        for flag, action in self._option_string_actions.items():
            if flag not in seen_flags:
                if cb := getattr(action, "parse_args", None):
                    arg_strings = cb(self, arg_strings)

                seen_flags.update(action.option_strings)

        return arg_strings

    def _parse_known_args(self, arg_strings, namespace):
        """Overridden to add call to _parse_action_args which allows customized
        actions and makes QuietAction work

        This and _read_args_from_files() are the two places the arg_strings get
        set, I tried everything to override parser functionality but there just
        isn't any other hook, these are the methods I looked at overriding and
        none of them provided an override opportunity to get me what I needed:

            * _match_argument
            * _get_values
            * _get_option_tuples
            * _parse_optional
            * _match_arguments_partial

        argparse.ArgumentParser._parse_known_args() calls
        _read_args_from_files() but only if a condition is met so you can't
        just override _read_args_from_files() which is a shame, so I have to
        override both to hook in my overriding functionality and make it
        possible to manipulate the arg_strings
        """
        arg_strings = self._parse_action_args(arg_strings)
        return super()._parse_known_args(arg_strings, namespace)

    def _read_args_from_files(self, arg_strings):
        """Overridden to add call to _parse_action_args which allows customized
        actions and makes QuietAction work"""
        arg_strings = super()._read_args_from_files(arg_strings)
        arg_strings = self._parse_action_args(arg_strings)
        return arg_strings

    def parse_known_args(self, args=None, namespace=None):
        self.add_handler(self._defaults["_command_class"])

        parsed, parsed_unknown = super().parse_known_args(args, namespace)

        unknown_args = []
        unknown_kwargs = {}

        if parsed_unknown:
            unknown = UnknownParser(
                parsed_unknown,
                hyphen_to_underscore=True,
                infer_type=True,
            )
            unknown_args = unknown.positionals()
            unknown_kwargs = unknown.unwrap_optionals()
            parsed_unknown = []

            if unknown_kwargs:
                if parsed._has_handle_kwargs:
                    for k, v in unknown_kwargs.items():
                        setattr(parsed, k, v)

                else:
                    for k in parsed._handle_signature["names"]:
                        if k in unknown_kwargs:
                            setattr(parsed, k, unknown_kwargs.pop(k))

                    for k, v in unknown_kwargs.items():
                        parsed_unknown.extend(unknown.info[k]["arg_strings"])

            if unknown_args:
                # we try and line our unknown args with names in the handle
                # signature
                for name in parsed._handle_signature["names"]:
                    if unknown_args:
                        if name not in parsed:
                            setattr(parsed, name, unknown_args.pop(0))

                    else:
                        break

                if parsed._has_handle_args:
                    setattr(
                        parsed,
                        parsed._handle_signature["*_name"],
                        unknown_args
                    )

                else:
                    parsed_unknown.extend(unknown_args)

        # re-organize to be in defined groups. If you set a group then you
        # have to use the group in the signature because this makes sure the
        # arguments are grouped into their defined groups
        for groupname, names in parsed._groups.items():
            for name in names:
                if name in parsed:
                    if groupname not in parsed:
                        setattr(parsed, groupname, type(parsed)())

                    setattr(
                        getattr(parsed, groupname),
                        name,
                        getattr(parsed, name)
                    )

                    delattr(parsed, name)

        return parsed, parsed_unknown

    def add_handler(self, command_class):
        """Every Command subclass will be added through this method, this is
        automatically called when .parse_known_args is called

        :param command_class: Command, this is the Command subclass that is
            going to be added to this parser
        """
        if self.handler_added:
            return

        self.handler_added = True
        _groups = {} # holds the arguments that belong to each group
        sig = {}
        _arg_count = 0

        if command_class:
            rc = command_class.reflect()
            sig = rc.method().signature

            groups = {} # holds the group parser instance

            for _arg_count, pa in enumerate(rc.arguments(), 1):
                if pa.group:
                    group = NamingConvention(pa.group)
                    groupname = group.varname()
                    if groupname not in groups:
                        groups[groupname] = self.add_argument_group(group)
                        _groups[groupname] = []

                    groups[groupname].add_argument(*pa[0], **pa[1])
                    _groups[groupname].append(pa.name)

                else:
                    self.add_argument(*pa[0], **pa[1])

        self.set_defaults(
            _command_class=command_class,
            _has_handle_args=True if sig.get("*_name") else False,
            _has_handle_kwargs=True if sig.get("**_name") else False,
            _handle_signature=sig,
            _arg_count=_arg_count,
            _groups=_groups,
        )

