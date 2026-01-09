# -*- coding: utf-8 -*-
import sys
import inspect
import re
from collections.abc import Iterable, Mapping, Callable
from types import ModuleType

from datatypes import NamingConvention

from .compat import *
from .decorators import classproperty
from .reflection import ReflectCommand, Argument
from .io import Output, Input
from . import exception


class Command(object):
    """This is the base class of all commands and subcommands, any custom
    command should extend this class and define the .handle() method,
    basically, every script will go through a child of this class's handle()
    method
    """
    output_class = Output

    input_class = Input

    command_classes = {}
    """Holds all the command classes that have been loaded into memory, the
    classpath is the key and the class object is the value, see
    __init_subclass__"""

    private = False
    """set this to True if the Command is not designed to be called"""

    version = ""
    """Set this as the version for this command"""

    @classproperty
    def module(cls) -> ModuleType:
        """The module the child class is defined in"""
        try:
            return sys.modules[cls.__module__]

        except KeyError as e:
            raise AttributeError("module") from e

    @classmethod
    def get_aliases(cls) -> set[str]:
        """If you want your SUBCOMMAND to have aliases (ie, foo-bar and foo_bar
        will both trigger the subcommand) then you can return the aliases, this
        can be set in a child class or set aliases = [] to completely remove
        any aliases in a subclass"""
        nc = NamingConvention(cls.__name__)
        return nc.variations()

    @classmethod
    def get_name(cls) -> str|None:
        """Get the Command name.

        This is used in Pathfinder to decide the subcommand for this class

        :returns: the basename in kebab case, or None if this is
            a default controller
        """
        name = cls.__name__
        ignore_names = set(["Default"])
        if name in ignore_names:
            name = None

        else:
            name = NamingConvention(name).kebabcase()

        return name

    @classmethod
    def reflect(cls) -> ReflectCommand:
        """The interface does a lot of introspection to figure out how to call
        the .handle() method, this returns the reflection class of this
        specific command"""
        return ReflectCommand(cls)

    @classmethod
    def is_private(cls) -> bool:
        """Return true if this is a valid user facing command class

        any found Command subclass that has a name that doesn't end with
        Command (eg BaseCommand) and doesn't start with an underscore (eg _Foo) 
        is a valid external command

        :returns: True if valid, False if not user facing
        """
        return (
            cls.private
            or cls.__name__.startswith("_")
            or cls.__name__.endswith("Command")
        )

    def __init__(self, application=None, parser=None):
        """
        :param application: the instance that was used to create self
        :type application: Application
        :param parser: the parser that was used to parse the flags on the
            command line that led to self being created
        :type parser: argparse.ArgumentParser
        """
        self.input = self.input_class()
        self.output = self.output_class()

        self.application = application
        self.parser = parser

    def __init_subclass__(cls):
        """When a child class is loaded into memory it will be saved into
        .command_classes, this way every command class knows about all
        the other classes, this is the method that makes a lot of the magic
        of captain possible

        https://peps.python.org/pep-0487/
        """
        cls.command_classes[f"{cls.__module__}:{cls.__qualname__}"] = cls

    def __getattr__(self, k):
        """Makes the .input and .output interfaces a little more fluid, output
        methods take precedence

        https://github.com/Jaymon/captain/issues/67
        """
        cb = getattr(self.output, k, None)
        if not cb:
            cb = getattr(self.input, k, None)
            if not cb:
                raise AttributeError(k)

        return cb

    def _get_handler_method(self) -> Callable[..., int]:
        """Internal method. This returns the method that will be called in
        `.run`"""
        method = self.handle

        if self.parser:
            node_value = self.parser._defaults["_pathfinder_node"].value
            if method_name := node_value.get("method_name", None):
                method = getattr(self, method_name)

        return method

    async def get_parsed_params(self, parsed) -> tuple[Iterable, Mapping]:
        """Translates parsed CLI positionals and keywords into arguments
        and keywords to pass to the handler method"""
        args = []
        kwargs = {}

        rm = self.reflect().reflect_method()
        parsed_kwargs = {}

        for k, v in parsed._get_kwargs():
            # we filter out private (starts with _) and placeholder
            # (surrounded by <>) keys
            if not k.startswith("_") and not k.startswith("<"):
                parsed_kwargs[k] = v

        for ra in rm.reflect_arguments(**parsed_kwargs):
            if ra.is_positional():
                args.extend(ra.get_positional_values())

            elif ra.is_keyword():
                kwargs.update(ra.get_keyword_values())

        return args, kwargs

    async def get_method_params(self, *args, **kwargs) -> tuple[Iterable, Mapping]:
        # set instance properties that have been passed in
        rc = self.reflect()
        for pas in rc.get_class_arguments():
            for pa in pas:
                # any class properties should be set to None on this instance
                # since they don't exist and we don't want any instance methods
                # messing with the actual Argument instance
                setattr(self, pa.name, kwargs.pop(pa.name, None))

        return args, kwargs

    async def handle(self, *args, **kwargs) -> int|None:
        self.parser.print_help()

    async def handle_error(self, e) -> int|None:
        """This is called when an uncaught exception on the Command is raised,
        it can be defined in the child to allow custom handling of uncaught
        exceptions"""
        if isinstance(e, exception.Stop):
            ret_code = e.code
            msg = String(e)
            if msg:
                if ret_code != 0:
                    self.output.err(msg)

                else:
                    self.output.out(msg)

        else:
            raise e

        return ret_code

    async def run(self, *args, **kwargs) -> int:
        """Wrapper around the internal handle methods, this should be
        considered the correct external method to call

        The handle methods should be considered "internal" to the Captain class
        that are interacted with through this method

        :param *args: all positional values passed in through the command line
            passed through any configured parsers, merged with .parsed
        :param **kwargs: all the flag values passed in through the command line
            passed through any configured parsers, merged with .parsed
        :returns: int, the return code
        """
        try:
            args, kwargs = await self.get_method_params(*args, **kwargs)
            method = self._get_handler_method()
            ret_code = method(*args, **kwargs)

        except Exception as e:
            ret_code = self.handle_error(e)

        finally:
            while inspect.iscoroutine(ret_code):
                ret_code = await ret_code

        return ret_code or 0

    async def call(self, *args, **kwargs) -> int:
        """Hook to make it easier to call other commands from a handle method

        :param *args: anything in this will be passed to the other command
            as positional arguments
        :param **kwargs: anything in this will be passed to the other command
            as keyword arguments
        :returns: int, the return code of the other command
        :raises: Exception, any exceptions the other command raises will be
            passed through
        """
        return await self.application.call(*args, **kwargs)

