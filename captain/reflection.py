# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import re
import inspect
import types
import argparse

from .compat import *


class ReflectCommand(object):
    """Provides some handy helper introspection methods for dealing with the Command
    class

    for the most part, the main command can either be a function or a class instance
    with a __call__, but when inheriting args (using the @args decorator) there are
    actually 2 other types: method and uninstantiated class, this makes sure when
    data is being pulled out of the callback it uses the proper function/method that
    will actually be called when the callback is ran
    """
    @property
    def desc(self):
        def get_desc(o):

            desc = ""
            comment_regex = re.compile(r"^\s*#\s*", flags=re.M)

            if is_py2:
                desc = inspect.getdoc(o)
                if not desc:
                    desc = inspect.getcomments(o)
                    if desc:
                        desc = comment_regex.sub("", desc).strip()
                        desc = re.sub(r"^(?:\s*#\s*)?\-\*\-.*", "", desc, flags=re.M).strip()
                        #desc = re.sub(r"^\s*#!.*$", "", desc, flags=re.M).strip()

            else:
                # avoid method doc inheritance in py >=3.5
                desc = o.__doc__

            return desc

        desc = get_desc(self.command_class.handle)
        if not desc:
            desc = get_desc(self.command_class)
            if not desc:
                desc = get_desc(self.command_class.module)

        if not desc:
            desc = ""

        return desc

#     @property
#     def callable(self):
#         if self.is_instance():
#             ret = self.callback.__call__
#         elif self.is_class():
#             #ret = self.callback.__init__
#             ret = self.callback.__call__
#         else:
#             ret = self.callback
#         return ret

#     @property
#     def handle_signature(self):
#         return ReflectMethod(self.command_class.handle).signature
# 
    def __init__(self, command):
        self.command_class = command if inspect.isclass(command) else command.__class__

    def method(self, method_name="handle"):
        return ReflectMethod(self.command_class.handle)

    def parseargs(self):
        for pa in self.method().parseargs():
            yield pa


#     def get(self, key, default_val=None):
#         if self.is_instance():
#             ret = self.callback.__call__.__dict__.get(key, default_val)
#         elif self.is_class():
#             #ret = self.callback.__init__.__dict__.get(key, default_val)
#             ret = self.callback.__call__.__dict__.get(key, default_val)
#         else:
#             ret = self.callback.__dict__.get(key, default_val)
# 
#         return ret


class ReflectMethod(object):
    @property
    def signature(self):
        #args, args_name, kwargs_name, args_defaults = getfullargspec(self.callable)
        signature = getfullargspec(self.method)
        args = signature[0][1:] # remove self which will always get passed in automatically
        if not args: args = []

        args_default = {}
        if signature[3]:
            start = len(args) - len(signature[3])
            args_default = dict(zip(args[start:], signature[3]))

        args_required = set()
        for arg in args:
            if arg not in args_default:
                args_required.add(String(arg))

        args_name = signature[1]
        kwargs_name = signature[2]

        return {
            "names": list(map(String, args)),
            "required": args_required,
            "defaults": args_default,
            "*_name": String(args_name) if args_name else args_name,
            "**_name": String(kwargs_name) if kwargs_name else kwargs_name,
        }

    def decorator_args(self):
        args = reversed(self.method.__dict__.get('decorator_args', []))
        return args

    def inherit_args(self):
        args = reversed(self.method.__dict__.get('inherit_args', []))
        return args

    def __init__(self, method):
        self.method = method

    def parseargs(self):
        sig = self.signature

        command_classes = self.inherit_args()
        for command_class in command_classes:
            pout.b(command_class.__name__)
            for pa in command_class.reflect().method().parseargs():
                pout.v(pa)
                pa.merge_signature(sig)
                yield pa

        dargs = self.decorator_args()
        for a, kw in dargs:
            pa = ParseArg(*a, **kw)
            pa.merge_signature(sig)
            yield pa


class ParseArg(tuple):

    @property
    def args(self):
        return self[0]

    @property
    def kwargs(self):
        return self[1]

    def __new__(cls, *names, **kwargs):
        instance = super(ParseArg, cls).__new__(cls, [list(names), kwargs])
        instance.set_names()
        return instance

    def is_positional(self):
        return not self.is_named()

    def is_named(self):
        """returns True if argument is a name argument"""
        for n in self[0]:
            if n.startswith("-"):
                return True
        return False

    def merge_signature(self, sig):
        """merge a signature into self

        :param sig: dict, a signature in the form of return value of ReflectMethod.signature
        """
        for n in sig["names"]:
            if n in self.names:

                self.name = n
                self[1]["dest"] = n

                if n in sig["defaults"]:
                    self.set_default(sig["defaults"][n])

    def set_names(self):
        is_named = self.is_named()
        names = set()
        longest_name = ""
        for n in list(self[0]):
            ns = n.lstrip("-")
            if len(longest_name) < len(ns):
                longest_name = ns

            names.add(ns)

            if is_named and len(ns) > 1:
                for n2 in (ns.replace('_', '-'), ns.replace('-', '_')):
                    if n2 not in names:
                        self[0].append("--{}".format(n2))
                        names.add(n2)

        dest = self[1].get("dest", "")
        if dest:
            names.add(dest)

        self.name = dest or longest_name
        self.names = names

    def set_default(self, val):
        """this is used for introspection from the main() method when there is an
        argument with a default value, this figures out how to set up the ArgParse
        arguments"""
        kwargs = {}
        if isinstance(val, (type, types.FunctionType)):
            # if foo=some_func then some_func(foo) will be ran if foo is passed in
            kwargs['type'] = val
            kwargs['required'] = True
            kwargs["default"] = argparse.SUPPRESS

        elif isinstance(val, bool):
            # if false then passing --foo will set to true, if True then --foo will
            # set foo to False
            kwargs['action'] = 'store_false' if val else 'store_true'
            kwargs['required'] = False

        elif isinstance(val, (int, float, str)):
            # for things like foo=int, this says that any value of foo is an integer
            kwargs['type'] = type(val)
            kwargs['default'] = val
            kwargs['required'] = False

        elif isinstance(val, (list, set)):
            # list is strange, [int] would mean we want a list of all integers, if
            # there is a value in the list: ["foo", "bar"] then it would mean only
            # those choices are valid
            val = list(val)
            kwargs['action'] = 'append'
            kwargs['required'] = True

            if len(val) > 0:
                if isinstance(val[0], type):
                    kwargs['type'] = val[0]

                else:
                    # we are now reverting this to a choices check
                    kwargs['action'] = 'store'
                    l = set()
                    ltype = None
                    for elt in val:
                        vtype = type(elt)
                        l.add(elt)
                        if ltype is None:
                            ltype = vtype

                        else:
                            if ltype is not vtype:
                                ltype = str

                    kwargs['choices'] = l
                    kwargs['type'] = ltype

        if kwargs:
            self[1].update(kwargs)


#     def __init__(self, v):
#         super(ParseArg, self).__init__(v)
#         self.





#     def __init__(self, *args, **kwargs):
#         self.args = list(args)
#         self.kwargs = kwargs
# 
#         return super(ParseArg, self).__init__([self.args, self.kwargs])

