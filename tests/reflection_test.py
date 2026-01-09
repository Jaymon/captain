# -*- coding: utf-8 -*-
import argparse

from captain.reflection import (
    ReflectCommand,
    Argument,
    Pathfinder,
)
from captain import Command, Application

from . import TestCase, FileScript


class ReflectCommandTest(TestCase):
    def test_desc_method(self):
        class Default(Command):
            def handle(self):
                """the description on method doc"""
                pass

        cbi = ReflectCommand(Default)
        self.assertEqual("the description on method doc", cbi.get_docblock())

        class Default(Command):
            # the description on method comment
            # and the second line
            def handle(self):
                pass

        cbi = ReflectCommand(Default)
        self.assertEqual(
            "the description on method comment\nand the second line",
            cbi.get_docblock()
        )

    def test_desc_class(self):
        class Default(Command):
            """the description on class doc"""
            def handle(self):
                pass

        cbi = ReflectCommand(Default)
        self.assertEqual("the description on class doc", cbi.get_docblock())

        cbi = ReflectCommand(FileScript([
            "# the description on class comment",
            "# and the second line",
            "class Default(Command):",
            "    def handle(self): pass",
        ]).command_class())

        self.assertEqual(
            "the description on class comment\nand the second line",
            cbi.get_docblock()
        )

    def test_property_argument(self):
        rc = ReflectCommand(FileScript([
            "class Default(Command):",
            "    foo = Argument('--bar')",
            "    def handle(self): pass",
        ]).command_class())

        args = list(rc.get_arguments())
        self.assertEqual(1, len(args))
        self.assertEqual("foo", args[0][0].name)

    def test_get_arguments(self):
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

        am = {}
        for a in ChildCommand.reflect().get_arguments():
            am[a[0].name] = a[0]

        self.assertTrue("child foo" in am["foo"][1]["help"])
        self.assertTrue("parent bar" in am["bar"][1]["help"])


class ReflectMethodTest(TestCase):
    def test_get_arguments(self):
        cbi = ReflectCommand(FileScript([
            "class Default(Command):",
            "    @arg('--foo', '-f', default=2, help='foo value')",
            "    @arg('--bang-one', '-b', default=4, help='bang value')",
            "    def handle(self, foo, bar=1, che=3, **kwargs): pass",
        ]).command_class()).reflect_method()

        args = list(cbi.get_arguments())

        self.assertEqual("foo", args[0][0][1]["dest"])
        self.assertEqual("bang_one", args[3][0][1]["dest"])

    def test_annotation_1(self):
        #def handle(self, a1: int, a2: str, /, *, k1: str, k2: bool = False)
        rm = ReflectCommand(FileScript("""
            class Foo(Command):
                def handle(self, a1: int, /, *, k1: str, k2: bool = False):
                    pass
        """).command_class("Foo")).reflect_method()

        am = {}
        for a in rm.get_arguments():
            am[a[0].name] = a[0]

        self.assertEqual(3, len(am))
        self.assertEqual("store_true", am["k2"][1]["action"])


class ArgumentTest(TestCase):
    def test___new__(self):
        pa = Argument("--foo-bar", "--foo", "-f", default=2, help="foo value")
        self.assertTrue("--foo" in pa[0])
        self.assertEqual("foo_bar", pa.name)

        pa = Argument(
            "--foo-bar", "--foo", "-f",
            dest="foo",
            default=2,
            help="foo value"
        )
        self.assertTrue("--foo-bar" in pa[0])
        self.assertEqual("foo", pa.name)

    def test_merge_environment(self):
        """Make sure an environment variable argument merges correctly"""
        a1 = Argument("--foo", dest="foo", required=True)
        a2 = Argument("--foo", "$FOO", default=1)

        a1.merge(a2)
        self.assertEqual("foo", a1.name)
        self.assertTrue("default" in a1[1])

    def test_custom_standard_type(self):
        class FooType(str):
            def __new__(cls, d):
                d = "HAPPY" + d
                return super().__new__(cls, d)

        s = Argument("--footype", type=FooType)

        parser = argparse.ArgumentParser()
        parser.add_argument(*s[0], **s[1])
        args = parser.parse_args(["--footype", "/foo/bar/che"])
        self.assertTrue(args.footype.startswith("HAPPY"))

    async def test_class_property(self):
        s = FileScript([
            "class Default(Command):",
            "    foo = Argument('--foo', type=int)",
            "    bar = Argument('--bar', action='store_true')",
            "    che = Argument('--che', required=True)",
            "    def handle(self):",
            "        print(f'foo: {self.foo}, bar: {self.bar}')",
            "        print(f'che={self.che}')",
        ])

        r = await s.run("--foo=1 --bar --che=che")
        self.assertTrue("foo: 1" in r)
        self.assertTrue("bar: True" in r)
        self.assertTrue("che=che" in r)

    def test_no_names(self):
        c = FileScript("""
            class Default(Command):
                a1 = Argument(type=int)
                def handle(self): pass
        """).command_class()

        self.assertEqual("a1", c.a1[1]["dest"])
        self.assertTrue("--a1", c.a1[0])

        a2 = Argument(dest="foo")
        self.assertEqual("foo", a2[1]["dest"])
        self.assertTrue("--foo", a2[0])

    def test_infer_dest_positional(self):
        a = Argument("a1")
        self.assertFalse("dest" in a[1])

    def test_get_keywords(self):
        a = Argument("--foo-bar")
        keywords = a.get_keywords()
        self.assertEqual(4, len(keywords))
        self.assertTrue("--foo-bar" in keywords)
        self.assertTrue("--foo_bar" in keywords)

        a = Argument("foo-bar")
        keywords = a.get_keywords()
        self.assertEqual(0, len(keywords))


