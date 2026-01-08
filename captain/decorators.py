# -*- coding: utf-8 -*-
from datatypes import classproperty

from .compat import *


def arg(*parser_args, **parser_kwargs):
    """decorator that adds support for the full
    argparse.ArgumentParser.add_argument api

    :example:
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
        - group: str, if you pass in a group on one or more @arg calls then
            those names will be bundled into that group name parameter
    """
    def wrap(handle_method):
        handle_method.__dict__.setdefault('decorator_args', [])
        handle_method.__dict__['decorator_args'].append(
            (parser_args, parser_kwargs)
        )
        return handle_method
    return wrap 

