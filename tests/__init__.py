# -*- coding: utf-8 -*-
import inspect

import testdata
from testdata.test import TestCase

from captain.compat import *
from captain import Application, Command
from captain.reflection import ReflectMethod, ReflectCommand


class FileScript(object):
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
                header += "\n".join([
                    "# -*- coding: utf-8 -*-",
                    "",
                ])

            if "from captain" not in body:
                header += "\n".join([
                    #"#!/usr/bin/env python",
                    #"import sys",
                    #"sys.path.insert(0, '{}')".format(self.cwd),
                    "from captain import (",
                    "    Command,",
                    "    Argument,",
                    "    arg,",
                    "    args,",
                    "    exception,",
                    ")",
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

    def create_script(self, body, **kwargs):
        if kwargs.get("module", False):
            m = testdata.create_module(
                body,
                module_name="{}.__main__".format(testdata.get_module_name()),
            )

        else:
            m = testdata.create_module(
                body,
            )

        return m

    def run(self, arg_str="", **kwargs):
        return testdata.run_command(
            "{} {}".format(testdata.get_interpreter(), self.path.path),
            arg_str,
            cwd=self.cwd,
            **kwargs
        ).strip()

