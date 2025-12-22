# -*- coding: utf-8 -*-
import re
import inspect
import types
import argparse
from collections.abc import Iterable, Generator

from datatypes import (
    NamingConvention,
    ClasspathFinder,
)
from datatypes.reflection import (
    ReflectParam,
    ReflectClass,
    ReflectCallable,
    ReflectModule,
)

from .compat import *


class ReflectCommand(ReflectClass):
    """Provides some handy helper introspection methods for dealing with the
    Command class"""
    def reflect_method(self, method_name="handle"):
        if method_name == "handle":
            return ReflectMethod(self.get(method_name))

        else:
            return super().reflect_method(method_name)

#     def get_command_name(self) -> str:
#         """Get the command name of this class, the reason why this is separate
#         from `.name` is because the command's name can be different than
#         the command name"""
#         return self.get_target().get_name()

    def get_class_arguments(self):
    #def get_arguments(self):
        """Returns all the defined class arguments that will become class
        properties when the command is ran

        :returns: dict[str, Argument], where the key is the name of the 
            property and the value is the Argument information that can be
            used when adding the argument to a parser using
            parser.add_argument
        """
        arg_iter = inspect.getmembers(
            self.get_target(),
            lambda v: isinstance(v, Argument),
        )
        for k, v in arg_iter:
            yield [v]

    def get_arguments(self):
        yield from self.get_class_arguments()
        yield from self.reflect_method().get_arguments()

#     def arguments(self):
#         """yield all the Argument instances of the arguments defined for this
#         command"""
# 
#         # first get all the class property arguments
#         pas = self.get_target().arguments()
#         for pk, pa in pas.items():
#             yield pa
# 
#         # second get all the method arguments
#         for pa in self.reflect_method().arguments():
#             yield pa

    def get_docblock(self):
        doc = ""
        if not self.get_target().is_private():
            rm = self.reflect_method()
            doc = rm.get_docblock()
            if not doc:
                doc = super().get_docblock()

        return doc


class ReflectParam(ReflectParam):
#     def __init__(self, param, reflect_method, **kwargs):
#         super().__init__(param)
# 
#         self.names, self.flags = self.get_argument_params(param)

    def get_argparse_names(self):
        name = self.name
        if self.is_keyword():
            name = NamingConvention(name).cli_keyword()

        names = [name]

        if rt := self.reflect_type():
            for metadata in rt.get_metadata():
                if isinstance(metadata, Mapping):
                    for k in ["aliases", "names"]:
                        if vs := metadata.get(k, []):
                            names.extend(vs)

                    for k in ["alias", "name"]:
                        if v := metadata.get(k, ""):
                            names.append(v)

        return names

#     def get_argparse_keywords(self):
#         flags = super().get_argparse_keywords()
#         pout.v(argparse.ArgumentParser.add_argument)
# 
#         flagset = set()
#         rc = ReflectCallable(argparse.ArgumentParser.add_argument)
#         for param in rc.get_params():
#             flagset.add(param.name)
# 
#         pout.v(flagset)
# 
#         return flags

#     def get_argument_params(self):
#         params
#         names = []
#         flags = {}
# 
#         if param.kind in (param.VAR_POSITIONAL, param.POSITIONAL_ONLY):
#             names.append(param.name)
# 
#         if param.default is param.empty:
#             if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
#                 flags["required"] = False
# 
#             else:
#                 flags["required"] = True
# 
#         else:
#             flags["required"] = False
#             flags["default"] = param.default
# 
#         if param.annotation is param.empty:
#             if param.kind == param.VAR_POSITIONAL:
#                 flags["action"] = "append"
# 
# #                 elif param.kind == param.VAR_KEYWORD:
# #                     flags["type"] = dict
# # 
# #                 else:
# #                     flags["type"] = Any
# 
#         else:
#             flags["type"] = param.annotation
# 
#             rt = self.create_reflect_type(flags["type"])
#             if rt.is_annotated():
#                 for metadata in rt.get_metadata():
#                     if isinstance(metadata, Mapping):
#                         flags.update(metadata)
# 
#                     elif isinstance(metadata, str):
#                         names.extend(filter(None, metadata.split(" ")))
# 
#                     else:
#                         names.extend(metadata)
# 
#         return names, flags


