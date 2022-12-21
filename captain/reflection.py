# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import re
import inspect
import types
import argparse

from .compat import *


class ReflectCommand(object):
    """Provides some handy helper introspection methods for dealing with the Command
    class"""
    @property
    def desc(self):
        """Get the description for the command

        this will first try and get the comment for the handle() method, if that
        fails then it will try the Command class, if that fails it will try to get
        the module's docblock
        """
        def get_desc(o):
            desc = ""
            comment_regex = re.compile(r"^\s*#\s*", flags=re.M)

            desc = inspect.getdoc(o)
            if not desc:
                desc = inspect.getcomments(o)
                if desc:
                    desc = comment_regex.sub("", desc).strip()
                    desc = re.sub(r"^(?:\s*#\s*)?\-\*\-.*", "", desc, flags=re.M).strip()

            return desc

        desc = get_desc(self.command_class.handle)
        if not desc:
            desc = get_desc(self.command_class)
            if not desc:
                desc = get_desc(self.command_class.module)

        if not desc:
            desc = ""

        return desc

    def __init__(self, command):
        self.command_class = command if inspect.isclass(command) else command.__class__

    def method(self, method_name="handle"):
        return ReflectMethod(self.command_class.handle)

    def parseargs(self):
        """yield all the ParseArg instances of the arguments defined for this command"""
        for pa in self.method().parseargs():
            yield pa


class ReflectMethod(object):
    @property
    def signature(self):
        """Get the call signature of the reflected method"""
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
        """Iterate through all the @arg decorator calls

        :returns: generator, this will yield in the order the @arg were added from
            top to bottom
        """
        args = reversed(self.method.__dict__.get('decorator_args', []))
        return args

    def inherit_args(self):
        """Iterate through all the @args decorator calls

        :returns: generator, this will yield in the order the @args were added from
            top to bottom
        """
        args = reversed(self.method.__dict__.get('inherit_args', []))
        return args

    def __init__(self, method):
        self.method = method

    def parseargs(self):
        """Return all the ParseArg instances that should be added to the ArgumentParser
        instance that will validate all the arguments that want to be passed to
        this method

        :returns: generator<ParseArg>, all the found arguments for this method
        """
        sig = self.signature
        pas = {}

        # the values injected via @args decorator
        iargs = self.inherit_args()
        for command_classes, kw in iargs:
            ignore = set(kw.get("omit", kw.get("remove", kw.get("ignore", []))))
            for command_class in command_classes:
                for pa in command_class.reflect().method().parseargs():
                    # ignore any arguments that are in the ignore set
                    if not (ignore & pa.names):
                        pa.merge_signature(sig)
                        pas[pa.name] = pa

        # the values injected via @arg decorator
        dargs = self.decorator_args()
        for a, kw in dargs:
            pa = ParseArg(*a, **kw)
            pa.merge_signature(sig)
            if pa.name in pas:
                pas[pa.name].merge(pa)
            else:
                pas[pa.name] = pa

        return pas.values()


class ParseArg(tuple):
    """This class gets all the *args and **kwargs together to be passed to an
    argparse.ArgumentParser.add_argument() call, this combines the signature values
    with the @arg() arguments to get a comprehensive set of values that will be
    passed to add_argument

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
                if self.is_named():
                    self.name = n
                    self[1]["dest"] = n

                if n in sig["defaults"]:
                    self.set_default(sig["defaults"][n])

    def merge(self, pa):
        """Merge another ParseArg instance into this one

        :param pa: ParseArg instance, any pa.args that are not in self.args will
            be added, pa.args does not override self.args, pa.kwargs keys will
            overwrite self.kwargs keys
        """
        sa = set(self.args)
        for a in pa.args:
            if a not in sa:
                self.args.append(a)

        # passed in ParseArg kwargs take precedence
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

            if is_named and len(ns) > 1:
                for n2 in (ns.replace('_', '-'), ns.replace('-', '_')):
                    if n2 not in names:
                        self[0].append("--{}".format(n2))
                        names.add(n2)

        # we need to compensate for: "ValueError: dest supplied twice for positional argument"
        # It looks like if there is one arg and it is a positional (eg, no -- prefix)
        # then it will use that as the dest and you can't set a dest kwarg
        # https://docs.python.org/3/library/argparse.html#dest
        dest = self[1].get("dest", "")
        if dest:
            names.add(dest)
            self.name = dest
            if not is_named:
                # ok, we have a positional and a dest, that will fail, so let's
                # do some manipulation
                self[1].setdefault("metavar", self[0][0])
                self[0][0] = dest
                self[1].pop("dest")

        else:
            if is_named:
                self[1].setdefault("dest", longest_name.replace('-', '_'))
            self.name = longest_name

        self.names = names

    def set_default(self, val):
        """this is used for introspection from the signature when there is an
        argument with a default value, this figures out how to set up the add_argument
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

