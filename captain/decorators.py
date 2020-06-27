# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import


class classproperty(property):
    """
    allow a class property to exist on the Orm
    NOTE -- this is read only, you can't write to the property

    borrowed from prom.decorators.classproperty

    example --
        class Foo(object):
            @classproperty
            def bar(cls):
                return 42
        Foo.bar # 42
    http://stackoverflow.com/questions/128573/using-property-on-classmethods
    http://stackoverflow.com/questions/5189699/how-can-i-make-a-class-property-in-python
    http://docs.python.org/2/reference/datamodel.html#object.__setattr__
    """
    def __get__(self, instance, cls):
        return self.fget(cls)


def arg(*parser_args, **parser_kwargs):
    def wrap(handle_method):
        handle_method.__dict__.setdefault('decorator_args', [])
        handle_method.__dict__['decorator_args'].append((parser_args, parser_kwargs))
#         handle_method.__dict__['decorator_args'].append({
#             "args": parser_args,
#             "kwargs": parser_kwargs,
#         })
        return handle_method
    return wrap 


def args(*subcommands):
    def wrap(handle_method):
        handle_method.__dict__.setdefault('inherit_args', [])
        handle_method.__dict__['inherit_args'].extend(reversed(subcommands))
        return handle_method
    return wrap 