class ReflectMethod(ReflectCallable):
    def _get_decorator_args(self):
        """Iterate through all the @arg decorator calls

        :returns: generator, this will yield in the order the @arg were added
            from top to bottom
        """
        args = reversed(self.get_target().__dict__.get('decorator_args', []))
        return args

#     def reflect_params(self) -> Iterable[ReflectParam]:
#         """This will reflect all params in the method signature"""
#         for param in self.get_params():
#             yield self.create_reflect_param(param)

#     def create_reflect_param(self, *args, **kwargs) -> ReflectParam:
#         kwargs["reflect_method"] = self
#         return kwargs.pop("reflect_param_class", ReflectParam)(
#             *args,
#             **kwargs,
#         )

    def get_arguments(self) -> Generator[tuple]:
        """Return all the Argument instances that should be added to the
        ArgumentParser instance that will validate all the arguments that want
        to be passed to this method

        :returns: list[Argument], all the found arguments for this method
        """
        pas = {}

        param_descs = {}
        if rdoc := self.reflect_docblock():
            param_descs = rdoc.get_param_descriptions()

        for rp in self.reflect_params():
            pa = []
            arg_kwargs = {}
            param = rp.get_target()
            name = rp.name
            nc = NamingConvention(name)

            if name in param_descs:
                arg_kwargs["help"] = param_descs[name]

            if param.default is not param.empty:
                arg_kwargs["default"] = param.default

            if param.kind is param.POSITIONAL_OR_KEYWORD:
                pa = [
                    Argument(
                        nc.cli_positional(),
                        nargs="?",
                        **arg_kwargs,
                    ),
                    Argument(
                        nc.cli_keyword(),
                        dest=name,
                        **arg_kwargs,
                    ),
                ]

            elif param.kind is param.POSITIONAL_ONLY:
                pa = [
                    Argument(
                        nc.cli_positional(),
                        **arg_kwargs,
                    )
                ]

            elif param.kind is param.KEYWORD_ONLY:
                if "default" not in arg_kwargs:
                    arg_kwargs["required"] = True

                pa = [
                    Argument(
                        nc.cli_keyword(),
                        dest=name,
                        **arg_kwargs,
                    )
                ]

            elif param.kind is param.VAR_POSITIONAL:
                pass
#                 pa = [
#                     Argument(
#                         nc.cli_positional(),
#                         nargs="*",
#                     )
#                 ]

            elif param.kind is param.VAR_KEYWORD:
                pass

            if pa:
                pas[name] = pa

        # @arg decorator is deprecated but there is a lot of code out there
        # that uses the @arg decorator
        dargs = self._get_decorator_args()
        for a, kw in dargs:
            pa = Argument(*a, **kw)
            if pa.name in pas:
                if len(pas[pa.name]) > 1:
                    index = 0
                    if pa.is_keyword():
                        index = 1

                    pas[pa.name][index].merge(pa)
                    pas[pa.name] = [pas[pa.name][index]]

                else:
                    pas[pa.name].merge(pa)

            else:
                pas[pa.name] = pa

        yield from pas.values()

