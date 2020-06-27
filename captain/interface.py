# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys

from .compat import *
from . import exception
from .parse import ArgumentParser, QuietAction
from .decorators import classproperty
from .reflection import ReflectCommand
from .io import Output, Input
from . import logging


logger = logging.getLogger(__name__)


#class_cache = {}


# def handle():
#     #pout.v(sys.modules["__main__"])
#     #pout.v(handle.__module__)
# 
# #     callframe = sys._getframe(1)
# #     pout.i(callframe)
# #     pout.v(callframe.f_locals)
# 
#     pout.v(class_cache)
#     pass


class Captain(object):

    instance = None

    parser_class = ArgumentParser

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
        parser = self.create_parser()
        parsed, args, kwargs = parser.parse_handle_args(argv)
        c = parsed._command_instance
        c.parsed = parsed
        try:
            ret_code = c.handle(*args, **kwargs)

        except exception.Stop as e:
            ret_code = e.code
            msg = String(e)
            if msg:
                if ret_code != 0:
                    c.output.err(msg)
                else:
                    c.output.out(msg)

        return ret_code

    def handle(self):
        argv = sys.argv[1:]
        ret_code = self.run(argv)
        sys.exit(ret_code)

    def __call__(self):
        return self.handle()









class CommandFinder(type):
    """
    https://stackoverflow.com/a/18126678/5006
    """

    def __init__(cls, name, bases, properties):
        #if len(cls.mro()) > 2:
        #if issubclass(cls, Command):
        #pout.v(cls, bases)
        if not cls.__module__.startswith(__name__):
            # filter all *Command classes, this allows sensible inheritance
            # any found *Command subclass that has a name that doesn't end with
            # Command and doesn't start with underscore is a valid command
            class_name = cls.__name__
            if not class_name.endswith("Command") and not class_name.startswith("_"):
                #class_cache[class_name] = cls
                cls.interface.commands[class_name.lower()] = cls
                #pout.v(bases)

        return super(CommandFinder, cls).__init__(name, bases, properties)

#     def __new__(cls, name, bases, properties):
#         #if len(cls.mro()) > 2:
#         pout.v(cls, bases)
#         return super(Watcher, cls).__init__(name, bases, properties)


if is_py3:
    exec("class BaseCommand(object, metaclass=CommandFinder): pass")
    #class BaseCommand(metaclass=Watcher):
    #    pass

else:
    class BaseCommand(object):
        __metaclass__ = CommandFinder
        pass


class Command(BaseCommand):

    interface_class = Captain

    output_class = Output

    input_class = Input

    Stop = exception.Stop
    Error = exception.Error
    #ArgError = exception.ArgError

    @classproperty
    def interface(cls):
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


