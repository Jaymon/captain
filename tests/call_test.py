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

    def test_name(self):
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, **kwargs): pass",
        ])
        c_class = s.command_class("foo")
        self.assertEqual("foo", c_class.name)

        s = FileScript([
            "class Foo(Command):",
            "    name = 'bar'",
            "    def handle(self, **kwargs): pass",
        ])
        c_class = s.command_class("bar")
        self.assertEqual("bar", c_class.name)

    def test_aliases(self):
        s = FileScript([
            "class FooOne(Command):",
            "    def handle(self, **kwargs): pass",
        ])

        a = set([
            "fooone",
            "Foo_One",
            "foo_one",
            "Foo-One",
            "foo-one",
            "foo_one",
            "FooOne"
        ])
        c_class = s.command_class("foo-one")
        self.assertEqual(a, c_class.aliases)

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

    def test_arguments(self):
        class ParentCommand(Command):
            foo = Argument(
                "--foo", "-f",
                type=int,
                help="parent foo"
            )
            bar = Argument(
                "--bar", "-b",
                action="store_true",
                help="parent bar"
            )

        class ChildCommand(ParentCommand):
            foo = Argument("--foo", "-f", help="child foo")
            che = Argument("--che", "-c", required=True, help="child che")


        args = ChildCommand.arguments()
        self.assertTrue("child foo" in args["foo"][1]["help"])
        self.assertTrue("parent bar" in args["bar"][1]["help"])

