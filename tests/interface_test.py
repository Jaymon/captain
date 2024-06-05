# -*- coding: utf-8 -*-

from . import testdata, TestCase, FileScript, ModuleScript


class ApplicationTest(TestCase):
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

