# -*- coding: utf-8 -*-
import subprocess

from captain.call import Command
from captain.reflection import Argument

from . import TestCase, FileScript


class CommandTest(TestCase):
    def test_arguments(self):
        c = FileScript([
            "class Default(Command):",
            "    def handle(self, *args, **kwargs):",
            "        print('args: ', args)",
            "        print('kwargs: ', kwargs)",
        ])

        r = c.run("0 1 2 3")
        self.assertTrue("('0', '1', '2', '3')" in r)
        self.assertTrue("{}" in r)


        r = c.run("0 1 2 --foo=3 --bar=4")
        self.assertTrue("('0', '1', '2')" in r)
        self.assertTrue("foo" in r)
        self.assertTrue("'3'" in r)
        self.assertTrue("bar" in r)
        self.assertTrue("'4'" in r)

    def test_get_name(self):
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, **kwargs): pass",
        ])
        c_class = s.command_class("foo")
        self.assertEqual("foo", c_class.get_name())

        s = FileScript("""
            class Foo(Command):
                @classmethod
                def get_name(cls): return "bar"
                def handle(self, **kwargs): pass
        """)
        c_class = s.command_class("bar")
        self.assertEqual("bar", c_class.get_name())

    def test_get_aliases(self):
        s = FileScript("""
            class FooOne(Command):
                @classmethod
                def get_aliases(cls): return ["bar"]
                def handle(self, **kwargs): pass
        """)

        c_class = s.command_class("foo-one")
        self.assertEqual(["bar"], c_class.get_aliases())

    def test_unnamed_arg(self):
        """https://github.com/Jaymon/captain/issues/64"""
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, bar):",
            "        print(f'bar: {bar}')",
        ])

        with self.assertRaises(subprocess.CalledProcessError):
            r = s.run("foo")

        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, bar):",
            "        print(f'bar: {bar}')",
        ])

        r = s.run("foo 'bar value'")
        self.assertTrue("bar: bar value" in r)

        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, bar):",
            "        print(f'bar: {bar}')",
        ])

        r = s.run("foo --bar 'bar value'")
        self.assertTrue("bar: bar value" in r)

    def test_io_fluid_interface(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self, bar):",
            "        self.out(f'bar: {bar}')",
        ])
        r = s.run("--bar 1")
        self.assertTrue("bar: 1" in r)

        s = FileScript([
            "class Default(Command):",
            "    def handle(self, bar):",
            "        self.foobar(f'bar: {bar}')",
        ])
        with self.assertRaises(subprocess.CalledProcessError):
            r = s.run("--bar 1")

    def test_call(self):
        self.skip("Disabled while refactoring call")

        s = FileScript("""
            class Foo(Command):
                class Bar(Command):
                    class Che(Command):
                        async def handle(self, subcommands):
                            await self.call(subcommands)
                    class Boo(Command):
                        async def handle(self):
                            print("success")
        """)

        r = s.run("foo bar che \"foo bar boo\"")
        self.assertTrue("success" in r)

        r = s.run("foo bar che \"bar boo\"")
        self.assertTrue("success" in r)

        r = s.run("foo bar che \"boo\"")
        self.assertTrue("success" in r)

