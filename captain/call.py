# -*- coding: utf-8 -*-
import sys
import inspect

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
#         aliases = set()
#         if not self.is_private():
#             for name in [cls.__name__, cls.name]:
#                 for n in NamingConvention(name).variations():
#                     aliases.add(n)
#                     aliases.add(n.lower())
# 
#         return aliases

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

                    else:
                        ckwargs[k] = v

            ckwargs.update(kwargs)

            if args_name := parsed._handle_signature["*_name"]:
                cargs.extend(ckwargs.pop(args_name, []))

            cargs.extend(args)

            args = cargs
            kwargs = ckwargs

        return args, kwargs

    async def run(self, *args, **kwargs):
        """Wrapper around the internal handle methods, this should be
        considered the correct external method to call

        this could be easily overridden so you can easily do something before
        or after the handle calls

        The handle methods should be considered "internal" to the Captain class
        that are interacted with through this method

        passed in args and kwargs will be merged with .parsed

        :param *args: all positional values passed in through the command line
            passed through any configured parsers, merged with .parsed
        :param **kwargs: all the flag values passed in through the command line
            passed through any configured parsers, merged with .parsed
        :returns: int, the return code
        """
        try:
            args, kwargs = await self.get_handle_params(*args, **kwargs)
            ret_code = self.handle(*args, **kwargs)

        except Exception as e:
            ret_code = self.handle_error(e)

        finally:
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

