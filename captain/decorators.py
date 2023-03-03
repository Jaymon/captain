# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from datatypes import classproperty

from .compat import *


def arg(*parser_args, **parser_kwargs):
    """decorator that adds support for the full argparse.ArgumentParser.add_argument
    api

    :Example:
        class Default(Command):
            @arg("--foo", "-f", dest="foo", default=1, help="the foo value")
            def handle(self, foo): pass

        class GroupExample(Command):
            @arg("--foo", group="Foo Bar")
            @arg("--bar", group="Foo Bar")
            @arg("--baz")
            def handle(self, foo_bar, baz):
                # --foo and --bar will be grouped under foo_bar
                print(foo_bar.foo)
                print(foo_bar.bar)

    https://docs.python.org/3/library/argparse.html#the-add-argument-method

    :param *parser_args: name or flags (eg, "--foo", "foo", "-f")
    :param **parser_kwargs: (eg, action, nargs, const, type, required, etc)
        -group: str, if you pass in a group on one or more @arg calls then those
        names will be bundled into that group name parameter
    """
    def wrap(handle_method):
        handle_method.__dict__.setdefault('decorator_args', [])
        handle_method.__dict__['decorator_args'].append((parser_args, parser_kwargs))
        return handle_method
    return wrap 


def args(*subcommands, **kwargs):
    """Decorator that makes another Command's flags active on this command also

    :Example:
        class Foo(Command):
            @arg("--che", "-c", dest="che", default=1, help="the che value")
            def handle(self, che): pass

        class Bar(Command):
            @args(Foo)
            def handle(self, che): pass

    :param *subcommands: class, any Command child
    :param **kwargs:
        - ignore: a list of names you want to ignore from the subcommands, this
            will allow you to remove flags you don't want to inherit
    """
    def wrap(handle_method):
        handle_method.__dict__.setdefault('inherit_args', [])
        #handle_method.__dict__['inherit_args'].extend((reversed(subcommands), kwargs))
        handle_method.__dict__['inherit_args'].append((subcommands, kwargs))
        return handle_method
    return wrap 


