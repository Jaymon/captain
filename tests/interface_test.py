# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from . import testdata, TestCase, FileScript, ModuleScript



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
            "Foo-One",
            "foo_one",
            "FooOne"
        ])
        c_class = s.command_class("foo-one")
        self.assertEqual(a, c_class.aliases)


class CaptainTest(TestCase):
    def test_version(self):
        c = FileScript().captain

        self.assertEqual("0.0.1", c.version)

    def test_handle(self):
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
        with self.assertRaises(RuntimeError):
            r = s.run("1")

        with self.assertRaises(RuntimeError):
            r = s.run("1 --bar=1")

    def test_handle_sub_no_default(self):
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, **kwargs):",
            "        print('success foo')",
        ])

        r = s.run("foo --bar=1")
        self.assertTrue("success foo" in r)

        with self.assertRaises(RuntimeError):
            s.run()

    def test_handle_error(self):
        s = FileScript([
            "class Foo(Command):",
            "    def handle(self, **kwargs):",
            "        raise ValueError('yadda yadda yadda')"
            "",
            "class Bar(Command):",
            "    def handle(self, **kwargs):",
            "        raise self.Stop(0, 'stop message')"
        ])

        with self.assertRaises(RuntimeError):
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

        #r = s.run("")
        #r = s.run("--help")

        r = s.run("foo-one")
        self.assertTrue("foo_one" in r)

        r = s.run("foo_one")
        self.assertTrue("foo_one" in r)

        r = s.run("foo_two")
        self.assertTrue("foo_two" in r)

