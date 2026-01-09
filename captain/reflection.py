# -*- coding: utf-8 -*-
import re
import inspect
import types
import argparse
from collections.abc import Iterable, Generator, Mapping

from datatypes import (
    NamingConvention,
    MethodpathFinder,
)
from datatypes.reflection import (
    ReflectParam,
    ReflectClass,
    ReflectCallable,
    ReflectModule,
    ReflectType,
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

    def get_class_arguments(self) -> Generator[list[tuple]]:
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

    def get_arguments(self) -> Generator[list[tuple]]:
        yield from self.get_class_arguments()
        yield from self.reflect_method().get_arguments()

    def get_docblock(self):
        doc = ""
        if not self.get_target().is_private():
            rm = self.reflect_method()
            doc = rm.get_docblock()
            if not doc:
                doc = super().get_docblock()

        return doc


class ReflectParam(ReflectParam):
    def _get_argument_flags(self) -> Mapping:
        """Get the common argparse argument flags that are the same between
        positional and keyword argparse arguments"""
        flags = {"aliases": []}

        rt = None
        param = self.get_target()

        if param.default is not param.empty:
            flags["default"] = param.default

        if param.annotation is param.empty:
            if "default" in flags:
                rt = self.create_reflect_type(type(flags["default"]))

        else:
            rt = self.create_reflect_type(param.annotation)

        if rt:
            flags["type"] = rt.get_origin_type()

            if not rt.is_castable():
                flags.pop("type")

            if rt.is_literal():
                flags.pop("type", None)
                flags["choices"] = set(rt.get_args())

            for metadata in rt.get_metadata():
                if isinstance(metadata, Mapping):
                    flags.update(metadata)

                else:
                    flags["aliases"].append(metadata)

        return flags

    def get_positional_argument_flags(self) -> Mapping:
        """Get argparse positional flags"""
        flags = self._get_argument_flags()
        flags.pop("aliases", None)
        return flags

    def get_keyword_argument_flags(self) -> Mapping:
        """Get argparse keyword flags"""
        flags = self._get_argument_flags()

        if "default" not in flags:
            # mutual exclusive values can't be required, if it can be passed
            # in as either a positional or keyword it can't be required
            flags["required"] = not self.is_param()

        if "type" in flags:
            rt = self.create_reflect_type(flags["type"])
            if rt.is_bool():
                # https://docs.python.org/3/library/argparse.html#action
                if not flags.pop("default", False):
                    flags["action"] = "store_true"

                else:
                    flags["action"] = "store_false"

        return flags


class ReflectMethod(ReflectCallable):
    def _get_decorator_args(self):
        """Iterate through all the @arg decorator calls

        :returns: generator, this will yield in the order the @arg were added
            from top to bottom
        """
        args = reversed(self.get_target().__dict__.get('decorator_args', []))
        return args

    def get_arguments(self) -> Generator[list[tuple]]:
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
            param = rp.get_target()
            name = rp.name
            nc = NamingConvention(name)

            if param.kind is param.POSITIONAL_OR_KEYWORD:
                pa = [
                    Argument(
                        name,
                        nargs="?",
                        **rp.get_positional_argument_flags(),
                    ),
                    Argument(
                        nc.cli_keyword(),
                        dest=name,
                        help=param_descs.get(name, ""),
                        **rp.get_keyword_argument_flags(),
                    ),
                ]

            elif param.kind is param.POSITIONAL_ONLY:
                pa = [
                    Argument(
                        #nc.cli_positional(),
                        name,
                        help=param_descs.get(name, ""),
                        **rp.get_positional_argument_flags(),
                    )
                ]

            elif param.kind is param.KEYWORD_ONLY:
                pa = [
                    Argument(
                        nc.cli_keyword(),
                        dest=name,
                        help=param_descs.get(name, ""),
                        **rp.get_keyword_argument_flags(),
                    )
                ]

            elif param.kind is param.VAR_POSITIONAL:
                pass

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
                pas[pa.name] = [pa]

        yield from pas.values()


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
    def positionals(self):
        return self[0]

    @property
    def keywords(self):
        return self[1]

    def __new__(cls, *names, **kwargs):
        instance = super().__new__(cls, [list(names), kwargs])
        instance._resolve()
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

    def _resolve(self):
        """Check and fix any strange names or flags
        """
        # Set the dest keyword if using the first name if dest wasn't passed
        # in explicitely
        if self[0] and "dest" not in self[1] and self.is_keyword():
            self[1]["dest"] = NamingConvention(self[0][0]).cli_dest()

        # if no names were passed in then assume self is a keyword and try
        # to infer a flag name
        if not self[0]:
            if dest := self[1].get("dest"):
                self[0].append(NamingConvention(dest).cli_keyword())

        # set name, use dest if we have it, use name if it's a positional
        if dest := self[1].get("dest"):
            self[1].setdefault("metavar", NamingConvention(dest).cli_metavar())
            self.name = dest

        else:
            # if this fails, `.name` will have to be set in __set_name__
            if self[0] and self.is_positional():
                nc = NamingConvention(self[0][0])
                self[1].setdefault("metavar", nc.cli_metavar())
                self.name = nc.cli_positional()

        # for our purposes, default and required are mutually exclusive
        if "default" in self[1]:
            self[1].pop("required", None)

        action = self[1].get("action")
        if action in ["store_true", "store_false"]:
            self[1].pop("metavar", None)
            self[1].pop("type", None)

        for k in ["alias", "name"]:
            if v := self[1].pop(k, ""):
                self[0].append(v)

        for k in ["aliases", "names"]:
            if vs := self[1].pop(k, []):
                self[0].extend(vs)

        if self.is_positional():
            if rt := self.reflect_type():
                if not rt.is_listish():
                    if not self.is_required():
                        self[1]["nargs"] = "?"

                else:
                    self[1]["nargs"] = "+" if self.is_required() else "*"

    def is_positional(self):
        return self[0] and not self.is_keyword()

    def is_keyword(self):
        """returns True if argument is a keyword argument"""
        for n in self[0]:
            if n.startswith("-"):
                return True
        return False

    def is_required(self):
        """Return True if this argument is required to be passed in"""
        if "required" in self[1]:
            return self[1]["required"]

        else:
            return "default" not in self[1]

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

        self._resolve()

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

    def reflect_type(self) -> ReflectType|None:
        if "type" in self[1]:
            return ReflectType(self[1]["type"])

        elif "default" in self[1]:
            return ReflectType(type(self[1]["default"]))

        else:
            action = self[1].get("action")
            if action in ["store_true", "store_false"]:
                return ReflectType(bool)


class Pathfinder(MethodpathFinder):
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
            key, value = super()._get_node_class_info(
                kwargs["class"].get_name(),
                **kwargs,
            )

            rc = kwargs["class"].reflect()
            value["aliases"] = value["class"].get_aliases()
            value["description"] = rc.get_docblock()
            value["version"] = value["class"].version
            value["command_class"] = value["class"]

        else:
            # can be `Foo` or `Bar` in: <MODULE>:Foo.Bar.Che
            nc = NamingConvention(key)

            key, value = super()._get_node_class_info(
                nc.kebabcase(),
                **kwargs,
            )

            value["aliases"] = nc.variations()

        return key, value

    def _get_node_method_info(
        self,
        key: str,
        **kwargs,
    ) -> tuple[str|None, Mapping|None]:
        """All methods of Command children go through this method but this
        method only cares about `handle_* methods, all other methods won't
        create a node in the tree"""
        if key.startswith("handle_") and key != "handle_error":
            parts = key.split("_", 1)
            nc = NamingConvention(parts[1])

            key, value = super()._get_node_method_info(
                nc.kebabcase(),
                **kwargs
            )

            value["aliases"] = nc.variations()

            rc = ReflectCallable(value["method"])
            value["description"] = rc.get_docblock()

            value["command_class"] = value["class"]
            value["version"] = value["class"].version

            return key, value

        else:
            return None, None

