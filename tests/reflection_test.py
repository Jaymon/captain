# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import argparse

from captain.reflection import (
    ReflectCommand,
    ReflectMethod,
    ParseArg,
)
from captain import Command

from . import testdata, TestCase, FileScript, ModuleScript


class ReflectCommandTest(TestCase):
    def test_desc_method(self):
        class Default(Command):
            def handle(self):
                """the description on method doc"""
                pass

        cbi = ReflectCommand(Default)
        self.assertEqual("the description on method doc", cbi.desc)

        class Default(Command):
            # the description on method comment
            # and the second line
            def handle(self):
                pass

        cbi = ReflectCommand(Default)
        self.assertEqual("the description on method comment\nand the second line", cbi.desc)

    def test_desc_class(self):
        class Default(Command):
            """the description on class doc"""
            def handle(self):
                pass

        cbi = ReflectCommand(Default)
        self.assertEqual("the description on class doc", cbi.desc)

        c = FileScript([
            "# the description on class comment",
            "# and the second line",
            "class Default(Command):",
            "    def handle(self): pass",
        ]).command()

        cbi = ReflectCommand(c)
        self.assertEqual("the description on class comment\nand the second line", cbi.desc)

    def test_desc_module(self):
        s = FileScript([
            '#!/usr/bin/env python',
            '# -*- coding: utf-8 -*-',
            '# the description on module comment',
            "# and the second line",
            "from captain import Command",
            "class Default(Command): pass",
        ], header="")

        cbi = ReflectCommand(s.command())
        self.assertEqual("the description on module comment\nand the second line", cbi.desc)

        s = FileScript([
            '"""the description on module doc"""',
            "from captain import Command",
            "class Default(Command): pass",
        ], header="")

        cbi = ReflectCommand(s.command())
        self.assertEqual("the description on module doc", cbi.desc)


class ReflectMethodTest(TestCase):
    def test_signature(self):
        cbi = FileScript([
            "class Default(Command):",
            "    def handle(self, foo, bar=1, che=3, **kwargs): pass",
        ]).reflect_method()

        sig = cbi.signature
        self.assertEqual(set(["foo"]), sig["required"])
        self.assertEqual(["foo", "bar", "che"], sig["names"])
        self.assertEqual(1, sig["defaults"]["bar"])
        self.assertEqual("kwargs", sig["**_name"])
        self.assertIsNone(sig["*_name"])

    def test_parseargs(self):
        cbi = FileScript([
            "class Default(Command):",
            "    @arg('--foo', '-f', default=2, help='foo value')",
            "    @arg('--bang-one', '-b', default=4, help='bang value')",
            "    def handle(self, foo, bar=1, che=3, **kwargs): pass",
        ]).reflect_method()

        args = list(cbi.parseargs())
        self.assertEqual("foo", args[0][1]["dest"])
        self.assertEqual("bang_one", args[1][1]["dest"])

    def test_omit(self):
        """Makes sure you can ignore flags when inheriting

        https://github.com/Jaymon/captain/issues/73
        """
        s = FileScript([
            "class Baz(Command):",
            "    @arg('--baz-foo', default='1')",
            "    @arg('--baz-bar', type=int)",
            "    def handle(self, **kwargs): pass",
            "",
            "class Foo(Command):",
            "    @arg('--foo-foo', default='1')",
            "    @arg('--foo-bar', type=int)",
            "    def handle(self, **kwargs): pass",
            "",
            "class Che(Command):",
            "    @arg('--che-foo', default='1')",
            "    @arg('--che-bar', type=int)",
            "    def handle(self, **kwargs): pass",
            "",
            "class Bam(Command):",
            "    @args(Che, Foo, omit=['foo-foo', 'che-bar'])",
            "    @args(Baz, omit=['baz-foo'])",
            "    def handle(self, **kwargs):",
            "        print('kwargs: {}'.format(kwargs))",
        ])

        contains = set(["baz-bar", "foo-bar", "che-foo"])
        mi = s.reflect_method("Bam")

        pas = list(mi.parseargs())
        self.assertEqual(len(contains), len(pas))
        for pa in pas:
            self.assertTrue(pa.names & contains)

    def test_override(self):
        """Makes sure you can override flags

        https://github.com/Jaymon/captain/issues/73
        """
        s = FileScript([
            "class Foo(Command):",
            "    @arg('foo', nargs='*')",
            "    def handle(self, **kwargs): pass",
            "",
            "class Bar(Command):",
            "    @args(Foo)",
            "    @arg('foo', nargs='+')",
            "    def handle(self, **kwargs): pass",
        ])

        mi = s.reflect_method("Bar")

        pas = list(mi.parseargs())
        self.assertEqual(1, len(pas))
        self.assertEqual("+", pas[0].kwargs["nargs"])


class ParseArgTest(TestCase):
    def test___new__(self):
        pa = ParseArg("--foo-bar", "--foo", "-f", default=2, help="foo value")
        self.assertTrue("--foo_bar" in pa[0])
        self.assertEqual("foo-bar", pa.name)

        pa = ParseArg("--foo-bar", "--foo", "-f", dest="foo", default=2, help="foo value")
        self.assertTrue("--foo_bar" in pa[0])
        self.assertEqual("foo", pa.name)

    def test_merge_signature_1(self):
        pa = ParseArg("--foo", "-f", help="foo value")
        pa.merge_signature({"names": ["foo"], "defaults": {"foo": 1}})
        self.assertFalse(pa[1]["required"])
        self.assertEqual("foo", pa[1]["dest"])
        self.assertEqual(int, pa[1]["type"])

    def test_merge_signature_2(self):
        pa = ParseArg("-f", dest="foo", help="foo value")
        pa.merge_signature({"names": ["foo"], "defaults": {"foo": 1}})
        self.assertFalse(pa[1]["required"])
        self.assertEqual("foo", pa[1]["dest"])
        self.assertEqual(1, pa[1]["default"])

    def test_default(self):
        pa = ParseArg('foo')
        pa.set_default(True)
        self.assertEqual("store_false", pa[1]["action"])

    def test_custom_standard_type(self):
        class FooType(str):
            def __new__(cls, d):
                d = "HAPPY" + d
                return super(FooType, cls).__new__(cls, d)

        s = ParseArg("--footype", type=FooType)

        parser = argparse.ArgumentParser()
        parser.add_argument(*s[0], **s[1])
        args = parser.parse_args(["--footype", "/foo/bar/che"])
        self.assertTrue(args.footype.startswith("HAPPY"))

