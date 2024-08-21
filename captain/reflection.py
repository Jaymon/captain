# -*- coding: utf-8 -*-
import re
import inspect
import types
import argparse

from datatypes import (
    NamingConvention,
    ReflectClass,
    ReflectCallable,
)

from .compat import *


class ReflectCommand(ReflectClass):
    """Provides some handy helper introspection methods for dealing with the
    Command class"""
    @property
    def reflect_method_class(self):
        return ReflectMethod

    def reflect_method(self, method_name="handle"):
        return ReflectMethod(self.get(method_name))

    def arguments(self):
        """yield all the Argument instances of the arguments defined for this
        command"""

        # first get all the class property arguments
        pas = self.obj.arguments()
        for pk, pa in pas.items():
            yield pa

        # second get all the method arguments
        for pa in self.reflect_method().arguments():
            yield pa

    def get_docblock(self):
        doc = ""
        if not self.obj.is_private():
            rm = self.reflect_method()
            doc = rm.get_docblock()
            if not doc:
                doc = super().get_docblock()

        return doc


class ReflectMethod(ReflectCallable):
    def decorator_args(self):
        """Iterate through all the @arg decorator calls

        :returns: generator, this will yield in the order the @arg were added
            from top to bottom
        """
        args = reversed(self.obj.__dict__.get('decorator_args', []))
        return args

    def inherit_args(self):
        """Iterate through all the @args decorator calls

        :returns: generator, this will yield in the order the @args were added
            from top to bottom
        """
        args = reversed(self.obj.__dict__.get('inherit_args', []))
        return args

    def arguments(self):
        """Return all the Argument instances that should be added to the
        ArgumentParser instance that will validate all the arguments that want
        to be passed to this method

        :returns: list[Argument], all the found arguments for this method
        """
        pas = {}
        sig = self.get_signature_info()

        # the values injected via @args decorator
        iargs = self.inherit_args()
        for command_classes, kw in iargs:
            ignore = set(
                kw.get("omit", kw.get("remove", kw.get("ignore", [])))
            )
            for command_class in command_classes:
                for pa in command_class.reflect().reflect_method().arguments():
                    # ignore any arguments that are in the ignore set
                    if not (ignore & pa.names):
                        pa.merge_signature(sig)
                        pas[pa.name] = pa

        # the values injected via @arg decorator
        dargs = self.decorator_args()
        for a, kw in dargs:
            pa = Argument(*a, **kw)
            pa.merge_signature(sig)
            if pa.name in pas:
                pas[pa.name].merge(pa)

            else:
                pas[pa.name] = pa

        return pas.values()


class Argument(tuple):
    """This class gets all the *args and **kwargs together to be passed to an
    argparse.ArgumentParser.add_argument() call, this combines the signature
    values with the @arg() arguments to get a comprehensive set of values that
    will be passed to add_argument

    This class is a tuple where self[0] is *args, and self[1] is **kwargs for
    add_argument(), so the call would be: add_argument(*self[0], **self[1])

    https://docs.python.org/3/library/argparse.html#the-add-argument-method
    """
    @property
    def args(self):
        return self[0]

    @property
    def kwargs(self):
        return self[1]

    def __new__(cls, *names, **kwargs):
        group = kwargs.pop("group", None)
        instance = super().__new__(cls, [list(names), kwargs])
        instance.set_names()
        instance.group = group
        return instance

    def __set_name__(self, command_class, name):
        """This is called right after __init__

        https://docs.python.org/3/howto/descriptor.html#customized-names

        This is only called when an instance is created while a class is being
        parsed/created

        :param command_class: type, the class this Argument will belong to
        :param name: str, the argument's public name on the class
        """
        if self.is_named():
            self.name = name
            self[1]["dest"] = name
            self.names.update(NamingConvention(name).variations())

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

        :param sig: dict, a signature in the form of return value of
            ReflectMethod.signature
        """
        for n in sig["names"]:
            if n in self.names:
                if self.is_named():
                    self.name = n
                    self[1]["dest"] = n

                if n in sig["defaults"]:
                    self.set_default(sig["defaults"][n])

    def merge(self, pa):
        """Merge another Argument instance into this one

        :param pa: Argument instance, any pa.args that are not in self.args
            will be added, pa.args does not override self.args, pa.kwargs keys
            will overwrite self.kwargs keys
        """
        sa = set(self.args)
        for a in pa.args:
            if a not in sa:
                self.args.append(a)

        # passed in Argument kwargs take precedence
        self.kwargs.update(pa.kwargs)

    def set_names(self):
        """Find all the possible names for the flag, this normalizes things so
        --foo-bar is the same as --foo_bar"""
        is_named = self.is_named()
        names = set()
        longest_name = ""
        for n in list(self[0]):
            ns = n.strip("-")
            if len(longest_name) < len(ns):
                longest_name = ns

            names.add(ns)
            names.update(NamingConvention(ns).variations())

        if dest := self[1].get("dest", ""):
            self.name = dest
            names.update(NamingConvention(dest).variations())

        else:
            if is_named:
                self[1].setdefault("dest", longest_name.replace('-', '_'))
            self.name = longest_name

        self.names = names

    def set_default(self, val):
        """this is used for introspection from the signature when there is an
        argument with a default value, this figures out how to set up the
        add_argument arguments"""
        kwargs = {}
        if isinstance(val, (type, types.FunctionType)):
            # if foo=some_func then some_func(foo) will be ran if foo is passed
            # in
            kwargs['type'] = val
            kwargs['required'] = True
            kwargs["default"] = argparse.SUPPRESS

        elif isinstance(val, bool):
            # if false then passing --foo will set to true, if True then --foo
            # will set foo to False
            kwargs['action'] = 'store_false' if val else 'store_true'
            kwargs['required'] = False

        elif isinstance(val, (int, float, str)):
            # for things like foo=int, this says that any value of foo is an
            # integer
            kwargs['type'] = type(val)
            kwargs['default'] = val
            kwargs['required'] = False

        elif isinstance(val, (list, set)):
            # list is strange, [int] would mean we want a list of all integers,
            # if there is a value in the list: ["foo", "bar"] then it would
            # mean only those choices are valid
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