class PathfinderTest(TestCase):
    def test_add_class(self):
        modpath = self.get_module_name(2, "commands")
        self.create_module(
            [
                "from captain import Command",
                "",
                "class CheBoo(Command):",
                "    def handle(self):",
                "        pass",
                #"        self.output.out('foo-bar che-boo')",
                "",
                "class Default(Command):",
                "    def handle(self):",
                "        pass",
                #"        self.output.out('foo-bar')",
            ],
            modpath=modpath + ".foo_bar",
            load=True
        )

        pf = Application([modpath]).pathfinder

        value = pf.get(["foo-bar"])
        self.assertEqual("Default", value["command_class"].__name__)

        value = pf.get(["foo-bar", "che-boo"])
        self.assertEqual("CheBoo", value["command_class"].__name__)
        self.assertTrue(issubclass(pf.get([])["command_class"], Command))

    def test_multi(self):
        modpath = self.create_module([
            "from captain import Command",
            "",
            "class Che(Command):",
            "    def handle(self, foo: int, bar: int = 1):",
            "        pass",
            "",
            "class Bam(Command):",
            "    def handle(self, **kwargs):",
            "        pass",
        ], load=True)

        pf = Application([modpath]).pathfinder

        self.assertEqual(2, len(pf))
        self.assertEqual("Che", pf.get("che")["command_class"].__name__)
        self.assertEqual("Bam", pf.get("bam")["command_class"].__name__)

    def test_module_description(self):
        modpath = self.create_module({
            "foo": {
                "": "'''bundles foo subcommands'''",
                "bar": """
                    '''bundles bar subcommands'''
                    from captain import Command
                    class Che(Command): pass
                """,
            }
        }, load=True)

        pf = Application([modpath]).pathfinder

        self.assertTrue("foo subcommands" in pf["foo"]["description"])
        self.assertTrue("bar subcommands" in pf["foo", "bar"]["description"])
        self.assertEqual("", pf["foo", "bar", "che"]["description"])

    async def test_default_node(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self, foo, bar):",
            "        print(f'foo: {foo}')",
            "        print(f'bar: {bar}')",
        ])

        r = await s.run("--bar 1 --foo=2")
        self.assertTrue("bar: 1" in r)
        self.assertTrue("foo: 2" in r)

    async def test_method_node(self):
        s = FileScript("""
            class Foo(Command):
                def handle_bar(self):
                    print("foo bar")
                def handle_che(self):
                    print("foo che")
        """)

        self.assertEqual("foo bar", await s.run("foo bar"))
        self.assertEqual("foo che", await s.run("foo che"))

        r = await s.run("foo")
        self.assertTrue("usage" in r)

        with self.capture() as c:
            await s.application.call("foo", "bar")
            self.assertEqual("foo bar", str(c).strip())

    async def test_aliases(self):
        """
        https://github.com/Jaymon/captain/issues/98
        """
        modpath = self.create_module({
            "foo_bar": {
                "che_boo": """
                    from captain import Command
                    class WooToo:
                        class BamFoo(Command): pass
                """,
            },
        })

        p = Application([modpath]).parser

        n = p.parse_args(["foo_bar", "che_boo", "WooToo"])
        self.assertEqual("woo-too", n._pathfinder_node.key)

        n = p.parse_args(["foo-bar", "che-boo", "woo-too"])
        self.assertEqual("woo-too", n._pathfinder_node.key)

    async def test_lowercase_subcommand_class_names(self):
        """
        https://github.com/Jaymon/captain/issues/97
        """
        s = FileScript("""
            class foo(Command):
                def handle(self):
                    print("foo")
        """)

        a = s.application
        self.assertTrue("foo" in a.pathfinder)
        self.assertEqual("foo", a.pathfinder["foo"]["class_name"])

