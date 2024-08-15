# -*- coding: utf-8 -*-
import argparse
import textwrap
import os
import re
import sys
from collections import defaultdict

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

#     def _metavar_formatter(self, action, default_metavar):
#         """Overrides the default formatter in order hide the aliases
# 
#         https://github.com/python/cpython/blob/3.11/Lib/argparse.py#L1189
# 
#         NOTE -- this relies on knowing how the parent's version of this
#         method works and duck types the action to get the desired output
#         """
#         if isinstance(action, argparse._SubParsersAction._ChoicesPseudoAction):
#             fake_action = argparse.Namespace(
#                 metavar=None,
#                 choices=None,
#             )
# 
#         elif isinstance(action, argparse._SubParsersAction):
#             choices = set()
#             for parser in action.choices.values():
#                 if parser._defaults["_parser_name"]:
#                     choices.add(parser._defaults["_parser_name"])
# 
#             choices = list(choices)
#             choices.sort()
# 
#             fake_action = argparse.Namespace(
#                 metavar=None,
#                 choices=choices,
#             )
# 
#         else:
#             fake_action = action
# 
#         return super()._metavar_formatter(fake_action, default_metavar)

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



class Pathfinder(DictTree):
    """Internal class to Router. This handles setting the subcommand hierarchy,
    this is used to create all the parsers in the Router.
    """
    def __init__(self, command_prefixes, command_class):
        """
        :param command_prefixes: list[str]
        :param command_class: Command, this is used internally to check
            subclass suitability
        """
        super().__init__()

        self.command_prefixes = command_prefixes
        self.command_class = command_class

        self.set([], self._get_node_value())

    def create_instance(self):
        """Internal method that makes sure creating sub-instances of this
        class when creating nodes doesn't error out"""
        return type(self)(
            self.command_prefixes,
            self.command_class
        )

    def _get_node_key(self, key):
        """Internal method. Get the normalized key and possible aliases for
        the key

        :param key: str, this will be normalized
        :returns: tuple(str, set[str]), the actual key value figured out from
            the passed in key and then all the potential aliases for that
            key
        """
        nc = NamingConvention(key)
        return nc.kebabcase(), nc.variations()

    def _get_node_value(self, **kwargs):
        """Internal method. Gets the node value"""
        value = {
            "command_class": self.command_class,
            "parser": None,
            "subparsers": None,
            "aliases": set(),
            **kwargs
        }

        if issubclass(value["command_class"], self.command_class):
            if aliases := value["command_class"].aliases:
                value["aliases"] = aliases

        else:
            value["command_class"] = self.command_class

        return value

    def _get_node_values(self, classpath, command_class):
        """Internal method. This yields the keys and values that will be
        used to create new nodes in this tree

        :param classpath: str, the full modpath:classpath
        :returns: generator[tuple(list[str], dict)]
        """
        rn = ReflectName(classpath)
        keys = []

        for command_prefix in self.command_prefixes:
            if classpath.startswith(command_prefix):
                for modname in rn.relative_module_parts(command_prefix):
                    key, aliases = self._get_node_key(modname)
                    value = self._get_node_value(aliases=aliases)
                    keys.append(key)
                    yield keys, value

                break

        # we can't use rn.get_classes() here because classpath could be
        # something like: `<run_path>:ClassPrefix.Command` and so we can't
        # actually get the module
        command_class_i = len(rn.class_names) - 1
        for i, class_name in enumerate(rn.class_names):

            node_kwargs = {}
            if command_class_i == i:
                node_kwargs["command_class"] = command_class

            if class_name == "Default":
                value = self._get_node_value(**node_kwargs)

            else:
                key, aliases = self._get_node_key(class_name)
                node_kwargs["aliases"] = aliases
                keys.append(key)
                value = self._get_node_value(**node_kwargs)

            yield keys, value

    def add_class(self, classpath, command_class):
        """This is the method that is called from Router.create_pathfinder

        :param classpath: str, the full modpath:classpath
        """
        for keys, value in self._get_node_values(classpath, command_class):
            self.set(keys, value)


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
        self.pathfinder_class = kwargs.get("pathfinder_class", Pathfinder)

        self.parser = self.create_parser(**kwargs)

    def create_command(self, argv=None):
        """This command is used by the Application instance to get the
        command that will ultimately handle the request

        :param argv: list[str], a list of argument strings, if this isn't
            passed in then it will use sys.argv
        :returns: Command
        """
        parsed = self.parser.parse_args(argv)
        return parsed._command_class(parsed)

    def create_parsers(self, common_parser):
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

        for keys, n in self.pathfinder.nodes():
            value = n.value
            parser = value["parser"]
            subcommand = keys[-1] if keys else ""
            if not parser:
                command_class = value["command_class"]
                desc = command_class.reflect().get_help(self.command_class)
                version = command_class.version

                if parent_n := n.parent:
                    subparsers = parent_n.value["subparsers"]
                    if not subparsers:
                        subparsers = parent_n.value["parser"].add_subparsers()
                        parent_n.value["subparsers"] = subparsers

                    parser = subparsers.add_parser(
                        subcommand,
                        parents=[common_parser],
                        help=desc,
                        description=desc,
                        conflict_handler="resolve",
                        aliases=value["aliases"],
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
                value["parser"] = parser

            parsers.append(parser)

        return parsers

    def create_parser(self, **kwargs):
        """This creates and returns the root parser"""
        self.load_commands(**kwargs)
        self.pathfinder = self.create_pathfinder(**kwargs)
        common_parser = self.create_common_parser(**kwargs)
        self.create_parsers(common_parser)
        return self.pathfinder.value["parser"]

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
        pathfinder = self.pathfinder_class(
            self.command_prefixes,
            self.command_class
        )

        command_classes = self.command_class.command_classes
        for classpath, command_class in command_classes.items():
            pathfinder.add_class(classpath, command_class)

        return pathfinder



class SubParsersAction(argparse._SubParsersAction):
#     @property
#     def choices(self):
#         pout.h()
#         return self._name_parser_map
# 
#     @choices.setter
#     def choices(self, v):
#         pass

    def __init__(self, *args, **kwargs):
        self._alias_map = {}
        super().__init__(*args, **kwargs)

    def add_parser(self, name, **kwargs):
        """
        https://github.com/python/cpython/blob/3.11/Lib/argparse.py#L1189
        """
        self._alias_map[name] = kwargs.pop("aliases", [])
        return super().add_parser(name, **kwargs)

#         parser = super().add_parser(name, **kwargs)
# 
# #         for alias in aliases:
# #             self._alias_map[alias] = name
# 
#         self._alias_map[name] = aliases
# 
# #         for alias in aliases:
# #             self._name_parser_map[alias] = parser
# 
#         return parser

#     def __call__(self, parser, namespace, values, option_string=None):
# 
#         #pout.v(namespace, values, option_string)
#         pout.h()
# 
#         return super().__call__(parser, namespace, values, option_string)

    def get_arg_string(self, name):
        if name not in self._alias_map:
            for n, aliases in self._alias_map.items():
                if name in aliases:
                    name = n
                    break

        return name


class ArgumentParser(argparse.ArgumentParser):
    """This class is used to create parsers in Router and shouldn't ever be
    used outside of the Router context

    https://github.com/python/cpython/blob/3.11/Lib/argparse.py
    """
    def __init__(self, **kwargs):
        # https://docs.python.org/3/library/argparse.html#conflict-handler
        self.command_class_added = False

        kwargs.setdefault("formatter_class", HelpFormatter)
        super().__init__(**kwargs)

        self.register('action', 'parsers', SubParsersAction)

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

        cb = getattr(action, "get_arg_string", None)
        if cb:
            arg_string = cb(arg_string)

#         if isinstance(action, SubParsersAction):
#             arg_string = action.get_name(arg_string)

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
        self.add_command_arguments(self._defaults["_command_class"])

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

    def add_command_arguments(self, command_class):
        """All the defined Command arguments will be added through this
        method, this is automatically called when .parse_known_args is called

        This adds arguments to self from @arg, @args, and Argument class
        properties. These arguments aren't all added on parser creation
        because that would be a lot of work if you have a lot of parsers, so
        it is done at the last possible moment when the correct parser has
        been chosen

        :param command_class: Command, this is the Command subclass that is
            going to be added to this parser
        """
        if self.command_class_added:
            return

        self.command_class_added = True
        _groups = {} # holds the arguments that belong to each group
        sig = {}
        _arg_count = 0
        pa_actions = []

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
                    action = self.add_argument(*pa[0], **pa[1])
                    pa_actions.append((pa, action))

        # now that all the arguments have been set and the actions created
        # let's add variations, we don't do this earlier so we don't risk
        # overriding a valid user defined flag with our computed alternatives
        for pa, action in pa_actions:
            # add the variations for this argument, this allows
            # --foo_bar to work for foo-bar but they won't appear
            # in the help output
            if action.option_strings:
                for name in pa.names:
                    if len(name) == 1:
                        flag = f"-{name}"

                    else:
                        flag = f"--{name}"

                    if flag not in self._option_string_actions:
                        # see the ._add_action method for how I figured this
                        # out
                        self._option_string_actions[flag] = action

        self.set_defaults(
            _command_class=command_class,
            _has_handle_args=True if sig.get("*_name") else False,
            _has_handle_kwargs=True if sig.get("**_name") else False,
            _handle_signature=sig,
            _arg_count=_arg_count,
            _groups=_groups,
        )

    def add_argument(self, *args, **kwargs):
        """Overrides parent to allow for environment names to be placed into
        the option_strings, an environ_name is an option_string that begins
        with the money sign (eg "$FOO") and it means that value can be sourced
        from the environment

        add_argument([dest|environ_name], ..., name=value, ...)
        add_argument([option_string|environ_name], ..., name=value, ...)

        Precedence order:

            1. A passed in optional/positional
            2. An environment variable
            3. The default value of the argument

        :param *args: tuple[str, ...]
            The dest name for a positional argument (eg "foo").
            The option string (eg "--foo")
            The environ name (eg "$FOO")
        :param **kwargs: all the keyword settings for this argument
        """
        flags = []
        environ_names = []
        for i, arg in enumerate(args):
            if arg[0] == "$":
                environ_names.append(arg[1:])

            else:
                flags.append(arg)

        environ = kwargs.pop("environ", os.environ)
        for environ_name in environ_names:
            if environ_name in environ:
                kwargs["default"] = environ[environ_name]

        return super().add_argument(*flags, **kwargs)

#     def _check_value(self, action, value):
#         pout.v(type(action), value)
#         return super()._check_value(action, value)

#     def _get_value(self, action, arg_string):
#         #pout.v(type(action), arg_string)
# 
#         if isinstance(action, SubParsersAction):
#             arg_string = action.get_name(arg_string)
# 
#         return super()._get_value(action, arg_string)

