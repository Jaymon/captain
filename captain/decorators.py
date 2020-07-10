# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from decorators import classproperty

from .compat import *


def arg(*parser_args, **parser_kwargs):
    """decorator that adds support for the full argparse.ArgumentParser.add_argument
    api

    :Example:
        class Default(Command):
            @arg("--foo", "-f", dest="foo", default=1, help="the foo value")
            def handle(self, foo): pass

    https://docs.python.org/3/library/argparse.html#the-add-argument-method

    :param *parser_args: name or flags (eg, "--foo", "foo", "-f")
    :param **parser_kwargs: (eg, action, nargs, const, type, required, etc)
    """
    def wrap(handle_method):
        handle_method.__dict__.setdefault('decorator_args', [])
        handle_method.__dict__['decorator_args'].append((parser_args, parser_kwargs))
        return handle_method
    return wrap 


def args(*subcommands):
    """Decorator that makes another Command's flags active on this command also

    :Example:
        class Foo(Command):
            @arg("--che", "-c", dest="che", default=1, help="the che value")
            def handle(self, che): pass

        class Bar(Command):
            @args(Foo)
            def handle(self, che): pass

    :param *subcommands: class, any Command child
    """
    def wrap(handle_method):
        handle_method.__dict__.setdefault('inherit_args', [])
        handle_method.__dict__['inherit_args'].extend(reversed(subcommands))
        return handle_method
    return wrap 


