# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from . import testdata, TestCase, FileScript, ModuleScript


class ArgsTest(TestCase):
    def test_inherit(self):
        s = FileScript([
            "class Foo(Command):",
            "    @arg('--one', default=True)",
            "    @arg('--two', default=True)",
            "    def handle(self, *args, **kwargs): return 0",
            "",
            "class Bar(Command):",
            "    @args(Foo)",
            "    @arg('--three', default=True)",
            "    def handle(self, *args, **kwargs): return 0",
        ])
        r = s.run("bar --help")
        self.assertTrue("--one" in r)
        self.assertTrue("--two" in r)
        self.assertTrue("--three" in r)

    def test_inheritance_args_passing_1(self):
        s = FileScript([
            "class One(Command):",
            "    @arg('--foo', type=int, choices=[1, 2])",
            "    def handle(self): pass",
            "",
            "class Two(Command):",
            "    @args(One)",
            "    def handle(self, foo):",
            "        self.output.out(foo)",
            "",
            "class Three(Command):",
            "    @args(One)",
            "    def handle(self, foo=[4,5]):",
            "        self.output.out(foo)",
            "",
            "class Four(Command):",
            "    @args(One)",
            "    @arg('--foo', type=int, choices=[5, 6])",
            "    def handle(self, foo):",
            "        self.output.out(foo)",
        ])

        with self.assertRaises(RuntimeError):
            r = s.run("two --foo=4")

        r = s.run("two --foo=2")
        self.assertEqual("2", r)

        with self.assertRaises(RuntimeError):
            r = s.run("three --foo=2")

        r = s.run("three --foo=4")
        self.assertEqual("4", r)

        with self.assertRaises(RuntimeError):
            r = s.run("four --foo=2")

        r = s.run("four --foo=6")
        self.assertEqual("6", r)

    def test_inheritance_args_passing_2(self):
        s = FileScript([
            "class One(Command):",
            "    @arg('--foo', type=int, choices=[1, 2])",
            "    def handle(self): pass",
            "",
            "class Two(Command):",
            "    @arg('--foo', type=int, choices=[3, 4])",
            "    @arg('--bar', action='store_true')",
            "    def handle(self, foo, bar): pass",
            "",
            "class Three(Command):",
            "    @args(One, Two)",
            "    def handle(self, foo, bar):",
            "        self.output.out(foo)",
            "        self.output.out(bar)",
        ])

        r = s.run("three --help")
        self.assertTrue("{3,4}" in r)
        self.assertTrue("--bar" in r)

    def test_dest_positional(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg('f', metavar='FOO', type=int)",
            "    def handle(self, f): print(f)",
        ])

        r = s.run("--help")
        self.assertTrue("FOO" in r)

        r = s.run("1234567")
        self.assertTrue("1234567" in r)

        s = FileScript([
            "class Default(Command):",
            "    @arg('foo', dest='f', type=int)",
            "    def handle(self, f): print(f)",
        ])

        r = s.run("--help")
        self.assertTrue("foo" in r)

        r = s.run("1234567")
        self.assertTrue("1234567" in r)

