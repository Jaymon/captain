# -*- coding: utf-8 -*-
import sys
import inspect
import re

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
    def name(cls):
        """This is the name that will be used to invoke the SUBCOMMAND, it can
        be overridden in child classes but has no effect if the child class is
        named Default"""
        n = NamingConvention(cls.__name__)
        return n.dash().lower()

    @classproperty
    def aliases(cls):
        """If you want your SUBCOMMAND to have aliases (ie, foo-bar and foo_bar
        will both trigger the subcommand) then you can return the aliases, this
        can be set in a child class or set aliases = [] to completely remove
        any aliases in a subclass"""
        return set()

    @classproperty
    def module(cls):
        """The module the child class is defined in"""
        try:
            return sys.modules[cls.__module__]

        except KeyError as e:
            raise AttributeError("module") from e

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

    @classmethod
    def arguments(cls):
        """Returns all the defined class arguments that will become class
        properties when the command is ran

        :returns: dict[str, Argument], where the key is the name of the 
            property and the value is the Argument information that can be
            used when adding the argument to a parser using
            parser.add_argument
        """
        arguments = {}
        for k, v in inspect.getmembers(cls, lambda v: isinstance(v, Argument)):
            arguments[k] = v

        return arguments

    def __init__(self, parsed=None):
        self.parsed = parsed
        self.input = self.input_class()
        self.output = self.output_class()

        # any class properties should be set to None on this instance since
        # they don't exist and we don't want any instance methods messing with
        # the actual Argument instance
        for k in self.arguments().keys():
            setattr(self, k, None)

    def __init_subclass__(cls):
        """When a child class is loaded into memory it will be saved into
        .command_classes, this way every command class knows about all
        the other classes, this is the method that makes a lot of the magic
        of captain possible

        https://peps.python.org/pep-0487/
        """
        super().__init_subclass__()
        if not cls.is_private():
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

    async def get_handle_params(self, *args, **kwargs):
        """Called right before the command's handle method is called.

        passed in args and kwargs will be merged with .parsed

        :param *args: will override any matching .parsed args
        :param **kwargs: will override any matching .parsed values
        :returns: tuple[tuple, dict], whatever is returned from this method is
            passed into the .handle method as *args, **kwargs
        """
        cargs = []
        ckwargs = {}
        c_argnames = set(self.arguments().keys())

        if parsed := self.parsed:
            m_argnames = set(parsed._handle_signature["names"])

            for k, v in vars(parsed).items():
                # we filter out private (starts with _) and placeholder
                # (surrounded by <>) keys
                if not k.startswith("_") and not k.startswith("<"):
                    if k in c_argnames:
                        setattr(self, k, v)

                    if k in m_argnames:
                        ckwargs[k] = v

                    elif parsed._handle_signature["**_name"]:
                        ckwargs[k] = v

                    elif k == parsed._handle_signature["*_name"]:
                        ckwargs[k] = v

            ckwargs.update(kwargs)

            if args_name := parsed._handle_signature["*_name"]:
                cargs.extend(ckwargs.pop(args_name, []))

            cargs.extend(args)

        return cargs, ckwargs

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
            args, kwargs = await self.get_handle_params(*args, **kwargs)
            ret_code = await self.handle_call(*args, **kwargs)

        except Exception as e:
            ret_code = await self.handle_error(e)

        return ret_code

    async def handle_call(self, *args, **kwargs):
        """Run the main .handle method

        this could be easily overridden so you can easily do something before
        or after the handle calls. This exists so there is an easy hook for
        context managers or the like after the parameters have been shaken out
        (which is why .run didn't work for things like context managers).

        See: https://github.com/Jaymon/captain/issues/90

        :param *args: the positional arguments that will be passed to .handle
            because they've already been normalized with .get_handle_params
        :param *kwargs: the keyword arguments that will be passed to .handle
            because they've already been normalized with .get_handle_params
        :returns: int, the return code
        """
        # child classes without async handle methods is common so we
        # don't await and instead await if we know it's a coroutine
        ret_code = self.handle(*args, **kwargs)
        while inspect.iscoroutine(ret_code):
            ret_code = await ret_code

        return ret_code

    async def handle(self, *args, **kwargs):
        self.parsed._parser.print_help()

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
        if not self.parsed:
            raise ValueError(
                "Cannot run subcommands without .parsed property"
            )

        if isinstance(subcommands, str):
            subcommands = re.split(r"\s+", subcommands)

        if subcommands:
            # find the starting parser moving backwards from the current
            # parser until we find the first subcommand
            parser = self.parsed._parser_node.parent.value["parser"]
            while parser_node := parser._defaults["_parser_node"]:
                action = parser_node.value["subparsers"]
                subcommand = action.get_arg_string(subcommands[0])
                if subcommand in action._name_parser_map:
                    #parser = action._name_parser_map[subcommand]
                    break

                else:
                    pn = parser._defaults["_parser_node"]
                    parser = pn.parent.value["parser"]

        else:
            # since we don't have any subcommands we want the root-most parser
            parser = self.parsed._parser_node.root.value["parser"]

        for subcommand in subcommands:
            parser_node = parser._defaults["_parser_node"]

            if parser_node.value["subparsers"]:
                action = parser_node.value["subparsers"]
                subcommand = action.get_arg_string(subcommand)
                parser = action._name_parser_map[subcommand]

            else:
                if subcommand == subcommands[-1]:
                    parser = parser_node["parser"]

                else:
                    raise ValueError(
                        f"Could not find parser for {subcommand} subcommand"
                    )

        command_class = parser._defaults["_command_class"]

        parsed = self.parsed
        rc = command_class.reflect()
        sig = rc.reflect_method().get_signature_info()
        parsed._handle_signature = sig

        command = command_class(parsed)

        return await command.run(*args, **kwargs)

