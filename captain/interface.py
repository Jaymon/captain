# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys

from .compat import *
from . import exception
from .parse import ArgumentParser, QuietAction
from .decorators import classproperty
from . import decorators
from .reflection import ReflectCommand
from .io import Output, Input
from . import logging


logger = logging.getLogger(__name__)


class Captain(object):
    """Singleton to handle running the script

    the singleton instance is available at Captain.get_instance(), it's this class's
    handle() method that is called to have captain take over control, if you check
    captain/__init__.py you will see it basically assigns handle to an instance of
    this class
    """

    instance = None
    """the singleton instance created/returned with get_instance()"""

    parser_class = ArgumentParser
    """The ArgumentParser class to use to create the parser"""

    @property
    def version(self):
        """Check all the modules of all the commands, first __version__ found wins"""
        v = ""
        for command_class in self.commands.values():
            m = command_class.module
            if m:
                v = getattr(m, "__version__", "")
                if v:
                    v = String(v)
                    break
        return v

    @classmethod
    def get_instance(cls):
        if not cls.instance:
            cls.instance = cls()
        return cls.instance

    def create_parser(self):
        subcommand_classes = dict(self.commands)
        command_class = subcommand_classes.pop("default", subcommand_classes.pop("main", None))
        return self.parser_class.create_instance(
            command_class,
            subcommand_classes,
            version=self.version,
            quiet=True,
            default_desc="Captain CLI",
        )

    def __init__(self):
        self.commands = {}

    def run(self, argv):
        """Actually run captain with the given argv"""
        parser = self.create_parser()
        parsed, args, kwargs = parser.parse_handle_args(argv)
        c = parsed._command_instance
        c.parsed = parsed
        try:
            ret_code = c.handle(*args, **kwargs)

        except Exception as e:
            ret_code = c.handle_error(e, ret_code)

        return ret_code

    def handle(self):
        """wraps run()"""
        argv = sys.argv[1:]
        ret_code = self.run(argv)
        sys.exit(ret_code)

    def __call__(self):
        return self.handle()


class CommandFinder(type):
    """The Command metaclass

    This is tough to explain, basically this allows our Captain singleton to
    see what Command classes are defined while the script is running, it allows us
    to get around all the strange reflection and code parsing stuff we did in the
    previous captain versions, it gets invoked when a new Command class is getting
    defined and it records those in our Captain singleton

    https://stackoverflow.com/a/18126678/5006
    """
    def __init__(cls, name, bases, properties):
        if not cls.__module__.startswith(__name__):
            # filter all *Command classes, this allows sensible inheritance
            # any found *Command subclass that has a name that doesn't end with
            # Command and doesn't start with underscore is a valid command
            class_name = cls.__name__
            if not class_name.endswith("Command") and not class_name.startswith("_"):
                cls.interface.commands[class_name.lower()] = cls

        return super(CommandFinder, cls).__init__(name, bases, properties)


if is_py3:
    # python 2 compiler throws an error on metaclass=... syntax
    exec("class BaseCommand(object, metaclass=CommandFinder): pass")

else:
    class BaseCommand(object):
        __metaclass__ = CommandFinder


# This is the base class of custom commands, any captain command needs to 
# extend this class and define handle(), basically, every captain script will
# go through a child of this class's handle() method, this class can't have a
# docblock because that screws up reflections docblock finder
class Command(BaseCommand):
    interface_class = Captain

    output_class = Output

    input_class = Input

    # these are just handy for handle() methods to quickly raise these without
    # having to import anything separately
    Stop = exception.Stop
    Error = exception.Error
    arg = decorators.arg
    args = decorators.args

    @classproperty
    def interface(cls):
        """Return our Captain singleton"""
        return cls.interface_class.get_instance()

    @classproperty
    def module(cls):
        return sys.modules[cls.__module__]

    @classmethod
    def reflect(cls):
        return ReflectCommand(cls)

    def __init__(self):
        self.input = self.input_class()
        self.output = self.output_class()

    def handle(self, *args, **kwargs):
        logger.warning(
            "Command.handle() received {} args and {} kwargs".format(
                len(args),
                len(kwargs),
            )
        )
        raise NotImplementedError("Override handle() in your child class")

    def handle_error(self, e, ret_code):
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
            self.output.exception(e)

        return ret_code

