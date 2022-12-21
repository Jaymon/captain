# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import inspect

import testdata
from testdata.test import TestCase

from captain.compat import *
from captain import Captain, Command
from captain.reflection import ReflectMethod, ReflectCommand


class FileScript(object):
    @property
    def captain(self):
        ret = None
        m = self.module()
        for name, o in inspect.getmembers(m, lambda o: inspect.isclass(o) or inspect.ismodule(o)):
            if isinstance(o, Captain):
                ret = o.get_instance()
                break

            elif issubclass(o, Command):
                ret = o.interface
                break

            elif inspect.ismodule(o):
                cap = getattr(o, "Captain", None)
                if cap:
                    ret = cap.get_instance()
                    break

        if not ret:
            raise AttributeError("captain")

        return ret

    @property
    def parser(self):
        return self.captain.create_parser()

    def __init__(self, body="", **kwargs):
        # we want to reset the global captain instance each time this class is
        # instantiated
        Captain.instance = None

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
                    "from captain import Command, handle, arg, args",
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
                "    handle()",
            ])

        return body

    def module(self):
        return self.path.module()

    def command_class(self, command_name="default"):
        cap = self.captain
        return cap.commands[command_name.lower()]

    def command(self, command_name="default"):
        return self.command_class(command_name=command_name)()

    def reflect(self, command_name="default"):
        return ReflectCommand(self.command_class(command_name))

    def reflect_method(self, command_name="default"):
        return self.reflect(command_name).method()

    def create_script(self, body, **kwargs):
        return testdata.create_module(
            contents=body,
            foo=1,
            #tmpdir=cwd,
        )

    def run(self, arg_str="", **kwargs):
        s = testdata.Command(
            "{} {}".format(testdata.get_interpreter(), self.path.path),
            cwd=self.cwd,
            **kwargs
        )
        return s.run(arg_str, **kwargs)


class ModuleScript(FileScript):
    def create_script(self, body):
        m = testdata.create_module(
            module_name="{}.__main__".format(testdata.get_module_name()),
            contents=body,
            #tmpdir=cwd,
        )
        return m