#         pas = {}
#         sig = self.get_signature_info()
# 
#         # the values injected via @arg decorator
#         dargs = self.decorator_args()
#         for a, kw in dargs:
#             pa = Argument(*a, **kw)
#             pa.merge_signature(sig)
#             if pa.name in pas:
#                 pas[pa.name].merge(pa)
# 
#             else:
#                 pas[pa.name] = pa
# 
#         return pas.values()


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
    def positionals(self):
        return self[0]

    @property
    def kwargs(self):
        return self[1]

    @property
    def keywords(self):
        return self[1]

    def __new__(cls, *names, **kwargs):
        instance = super().__new__(cls, [list(names), kwargs])
        instance._infer_values()
        return instance

    def __set_name__(self, command_class, name):
        """This is called right after __init__

        https://docs.python.org/3/howto/descriptor.html#customized-names

        This is only called when an instance is created while a class is being
        parsed/created

        :param command_class: type, the class this Argument will belong to
        :param name: str, the argument's public name on the class
        """
        self.name = name

        if not self[0]:
            # since no names are defined, we're going to make this a keyword
            nc = NamingConvention(name)
            self[0].append(nc.cli_keyword())
            self[1]["dest"] = name

        else:
            if self.is_keyword():
                self[1]["dest"] = name

    def _infer_values(self):
        """Set the dest keyword if using the first name if dest wasn't
        passed in explicitely"""
        if self[0] and "dest" not in self[1] and self.is_keyword():
            self[1]["dest"] = NamingConvention(self[0][0]).cli_dest()

        if not self[0]:
            if dest := self[1].get("dest"):
                self[0].append(NamingConvention(dest).cli_keyword())

        if dest := self[1].get("dest"):
            action = self[1].get("action")
            self[1]["metavar"] = NamingConvention(dest).cli_metavar()
            self.name = dest

    def is_positional(self):
        return not self.is_keyword()

    def is_keyword(self):
        """returns True if argument is a keyword argument"""
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
                if self.is_keyword():
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
        sa = set(self[0])
        for a in pa[0]:
            if a not in sa:
                self[0].append(a)

        # passed in Argument kwargs take precedence
        self[1].update(pa[1])

        if "default" in self[1]:
            self[1].pop("required", None)

        action = self[1].get("action")
        if action in ["store_true", "store_false"]:
            self[1].pop("metavar", None)

    def get_keywords(self) -> set[str]:
        keywords = set()
        if self.is_keyword():
            def get_flag(n):
                return f"-{n}" if len(n) == 1 else f"--{n}"

            for keyword in self[0]:
                # ignore environment variables
                if keyword.startswith("$"):
                    continue

                keyword = NamingConvention(keyword).cli_dest()
                for n in NamingConvention(keyword).variations():
                    keywords.add(get_flag(n))

            if dest := self[1].get("dest", ""):
                for n in NamingConvention(dest).variations():
                    keywords.add(get_flag(n))

        return keywords

#     def set_names(self):
#         """Find all the possible names for the flag, this normalizes things so
#         --foo-bar is the same as --foo_bar"""
#         is_named = self.is_keyword()
#         names = set()
#         longest_name = ""
#         for n in list(self[0]):
#             # ignore environment variables
#             if n.startswith("$"):
#                 continue
# 
#             ns = n.strip("-")
#             if len(longest_name) < len(ns):
#                 longest_name = ns
# 
#             names.add(ns)
#             names.update(NamingConvention(ns).variations())
# 
#         if dest := self[1].get("dest", ""):
#             self.name = dest
#             names.update(NamingConvention(dest).variations())
# 
#         else:
#             if is_named:
#                 self[1].setdefault("dest", longest_name.replace('-', '_'))
#             self.name = longest_name
# 
#         self.names = names

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


class Pathfinder(ClasspathFinder):
    """Internal class to Router. This handles setting the subcommand hierarchy,
    this is used to create all the parsers in the Router."""
    def _get_node_default_value(self, **kwargs):
        """The default value for any node that isn't a module or class"""
        return {
            "command_class": self.kwargs["command_class"],
            "parser": None,
            "subparsers": None,
            "aliases": set(),
            "description": "",
            "version": "",
        }

    def _get_node_module_info(self, key, **kwargs):
        """All modules loaded from command prefixes go through this method.
        Handle normalizing each module key to kebabcase"""
        nc = NamingConvention(key)

        key, value = super()._get_node_module_info(nc.kebabcase(), **kwargs)

        rm = ReflectModule(value["module"])
        value["aliases"] = nc.variations()
        value["description"] = rm.get_docblock()
        value["version"] = rm.get("__version__", "")

        return key, value

    def _get_node_class_info(self, key, **kwargs):
        """All user defined Command children go through this method"""
        if "class" in kwargs:
            rc = kwargs["class"].reflect()
            key = kwargs["class"].get_name()

        else:
            # can be `Foo` or `Bar` in: Foo.Bar.Che
            rc = None
            key = NamingConvention(key).kebabcase()

        key, value = super()._get_node_class_info(key, **kwargs)

        if rc:
            #value["reflect_class"] = rc
            value["aliases"] = value["class"].get_aliases()
            value["description"] = rc.get_docblock()
            value["version"] = value["class"].version
            value["command_class"] = value["class"]


#             if aliases := value["class"].aliases:
#                 value["aliases"] = aliases
# 
#             else:
#                 nc = NamingConvention(value["class"].__name__)
#                 value["aliases"] = nc.variations()
# 
#             value["description"] = value["class"].reflect().get_docblock()
#             value["version"] = value["class"].version
#             value["command_class"] = value["class"]

        return key, value


