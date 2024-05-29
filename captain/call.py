# -*- coding: utf-8 -*-
import sys

from datatypes import NamingConvention

from .compat import *
from .decorators import classproperty
from .reflection import ReflectCommand
from .io import Output, Input
from . import logging


logger = logging.getLogger(__name__)


# class CommandFinder(type):
#     """The Command metaclass
# 
#     This is tough to explain, basically this allows our Captain singleton to
#     see what Command classes are defined while the script is running, it allows us
#     to get around all the strange reflection and code parsing stuff we did in the
#     previous captain versions, it gets invoked when a new Command class is getting
#     defined and it saves those in our Captain singleton
# 
#     https://stackoverflow.com/a/18126678/5006
#     """
#     def __init__(cls, name, bases, properties):
#         if not cls.__module__.startswith(__name__):
#             # filter all *Command classes, this allows sensible inheritance
#             if cls.is_external():
#                 cls.interface.commands[cls.name] = cls
# 
#         return super().__init__(name, bases, properties)


# This is the base class of custom commands, any captain command needs to 
# extend this class and define handle(), basically, every captain script will
# go through a child of this class's handle() method, this class can't have a
# docblock because that screws up reflection's docblock finder
class Command(object):
    output_class = Output

    input_class = Input

    command_classes = {}
    """Holds all the command classes that have been loaded into memory, the
    classpath is the key and the class object is the value, see
    __init_subclass__"""

    @classproperty
    def name(cls):
        """This is the name that will be used to invoke the SUBCOMMAND, it can be
        overridden in child classes but has no effect if the child class is named
        Default"""
        n = NamingConvention(cls.__name__)
        return n.dash().lower()

    @classproperty
    def aliases(cls):
        """If you want your SUBCOMMAND to have aliases (ie, foo-bar and foo_bar will
        both trigger the subcommand) then you can return the aliases, this can be
        set in a child class or set aliases = [] to completely remove any aliases
        in a subclass"""
        aliases = set()
        for name in [cls.__name__, cls.name]:
            aliases.update(NamingConvention(name).variations())
        aliases.discard(cls.name)
        return aliases

    @classproperty
    def module(cls):
        """The module the child class is defined in"""
        return sys.modules[cls.__module__]

    @classmethod
    def reflect(cls):
        """The interface does a lot of introspection to figure out how to call
        the .handle() method, this returns the reflection class of this specific
        command

        :returns: ReflectCommand
        """
        return ReflectCommand(cls)

    @classmethod
    def is_external(cls):
        """Return true if this is a valid user facing command class

        any found Command subclass that has a name that doesn't end with
        Command (eg BaseCommand) and doesn't start with an underscore (eg _Foo) 
        is a valid external command

        :returns: bool, True if valid, False if not user facing
        """
        class_name = cls.__name__
        return not class_name.endswith("Command") and not class_name.startswith("_")

    def __init__(self):
        self.input = self.input_class()
        self.output = self.output_class()

    def __init_subclass__(cls):
        """When a child class is loaded into memory it will be saved into
        .command_classes, this way every command class knows about all
        the other classes, this is the method that makes a lot of the magic
        of captain possible

        https://peps.python.org/pep-0487/
        """
        super().__init_subclass__()
        if cls.is_external():
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
                cb = super().__getattr__(k)
        return cb

    def run(self, *args, **kwargs):
        """Wrapper around the internal handle methods, this should be considered the
        correct external method to call

        this could be easily overridden so you can easily do something before or after
        the handle calls

        The handle methods should be considered "internal" to the Captain class
        that are interacted with through this method

        :param *args: all positional values passed in through the command line passed through
            any configured parsers
        :param **kwargs: all the flag values passed in through the command line passed through
            any configured parsers
        :returns: int, the return code
        """
        try:
            ret_code = self.handle(*args, **kwargs)

        except Exception as e:
            ret_code = self.handle_error(e)

        return ret_code

    def handle(self, *args, **kwargs):
        logger.warning(
            "Command.handle() received {} args and {} kwargs".format(
                len(args),
                len(kwargs),
            )
        )
        raise NotImplementedError("Override handle() in your child class")

    def handle_error(self, e):
        """This is called when an uncaught exception on the Command is raised, it
        can be defined in the child to allow custom handling of uncaught exceptions"""
        if isinstance(e, self.Stop):
            ret_code = e.code
            msg = String(e)
            if msg:
                if ret_code != 0:
                    self.output.err(msg)
                else:
                    self.output.out(msg)

        else:
            raise

        return ret_code

