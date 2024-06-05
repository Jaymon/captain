# -*- coding: utf-8 -*-
import inspect

import testdata
from testdata.test import TestCase

from captain.compat import *
from captain import Application, Command
from captain.reflection import ReflectMethod, ReflectCommand


class FileScript(object):
#     @property
#     def captain(self):
#         ret = None
#         m = self.module()
#         members = inspect.getmembers(
#             m,
#             lambda o: inspect.isclass(o) or inspect.ismodule(o)
#         )
#         for name, o in members:
#             if isinstance(o, Application):
#                 ret = Application()
#                 break
# 
#             elif issubclass(o, Command):
#                 ret = o.interface
#                 break
# 
#             elif inspect.ismodule(o):
#                 if ret := getattr(o, "application", None):
#                     break
# 
#         if not ret:
#             raise AttributeError("captain")
# 
#         return ret

    @property
    def parser(self):
        return Application(command_prefixes=[self.path]).router.parser

    def __init__(self, body="", **kwargs):

        # we reset the command classes everytime we create a new script
        Command.command_classes = {}

        self.body = self.get_body(body, **kwargs)
        self.path = self.create_script(self.body, **kwargs)
        self.cwd = self.path.basedir


    def get_body(self, body, **kwargs):
        if not body:
            body = ""

        if not isinstance(body, basestring):
            body = "\n".join(body)

        if "header" in kwargs:
            header = kwargs["header"]
            if not isinstance(header, basestring):
                header = "\n".join(header)
        else:
            header = ""
            if "# -*-" not in body:
            #if "__future__" not in body and "# -*-" not in body:
                header += "\n".join([
                    "# -*- coding: utf-8 -*-",
                    "",
                ])

            if "from captain" not in body:
                header += "\n".join([
                    #"#!/usr/bin/env python",
                    #"import sys",
                    #"sys.path.insert(0, '{}')".format(self.cwd),
                    "from captain import Command, arg, args",
                    "",
                ])

            if "import captain" not in body:
                header += "\n".join([
                    "import captain",
                    "",
                ])

            header += "\n".join([
                "",
            ])

            if "__version__" not in body:
                header += "\n__version__ = '0.0.1'\n\n"

        if "class" not in body:
            subcommands = kwargs.pop("subcommands", False)
            if subcommands:
                body += "\n".join([
                    "",
                    "class Foo(Command):",
                    "    '''Foo subcommand description'''",
                    "    def handle(self, *args, **kwargs):",
                    "        print('success foo')",
                    "        print('args: ', args)",
                    "        print('kwargs: ', kwargs)",
                ])

            body += "\n".join([
                "",
                "class Default(Command):",
                "    '''default subcommand description'''",
                "    def handle(self, *args, **kwargs):",
                "        print('success default')",
                "        print('args: ', args)",
                "        print('kwargs: ', kwargs)",
            ])

        if header:
            body = header + body

        if "__name__ == " not in body:
            body += "\n".join([
                "",
                "",
                "if __name__ == '__main__':",
                "    captain.Application()()",
            ])

        return body

    def command_class(self, command_name="default"):
        command_class = None

        self.path.get_module()

        for command_class in Command.command_classes.values():
            if command_name.lower() == command_class.__name__.lower():
                break

            elif command_name.lower() == command_class.name:
                break

            else:
                if command_name in command_class.aliases:
                    break

        return command_class

#     def command(self, command_name="default"):
#         return self.command_class(command_name=command_name)()

#     def reflect(self, command_name="default"):
#         return ReflectCommand(self.command_class(command_name))
# 
#     def reflect_method(self, command_name="default"):
#         return self.reflect(command_name).method()

    def create_script(self, body, **kwargs):
        return testdata.create_module(
            body,
        )

    def run(self, arg_str="", **kwargs):
        return testdata.run_command(
            "{} {}".format(testdata.get_interpreter(), self.path.path),
            arg_str,
            cwd=self.cwd,
            **kwargs
        ).strip()


class ModuleScript(FileScript):
    def create_script(self, body):
        m = testdata.create_module(
            body,
            module_name="{}.__main__".format(testdata.get_module_name()),
            #tmpdir=cwd,
        )
        return m

