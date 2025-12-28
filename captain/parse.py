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
    NormalizeMixin,
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


class _SubParsersChoices(NormalizeMixin, dict):
    """Internal class used by SubParsersAction. Allows setting aliases to a
    key so that aliases can be used to find subparsers without showing up
    in things like the help output"""
    def __init__(self, *args, **kwargs):
        self.key_lookup = {}
        super().__init__(*args, **kwargs)

    def normalize_key(self, k):
        return self.key_lookup.get(k, k)

    def add_aliases(self, k, aliases):
        for ak in aliases:
            self.key_lookup[ak] = k


class SubParsersAction(argparse._SubParsersAction):
    """This is what is returned from ArgumentParser.add_subparsers and only
    exists to hide aliases from the help output

    https://github.com/python/cpython/blob/3.11/Lib/argparse.py#L793
    https://github.com/python/cpython/blob/3.11/Lib/argparse.py#L1154

    Sadly, we can't just use `._name_parser_map` and add additional keywords,
    so we do this instead and built-in support for calling `.get_arg_string`
    in our ArgumentParser
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # use our custom data structure so we can support aliases without them
        # showing up in the help output
        self._name_parser_map = _SubParsersChoices(self._name_parser_map)
        self.choices = self._name_parser_map

    def add_parser(self, name, aliases: list|None =None, **kwargs):
        """
        https://github.com/python/cpython/blob/3.11/Lib/argparse.py#L1189
        """
        parser = super().add_parser(name, **kwargs)
        if aliases:
            self.choices.add_aliases(name, aliases)

        return parser


class GroupAction(argparse.Action):
    """Mutually exclusive actions with a positional and optional with
    defaults and the same dest will overwrite the optional value with the
    default of the positional, so this custom action makes sure a non-default
    value in the namespace isn't overwritten by a default value
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if self.dest in namespace:
            if values != self.default:
                setattr(namespace, self.dest, values)

        else:
            setattr(namespace, self.dest, values)


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

        # whenever `.add_subparsers` is called without a `parsers` keyword use
        # this class as the default
        self.register('action', 'parsers', SubParsersAction)

    def _get_value(self, action, arg_string):
        """By default, there is no easy way to do something with a value after
        it is set, regardless of it being set by .default, .const, or an actual
        passed in value. This gets around that for custom actions by running
        get_value() if the action has one, it's similar to what we are doing
        with _parse_action_args()

        .. note:: For some reason this only gets called on default if the
        value is a String, I have no idea why, but a custom action using this
        needs to have string default values
        """
        ret = super()._get_value(action, arg_string)

        # see QuietAction
        if cb := getattr(action, "get_value", None):
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

    def _parse_known_args(self, arg_strings, namespace, intermixed=False):
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
        return super()._parse_known_args(
            arg_strings,
            namespace,
            intermixed=intermixed
        )

    def _read_args_from_files(self, arg_strings):
        """Overridden to add call to _parse_action_args which allows customized
        actions and makes QuietAction work"""
        arg_strings = super()._read_args_from_files(arg_strings)
        arg_strings = self._parse_action_args(arg_strings)
        return arg_strings

    def parse_known_args(self, args=None, namespace=None):
        node_value = self._defaults["_pathfinder_node"].value
        command_class = node_value["command_class"]
        self._add_command_arguments(command_class)

        parsed, parsed_unknown = super().parse_known_args(args, namespace)

        if parsed_unknown:
            rm = command_class.reflect().reflect_method()

            unknown = UnknownParser(
                parsed_unknown,
                hyphen_to_underscore=True,
                infer_type=True,
            )

            positionals_name, keywords_name = rm.get_catchall_names()

            if positionals_name or keywords_name:
                if positionals_name:
                    setattr(
                        parsed,
                        positionals_name,
                        unknown.positionals(),
                    )

                if keywords_name:
                    for k, v in unknown.unwrap_keywords().items():
                        setattr(parsed, k, v)

                if not positionals_name:
                    parsed_unknown = unknown.get_positional_strings()

                elif not keywords_name:
                    parsed_unknown = unknown.get_keyword_strings()


                else:
                    parsed_unknown = []

        return parsed, parsed_unknown

    def _add_command_arguments(self, command_class):
        """All the defined Command arguments will be added through this
        method, this is automatically called when .parse_known_args is called

        This adds arguments to self from @arg, and Argument class
        properties. These arguments aren't all added on parser creation
        because that would be a lot of work if you have a lot of parsers, so
        it is done at the last possible moment when the correct (sub)parser
        has been chosen but before it parses the argument strings

        :param command_class: Command, this is the Command subclass that is
            going to be added to this parser
        """
        if self.command_class_added:
            return

        self.command_class_added = True
        pa_actions = []

        rc = command_class.reflect()

        # add class properties
        for pas in rc.get_arguments():
            if len(pas) > 1:
                group = self.add_mutually_exclusive_group(
                    required=("default" not in pas[0][1]),
                )

                for pa in pas:
                    pa[1].setdefault("action", GroupAction)
                    action = group.add_argument(*pa[0], **pa[1])
                    pa_actions.append((pa, action))

            else:
                pa = pas[0]
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
                for keyword in pa.get_keywords():
                    if keyword not in self._option_string_actions:
                        # see the ._add_action method for how I figured this
                        # out
                        self._option_string_actions[keyword] = action

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
                # the environment variable exists so this argument no longer
                # needs to be required
                kwargs.pop("required", None)

        return super().add_argument(*flags, **kwargs)

