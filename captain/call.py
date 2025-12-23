# -*- coding: utf-8 -*-
import sys
import inspect
import re
from collections.abc import Iterable, Mapping

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
    def module(cls):
        """The module the child class is defined in"""
        try:
            return sys.modules[cls.__module__]

        except KeyError as e:
            raise AttributeError("module") from e


    @classmethod
    def get_aliases(cls):
        """If you want your SUBCOMMAND to have aliases (ie, foo-bar and foo_bar
        will both trigger the subcommand) then you can return the aliases, this
        can be set in a child class or set aliases = [] to completely remove
        any aliases in a subclass"""
        nc = NamingConvention(cls.__name__)
        return nc.variations()

    @classmethod
    def get_name(cls):
        """Get the Command name.

        This is used in Pathfinder to decide the subcommand for this class

        :returns: str|None, the basename in kebab case, or None if this is
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
    def reflect(cls):
        """The interface does a lot of introspection to figure out how to call
        the .handle() method, this returns the reflection class of this
        specific command

        :returns: ReflectCommand
        """
        return ReflectCommand(cls)

    @classmethod
    def is_private(cls):
        """Return true if this is a valid user facing command class

        any found Command subclass that has a name that doesn't end with
        Command (eg BaseCommand) and doesn't start with an underscore (eg _Foo) 
        is a valid external command

        :returns: bool, True if valid, False if not user facing
        """
        return (
            cls.private
            or cls.__name__.startswith("_")
            or cls.__name__.endswith("Command")
        )

    def __init__(self, parsed=None, application=None, parser=None):
        self.parsed = parsed
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

    async def get_parsed_params(self, parsed) -> tuple[Iterable, Mapping]:
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

    async def run(self, *args, **kwargs):
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
            #args, kwargs = await self.get_handle_params(*args, **kwargs)
            ret_code = self.handle(*args, **kwargs)
            #ret_code = await self.handle_call(*args, **kwargs)

        except Exception as e:
            ret_code = self.handle_error(e)
            #ret_code = await self.handle_error(e)

        finally:
            while inspect.iscoroutine(ret_code):
                ret_code = await ret_code

        return ret_code

    async def handle(self, *args, **kwargs):
        self.parser.print_help()

    async def handle_error(self, e):
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

    async def call(self, subcommands, *args, **kwargs):
        """Hook to make it easier to call other commands from a handle method

        :example:
            # call the "foo bar" command from self
            self.call("foo bar")

            # call the Default top level command, you have to pass in en empty
            # string
            self.call("")

            # call "foo" subcommand with a value
            self.call("foo", bar="<VALUE>")

        :param subcommands: str|Sequence[str], the subcommand path to call.
            If you want to call the root parser pass in empty string
        :param *args: anything in this will be passed to the other command
            as positional arguments
        :param **kwargs: anything in this will be passed to the other command
            as keyword arguments
        :returns: int, the return code of the other command
        :raises: Exception, any exceptions the other command raises will be
            passed through
        """
        call_args = []

        if subcommands:
            if isinstance(subcommands, str):
                call_args.extend(re.split(r"\s+", subcommands))

            else:
                call_args.extend(subcommands)

        call_args.extend(args)

        # This is kind of cheating a bit, we turn these into keyword
        # arguments so we can just run a new command with a new set of
        # args
        for k, v in kwargs.items():
            if not k.startswith("-"):
                k = f"--{k}"

            call_args.append(k)

            # booleans are a special case, for True or False only the flag
            # (`k`) gets set, so if you want an `action="store_true"` flag to
            # be set you would pass in `<NAME>=True` and for
            # `action="store_false"` you'd pass in `<NAME>=False`
            if not isinstance(v, bool):
                call_args.append(v)

        return await self.application.run(call_args)

#         if not self.parsed:
#             raise ValueError(
#                 "Cannot run subcommands without .parsed property"
#             )
# 
#         if isinstance(subcommands, str):
#             subcommands = re.split(r"\s+", subcommands)
# 
#         if subcommands:
#             # find the starting parser moving backwards from the current
#             # parser until we find the first subcommand
#             parser = self.parsed._parser_node.parent.value["parser"]
#             while parser_node := parser._defaults["_parser_node"]:
#                 action = parser_node.value["subparsers"]
#                 subcommand = action.get_arg_string(subcommands[0])
#                 if subcommand in action._name_parser_map:
#                     #parser = action._name_parser_map[subcommand]
#                     break
# 
#                 else:
#                     pn = parser._defaults["_parser_node"]
#                     parser = pn.parent.value["parser"]
# 
#         else:
#             # since we don't have any subcommands we want the root-most parser
#             parser = self.parsed._parser_node.root.value["parser"]
# 
#         for subcommand in subcommands:
#             parser_node = parser._defaults["_parser_node"]
# 
#             if parser_node.value["subparsers"]:
#                 action = parser_node.value["subparsers"]
#                 subcommand = action.get_arg_string(subcommand)
#                 parser = action._name_parser_map[subcommand]
# 
#             else:
#                 if subcommand == subcommands[-1]:
#                     parser = parser_node["parser"]
# 
#                 else:
#                     raise ValueError(
#                         f"Could not find parser for {subcommand} subcommand"
#                     )
# 
#         command_class = parser._defaults["_command_class"]
# 
#         parsed = self.parsed
#         rc = command_class.reflect()
#         sig = rc.reflect_method().get_signature_info()
#         parsed._handle_signature = sig
# 
#         command = command_class(parsed)
# 
#         return await command.run(*args, **kwargs)

