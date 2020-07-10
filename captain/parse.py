# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import argparse
import textwrap
from collections import defaultdict
import re

from .compat import *
from . import environ
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

    HELP_QUIET = ''.join([
        'Selectively turn off [D]ebug, [I]nfo, [W]arning, [E]rror, or [C]ritical, ',
        '(--quiet=DI means suppress Debug and Info), ',
        'use - to invert (--quiet=-EW means suppress everything but Error and warning), ',
        'use + to change default (--quiet=+D means remove D from default value)',
    ])

    HELP_Q_LOWER = ''.join([
        'Turn off [D]ebug (-q), [I]nfo (-qq), [W]arning (-qqq), [E]rror (-qqqq), ',
        'and [C]ritical (-qqqqq)',
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

        super(QuietAction, self).__init__(option_strings, self.DEST, **kwargs)

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
            pout.v(arg_string)
            arg_string = "-" + arg_string[2:]

        if arg_string.startswith("-"):
            # if we have a subtract then just remove those from being suppressed
            # so -E would only show errors
            arg_string = self.order(set(self.OPTIONS) - set(arg_string[1:].upper()))

        elif arg_string.startswith("+"):
            # if we have an addition then just remove those from default
            # so if default="D" then +D would leave default=""
            arg_string = self.order(set(self.default) - set(arg_string[1:].upper()))

        # this will actually configure the logging
        return QuietFilter(arg_string)
        #return arg_string


    def parse_args(self, parser, arg_strings):
        """This is a hack to allow `--quiet` and `--quiet DI` to work correctly,
        basically it goes through all arg_strings and if it finds --quiet it checks
        the next argument to see if it is some combination of DIWEC, if it is then
        it combines it to `--quiet=ARG` and returns the modified arg_strings list

        :param parser: argparse.ArgumentParser instance
        :param arg_strings: list, the raw arguments
        :returns: list, the arg_strings changed if needed
        """
        if "-q" in self.option_strings: return arg_strings

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
                        new_args.append("{}={}".format(arg_string, self.const))

                    elif re.match(r"^\-?[{}]+$".format(self.const), narg_string):
                        new_args.append("{}={}".format(arg_string, narg_string))
                        i += 1

                    else:
                        new_args.append("{}={}".format(arg_string, self.const))

                else:
                    new_args.append("{}={}".format(arg_string, self.const))

            else:
                new_args.append(arg_string)

            i += 1

        arg_strings = new_args
        return arg_strings


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """The problem I had was ArgumentDefaultsHelpFormatter would give me the default
    values but it would strip newlines from the text, while RawTextHelpFormatter
    would keep the newlines but not give default values and messed up formatting
    of the arguments, so this gives me defaults and also formats most everything

    http://stackoverflow.com/questions/12151306/argparse-way-to-include-default-values-in-help
    https://docs.python.org/2/library/argparse.html#formatter-class
    """
    def _fill_text(self, text, width, indent):
        """Overridden to not get rid of newlines

        https://github.com/python/cpython/blob/2.7/Lib/argparse.py#L620"""
        lines = []
        for line in text.splitlines(False):
            if line:
                # https://docs.python.org/2/library/textwrap.html
                lines.extend(textwrap.wrap(
                    line.strip(),
                    width,
                    initial_indent=indent,
                    subsequent_indent=indent
                ))

            else:
                lines.append(line)

        text = "\n".join(lines)
        return text


class ArgumentParser(argparse.ArgumentParser):

    @classmethod
    def create_instance(cls, command_class, subcommand_classes=None, **kwargs):
        subcommand_classes = subcommand_classes or {}

        common_parser = cls.create_common_instance(**kwargs)

        desc = command_class.reflect().desc if command_class else kwargs.get("default_desc", "")
        parser = cls(
            description=desc,
            parents=[common_parser],
            conflict_handler="resolve",
        )

        if command_class:
            parser.add_handler(command_class)
            rc = command_class.reflect()

            for pa in rc.parseargs():
                parser.add_argument(*pa[0], **pa[1])

        if subcommand_classes:
            # if dest isn't passed in you get "argument None is required" on
            # error in py2.7
            subparsers = parser.add_subparsers(dest="<SUBCOMMAND>")
            #subparsers = parser.add_subparsers()
            subparsers.required = False if command_class else True

            for subcommand_name, subcommand_class in subcommand_classes.items():

                #rc = ReflectCommand(subcommand_class)
                rc = subcommand_class.reflect()
                desc = rc.desc
                subparser = subparsers.add_parser(
                    subcommand_name,
                    parents=[common_parser],
                    help=desc,
                    description=desc,
                    conflict_handler="resolve",
                )
                #subparser.set_defaults(callback=subcommand_class().handle)
                subparser.add_handler(subcommand_class)

                for pa in rc.parseargs():
                    subparser.add_argument(*pa[0], **pa[1])

        return parser

    @classmethod
    def create_common_instance(cls, **kwargs):
        parser = cls(add_help=False)

        # !!! you can't have a normal group and mutually exclusive group
        #group = parser.add_argument_group('Built-in', 'Captain built-in options')

        version = kwargs.get("version", "")
        if version:
            parser.add_argument("--version", "-V", action='version', version="%(prog)s {}".format(version))

        quiet = kwargs.get("quiet", True)
        if quiet:
            # https://docs.python.org/3/library/argparse.html#mutual-exclusion
            me_group = parser.add_mutually_exclusive_group()

            me_group.add_argument(
                '--quiet', '-Q',
                action=QuietAction,
            )

            me_group.add_argument(
                "-q",
                action=QuietAction,
            )

        return parser

    def __init__(self, **kwargs):
        # https://docs.python.org/2/library/argparse.html#conflict-handler
        kwargs.setdefault("formatter_class", HelpFormatter)
        super(ArgumentParser, self).__init__(**kwargs)

    def _get_value(self, action, arg_string):
        """By default, there is no easy way to do something with a value after it
        is set, regardless of it being set by .default, .const, or an actual passed
        in value. This gets around that for custom actions by running get_value()
        if the action has one, it's similar to what we are doing _parse_action_args()

        NOTE -- For some reason this only gets called on default if the value is
        a String, I have no idea why, but a custom action using this needs to have
        string default values
        """
        ret = super(ArgumentParser, self)._get_value(action, arg_string)
        cb = getattr(action, "get_value", None)
        if cb:
            ret = cb(ret)
        return ret

    def _parse_action_args(self, arg_strings):
        """There is no easy way to customize the parsing by default, so this is 
        an attempt to allow customizing, this will go through each action and if
        that action has a parse_args() method it will run it, the signature for the
        handle method is parse_args(parser, arg_strings) return arg_string. This gives
        actions the ability to customize functionality and keeps that customization
        contained to within the action class."""
        for flag, action in self._option_string_actions.items():
            cb = getattr(action, "parse_args", None)
            if cb:
                arg_strings = cb(self, arg_strings)

        return arg_strings

    def _parse_known_args(self, arg_strings, namespace):
        """This and _read_args_from_files() are the two places the arg_strings get
        set, I tried everything to override parser functionality but there just isn't
        any other hook, these are the methods I looked at overriding and none of them
        provided an override opportunity to get me what I needed:

            * _match_argument
            * _get_values
            * _get_option_tuples
            * _parse_optional
            * _match_arguments_partial

        argparse.ArgumentParser._parse_known_args() calls _read_args_from_files()
        but only if a condition is met so you can't just override _read_args_from_files()
        which is a shame, so I have to override both to hook in my overriding functionality
        and make it possible to manipulate the arg_strings
        """
        arg_strings = self._parse_action_args(arg_strings)
        args, unknown_args = super(ArgumentParser, self)._parse_known_args(arg_strings, namespace)
        return args, unknown_args

    def _read_args_from_files(self, arg_strings):
        arg_strings = super(ArgumentParser, self)._read_args_from_files(arg_strings)
        arg_strings = self._parse_action_args(arg_strings)
        return arg_strings

    def parse_handle_args(self, argv):
        """This is our hook to parse all the arguments and get the values that will
        ulimately be passed to the handle() method"""
        unknown_args = []
        unknown_kwargs = {}

        parsed, parsed_unknown = self.parse_known_args(argv)

        if parsed_unknown:
            unknown_kwargs = UnknownParser(parsed_unknown)
            unknown_args = unknown_kwargs.pop("*", [])

            if unknown_args and not parsed._has_handle_args:
                # we parse again with the more restrictive parser to raise the error
                self.parse_args(argv)

            if unknown_kwargs and not parsed._has_handle_kwargs:
                # we parse again with the more restrictive parser to raise the error
                self.parse_args(argv)

        args = []
        tentative_kwargs = dict(vars(parsed)) # convert Namespace instance to dict

        # because of how args works, we need to make sure the kwargs are put in correct
        # order to be passed to the function, otherwise our real *args won't make it
        # to the *args variable
        for name in parsed._handle_signature["names"]:
            args.append(tentative_kwargs.pop(name))

        args.extend(unknown_args)
        tentative_kwargs.update(unknown_kwargs)

        # we want to remove any values from the built-in group since we don't
        # want to pass those to the handle method, any value that begins with an 
        # underscore or is wrapped with <> are stripped from the final args
        # passed to the handle() method, they will still be available in
        # self.parsed though
        kwargs = {}
        for k, v in tentative_kwargs.items():
            # we filter out private (start with _) and placeholder (surrounded by <>) keys
            if not k.startswith("_") and not k.startswith("<"):
                kwargs[k] = v

        return parsed, args, kwargs

    def add_handler(self, command_class):
        rc = command_class.reflect()
        sig = rc.method().signature
        c = command_class()
        self.set_defaults(
            _command_instance=c,
            _has_handle_args=True if sig["*_name"] else False,
            _has_handle_kwargs=True if sig["**_name"] else False,
            _handle_signature=sig,
        )

    def error(self, message):
        # compensate for https://bugs.python.org/issue9253#msg186387 in python2
        if is_py2 and message == "too few arguments":
            return

        super(ArgumentParser, self).error(message)


class UnknownParser(dict):
    """handle parsing any extra args that are passed from ArgParser.parse_known_args """
    def __init__(self, args):
        """
        :param args: list, the list of extra args returned from parse_known_args
        :returns: dict, key is the arg name (* for non positional args) and value is
            a list of found arguments (so --foo 1 --foo 2 is supported). The value is
            always a list
        """
        d = defaultdict(list)
        i = 0
        length = len(args)
        while i < length:
            if args[i].startswith("-"):
                s = args[i].lstrip("-")
                bits = s.split("=", 1)
                if len(bits) > 1:
                    key = bits[0]
                    val = bits[1].strip("\"'")
                    d[key].append(val)

                else:
                    if i + 1 < length:
                        if args[i + 1].startswith("-"):
                            d[s].append(True)

                        else:
                            d[s].append(args[i + 1])
                            i += 1

            else:
                d["*"].append(args[i])

            i += 1

        super(UnknownParser, self).__init__(d)

    def unwrap(self, ignore_keys=None):
        """remove list wrapper of any value that has a count of 1

        by default, this returns lists for everything because it has no idea what
        might have multiple values so it treats everything as if it has multiple values
        so it can support things like `--foo=1 --foo=2` but that might not be wanted,
        so this method will return a dict with any value that has a length of one it
        will remove the list, so `[1]` becomes `1`

        UnknownParse always has array values, let's normalize that so values
        with only one item contain just that item instead of a list of length 1

        :param ignore_keys: list, keys you don't want to strip of the list even if
            it only has one element
        :returns: dict, a dictionary with values unrwapped
        """
        ignore_keys = set(ignore_keys or [])
        ignore_keys.add("*")

        d = {}
        for k in (k for k in d if (len(d[k]) == 1) and k not in ignore_keys):
            d[k] = d[k][0]
        return d


class EnvironParser(UnknownParser):
    def __init__(self, args):
        super(EnvironParser, self).__init__(args)
        for k in list(self.keys()):
            if not re.match(r"^[A-Z0-9_-]+$", k):
                del self[k]


class Extra(object):
    def __init__(self, args):
        self.environ = {} # Environ()
        self.options = {}

        d = UnknownParser(args)
        for k, v in d.items():
            # is this en environment variable?
            if re.match(r"^[A-Z0-9_-]+$", k):
                self.environ[k] = v[0] if len(v) == 1 else v

            else:
                self.options[k] = v[0] if len(v) == 1 else v

