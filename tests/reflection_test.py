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
        self.assertEqual("foo", args[0].name)


class ReflectMethodTest(TestCase):
    def test_signature_info(self):
        cbi = ReflectCommand(FileScript([
            "class Default(Command):",
            "    def handle(self, foo, bar=1, che=3, **kwargs): pass",
        ]).command_class()).reflect_method()

        sig = cbi.get_signature_info()
        self.assertEqual(set(["foo"]), sig["required"])
        self.assertEqual(["foo", "bar", "che", "kwargs"], sig["names"])
        self.assertEqual(1, sig["defaults"]["bar"])
        self.assertEqual("kwargs", sig["keywords_name"])
        self.assertEqual("", sig["positionals_name"])

    def test_arguments(self):
        cbi = ReflectCommand(FileScript([
            "class Default(Command):",
            "    @arg('--foo', '-f', default=2, help='foo value')",
            "    @arg('--bang-one', '-b', default=4, help='bang value')",
            "    def handle(self, foo, bar=1, che=3, **kwargs): pass",
        ]).command_class()).reflect_method()

        args = list(cbi.arguments())
        self.assertEqual("foo", args[0][1]["dest"])
        self.assertEqual("bang_one", args[1][1]["dest"])

    def test_omit(self):
        """Makes sure you can ignore flags when inheriting

        https://github.com/Jaymon/captain/issues/73
        """
        mi = ReflectCommand(FileScript([
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
        ]).command_class("Bam")).reflect_method()

        contains = set(["baz-bar", "foo-bar", "che-foo"])

        pas = list(mi.arguments())
        self.assertEqual(len(contains), len(pas))
        for pa in pas:
            self.assertTrue(pa.names & contains)

    def test_override(self):
        """Makes sure you can override flags

        https://github.com/Jaymon/captain/issues/73
        """
        mi = ReflectCommand(FileScript([
            "class Foo(Command):",
            "    @arg('foo', nargs='*')",
            "    def handle(self, **kwargs): pass",
            "",
            "class Bar(Command):",
            "    @args(Foo)",
            "    @arg('foo', nargs='+')",
            "    def handle(self, **kwargs): pass",
        ]).command_class("Bar")).reflect_method()

        pas = list(mi.arguments())
        self.assertEqual(1, len(pas))
        self.assertEqual("+", pas[0].kwargs["nargs"])

    def test_annotation_1(self):
        #def handle(self, a1: int, a2: str, /, *, k1: str, k2: bool = False)
        rm = ReflectCommand(FileScript("""
            class Foo(Command):
                def handle(self, a1: int, /, *, k1: str, k2: bool = False):
                    pass
        """).command_class("Foo")).reflect_method()

        for a in rm.get_arguments():
            pout.v(a)

        raise ValueError("ADD ASSERTS!!!!!!!!!")
#         for rp in rm.reflect_params():
#             pout.v(rp.get_argparse_keywords())


class ArgumentTest(TestCase):
    def test___new__(self):
        pa = Argument("--foo-bar", "--foo", "-f", default=2, help="foo value")
        self.assertTrue("--foo" in pa[0])
        self.assertEqual("foo-bar", pa.name)

        pa = Argument(
            "--foo-bar", "--foo", "-f",
            dest="foo",
            default=2,
            help="foo value"
        )
        self.assertTrue("--foo-bar" in pa[0])
        self.assertEqual("foo", pa.name)

    def test_merge_signature_1(self):
        pa = Argument("--foo", "-f", help="foo value")
        pa.merge_signature({"names": ["foo"], "defaults": {"foo": 1}})
        self.assertFalse(pa[1]["required"])
        self.assertEqual("foo", pa[1]["dest"])
        self.assertEqual(int, pa[1]["type"])

    def test_merge_signature_2(self):
        pa = Argument("-f", dest="foo", help="foo value")
        pa.merge_signature({"names": ["foo"], "defaults": {"foo": 1}})
        self.assertFalse(pa[1]["required"])
        self.assertEqual("foo", pa[1]["dest"])
        self.assertEqual(1, pa[1]["default"])

    def test_merge_environment(self):
        """Make sure an environment variable argument merges correctly"""
        a1 = Argument("--foo", dest="foo", required=True)
        a2 = Argument("--foo", "$FOO", default=1)

        a1.merge(a2)
        self.assertEqual("foo", a1.name)
        self.assertTrue("default" in a1[1])

    def test_merge_error(self):
        """
        https://github.com/Jaymon/captain/issues/75

        Turns out, this isn't actually a bug and merging is working correctly,
        previously I was compensating for a positional argument having an
        arg ("foos") and a dest ("foo_names") by moving the arg to the metavar
        and then setting the dest as the arg, so the signature switched to
        `"foo_names", metavar="foos"` and then when the arguments were merged
        the "foos" metavar would override the "FOO" metavar. I think it's
        better to adhere to the default behavior rather than compensate for
        a bad signature
        """
        s = FileScript("""
            class Foo(Command):
                @arg(
                    "foos",
                    #metavar="FOO",
                    nargs="*",
                    dest="foo_names",
                    help="foo help 1"
                )
                def handle(self, *args, **kwargs): pass

            class Bar(Command):
                @args(Foo)
                @arg(
                    "foos",
                    nargs="+",
                    dest="foo_names",
                    help="foo help 2"
                )
                def handle(self, *args, **kwargs): pass
        """)

        with self.assertRaises(RuntimeError):
            s.run("bar --help")

    def test_default(self):
        pa = Argument('foo')
        pa.set_default(True)
        self.assertEqual("store_false", pa[1]["action"])

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

    def test_class_property(self):
        s = FileScript([
            "class Default(Command):",
            "    foo = Argument('--foo', type=int)",
            "    bar = Argument('--bar', action='store_true')",
            "    che = Argument('--che', required=True)",
            "    def handle(self, che):",
            "        print(f'foo: {self.foo}, bar: {self.bar}')",
            "        print(f'{self.che}={che}')",
        ])

        r = s.run("--foo=1 --bar --che=che")
        self.assertTrue("foo: 1" in r)
        self.assertTrue("bar: True" in r)
        self.assertTrue("che=che" in r)

    def test_names(self):
        pa = Argument("--foo-b", "--fb", "-f", dest="foo_bar")
        vs = pa.names
        for v in ["foo_bar", "FOO_BAR", "foo-bar"]:
            self.assertTrue(v in vs)

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

    def test_default_node(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self, foo, bar):",
            "        print(f'foo: {foo}')",
            "        print(f'bar: {bar}')",
        ])

        r = s.run("--bar 1 --foo=2")
        self.assertTrue("bar: 1" in r)
        self.assertTrue("foo: 2" in r)


