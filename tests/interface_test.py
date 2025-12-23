# -*- coding: utf-8 -*-
import subprocess

from . import TestCase, FileScript
from captain.interface import Application


class ApplicationTest(TestCase):
    def test_version(self):
        c = FileScript()
        self.assertTrue("0.0.1" in c.run("--version"))

    def test_handle_1(self):
        s = FileScript(subcommands=True)
        s.run("--bar=1 --che=2")

    def test_handle_help(self):
        s = FileScript(subcommands=True)

        # run help
        r1 = s.run("--help")
        r2 = s.run("foo --help")
        r3 = s.run("--help foo")
        self.assertEqual(r1, r3)
        self.assertNotEqual(r1, r2)

    def test_handle_sub_default(self):
        s = FileScript(subcommands=True)

        # run the main command
        r = s.run()
        self.assertTrue("success default" in r)

        r = s.run("--bar=1")
        self.assertTrue("success default" in r)

        # run the subcommand
        r = s.run("foo")
        self.assertTrue("success foo" in r)

        r = s.run("foo --bar=1")
        self.assertTrue("success foo" in r)

        # test error
        with self.assertRaises(subprocess.CalledProcessError):
            r = s.run("1")

        with self.assertRaises(subprocess.CalledProcessError):
            r = s.run("1 --bar=1")

    def test_handle_sub_no_default(self):
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, **kwargs):",
            "        print('success foo')",
        ])

        r = s.run("foo --bar=1")
        self.assertTrue("success foo" in r)

        r = s.run()
        self.assertTrue("usage" in r)

    def test_handle_error(self):
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, **kwargs):",
            "        raise ValueError('yadda yadda yadda')"
            "",
            "class Bar(Command):",
            "    def handle(self, **kwargs):",
            "        raise exception.Stop(0, 'stop message')"
        ])

        with self.assertRaises(subprocess.CalledProcessError):
            r = s.run("foo")

        r = s.run("bar")
        self.assertTrue("stop message" in r)

    def test_handle_aliases(self):
        s = FileScript([
            "class Foo_One(Command):",
            "    def handle(self, **kwargs):",
            "        self.output.out('foo_one')",
            "",
            "class FooTwo(Command):",
            "    def handle(self, **kwargs):",
            "        self.output.out('foo_two')",
        ])

        r = s.run("foo-one")
        self.assertTrue("foo_one" in r)

        r = s.run("foo_one")
        self.assertTrue("foo_one" in r)

        r = s.run("foo_two")
        self.assertTrue("foo_two" in r)

    def test_only_default(self):
        p = self.create_module([
            "from captain import Command",
            "",
            "class Default(Command):",
            "    def handle(self, *args, **kwargs):",
            "        self.output.out('default')",
        ])

        a = Application(command_prefixes=[p])

        parsed = a.parser.parse_args(["foo", "--one=1", "--two=2"])

        self.assertEqual(["foo"], parsed.args)
        self.assertEqual("1", parsed.one)
        self.assertEqual("2", parsed.two)

    def test_only_subcommands(self):
        p = self.create_module([
            "from captain import Command",
            "",
            "class Foo(Command):",
            "    def handle(self, *args, **kwargs):",
            "        self.output.out('foo')",
            "",
            "class Bar(Command):",
            "    def handle(self, *args, **kwargs):",
            "        self.output.out('bar')",
        ])

        a = Application(command_prefixes=[p])

        parsed = a.parser.parse_args(["foo", "--one=1", "--two=2"])
        self.assertEqual("1", parsed.one)
        self.assertEqual("2", parsed.two)

    def test_prefixes(self):
        p = self.create_modules({
            "far.commands": {
                "foo": [
                    "from captain import Command",
                    "",
                    "class Default(Command):",
                    "    def handle(self):",
                    "        self.output.out('foo')",
                    "",
                    "class Bar(Command):",
                    "    def handle(self):",
                    "        self.output.out('foo bar')",
                ],
                "__init__": [
                    "from captain import Command",
                    "",
                    "class Default(Command):",
                    "    def handle(self):",
                    "        self.output.out('foo')",
                ],
                "che": {
                    "__init__": [
                        "from captain import Command",
                        "",
                        "class Default(Command):",
                        "    def handle(self):",
                        "        self.output.out('che')",
                    ],
                    "boo": [
                        "from captain import Command",
                        "",
                        "class Default(Command):",
                        "    def handle(self):",
                        "        self.output.out('che boo')",
                    ],
                },
            },
        })

        a = Application(paths=[p])

        value = a.pathfinder.get(["che", "boo"])
        self.assertIsNotNone(value["parser"])

        value = a.pathfinder.get(["foo", "bar"])
        self.assertIsNotNone(value["parser"])

        value = a.pathfinder.get(["foo"])
        self.assertIsNotNone(value["parser"])

    def test_dash_underscore_subcommands(self):
        p = self.create_modules(
            {
                "commands": {
                    "foo_bar": [
                        "from captain import Command",
                        "",
                        "class CheBoo(Command):",
                        "    def handle(self):",
                        "        self.output.out('foo-bar che-boo')",
                    ],
                }
            },
            modpath=self.get_module_name()
        )

        a = Application(paths=[p])
        parsed = a.parser.parse_args(["foo-bar", "che-boo"])
        node_value = parsed._pathfinder_node.value
        self.assertEqual("CheBoo", node_value["command_class"].__name__)

    async def test_call(self):
        a = FileScript("""
            class FooBoo(Command):
                class Bar(Command):
                    class Che(Command):
                        async def handle(self, *args, **kwargs):
                            return kwargs["retcode"]
        """).application

        r = await a.call("foo-boo", "bar", "che", retcode=3)
        self.assertEqual(3, r)

        return
        with self.capture() as c:
            await a.call("foo-boo", "bar", "che", k1=1)

        pout.v(c)

