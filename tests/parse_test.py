# -*- coding: utf-8 -*-
import subprocess
import argparse

from captain.compat import *
from captain.logging import QuietFilter
from captain.call import Command

from . import TestCase, FileScript


class ArgumentParserTest(TestCase):
    def tearDown(self):
        super().tearDown()

        # after each test reset logging
        QuietFilter.reset()

    def test_quiet_parsing(self):
        p = FileScript().parser

        #p.add_argument('args', nargs="*")
        #rquiet = p._option_string_actions["--quiet"].OPTIONS
        rargs = ["arg1", "arg2"]

        with self.assertRaises((argparse.ArgumentError, SystemExit)):
            p.parse_args(['-q', '--quiet=D'])

        args = p.parse_args(['-q', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("D", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['--quiet', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIWEC", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['-qqq', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['--quiet=DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['--quiet', 'DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['-Q', 'DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['--quiet=-EC', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("DIW"), set(getattr(args, "<QUIET_INJECT>")))

        args = p.parse_args(['-Q=-C', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("DIWE"), set(getattr(args, "<QUIET_INJECT>")))

        args = p.parse_args(['--quiet', '-DW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("IEC"), set(getattr(args, "<QUIET_INJECT>")))

        args = p.parse_args(['--quiet', 'DWarg', 'arg1', 'arg2'])
        self.assertEqual(["DWarg"] + rargs, args.args)
        self.assertEqual("DIWEC", getattr(args, "<QUIET_INJECT>"))

        p = FileScript().parser

        args = p.parse_args(['--quiet'])
        self.assertEqual("DIWEC", getattr(args, "<QUIET_INJECT>"))

        args = p.parse_args(['--quiet', 'DWI'])
        self.assertEqual("DWI", getattr(args, "<QUIET_INJECT>"))

        p = FileScript().parser
        p.add_argument('-D', action="store_true")

        args = p.parse_args(['--quiet', '-D'])
        self.assertEqual("DIWEC", getattr(args, "<QUIET_INJECT>"))
        self.assertTrue(args.D)

    async def test_quiet_1(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self):",
            "        self.output.verbose('verbose')",
            "        self.output.out('out')",
            "        self.output.err('err')",
        ])

        r = await s.run('')
        self.assertTrue("err" in r)
        self.assertTrue("verbose" in r)
        self.assertTrue("out" in r)

        r = await s.run('--quiet=-WE')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

        r = await s.run('--quiet=D')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertTrue("out" in r)

        r = await s.run('--quiet')
        self.assertFalse("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

    async def test_quiet_override(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg(",
            "        '--quiet', '-Q', '-q',",
            "        action='store_true',",
            "        help='override quiet'"
            "    )",
            "    def handle(self, quiet):",
            "        self.output.out(quiet)",
        ])
        r = await s.run('--help')
        self.assertTrue("override quiet" in r)
        self.assertNotRegex(r, r"-Q\s+QUIET")

        r = await s.run('--quiet')
        self.assertEqual("True", r)

        s = FileScript([
            "class Default(Command):",
            "    @arg('--quiet', action='store_true', help='override quiet')",
            "    def handle(self, quiet):",
            "        pass",
        ])

        r = await s.run('--help')
        self.assertRegex(r, r"--quiet\s+override\s+quiet")
        self.assertRegex(r, r"-Q\s+<QUIET")

    async def test_quiet_logging(self):
        s = FileScript([
            "import sys",
            "import logging",
            "logging.basicConfig(",
            "  format='[%(levelname)s] %(message)s',",
            "  level=logging.DEBUG,",
            "  stream=sys.stdout,",
            ")",
            "logging.getLogger('datatypes').setLevel(logging.ERROR)",
            "logging.getLogger('asyncio').setLevel(logging.ERROR)",
            "logger = logging.getLogger(__name__)",
            "",
            "class Default(Command):",
            "    def handle(self):",
            "        logger.debug('debug')",
            "        logger.info('info')",
            "        logger.warning('warning')",
            "        logger.error('error')",
            "        logger.critical('critical')",
            "        self.output.verbose('verbose')",
            "        self.output.out('out')",
            "        self.output.err('err')",
        ])

        with self.assertLogs() as cm:
            r = await s.run('--quiet=-I')
            self.assertEqual(1, len(cm.records))
            self.assertEqual("info", cm.records[0].message)
            self.assertEqual("out", r)

        with self.assertLogs() as cm:
            r = await s.run('--quiet=-C')
            self.assertEqual(1, len(cm.records))
            self.assertEqual("critical", cm.records[0].message)
            self.assertEqual("", r)

        with self.assertRaises(AssertionError):
            with self.assertLogs() as cm:
                r = await s.run("-qqqqq")

        with self.assertLogs() as cm:
            await s.run("-qqqq")
            self.assertEqual(1, len(cm.records))
            self.assertEqual("critical", cm.records[0].message)

        with self.assertLogs() as cm:
            r = await s.run("-qqq")
            self.assertEqual(2, len(cm.records))
            self.assertEqual("error", cm.records[0].message)
            self.assertEqual("critical", cm.records[1].message)

        with self.assertLogs() as cm:
            r = await s.run("-qq")
            self.assertEqual("warning", cm.records[0].message)
            self.assertEqual("error", cm.records[1].message)
            self.assertEqual("critical", cm.records[2].message)

        with self.assertLogs() as cm:
            r = await s.run("-q")
            self.assertEqual("info", cm.records[0].message)
            self.assertEqual("warning", cm.records[1].message)
            self.assertEqual("error", cm.records[2].message)
            self.assertEqual("critical", cm.records[3].message)

    async def test_quiet_default(self):
        s = FileScript("""
            import sys
            import logging

            logging.basicConfig(
                format="[%(levelname)s] %(message)s",
                level=logging.DEBUG,
                stream=sys.stdout,
            )
            logger = logging.getLogger(__name__)

            class Default(Command):
                def handle(self):
                    logger.debug("debug")
                    logger.info("info")
                    logger.warning("warning")
                    logger.error("error")
                    logger.critical("critical")
                    self.output.verbose("verbose")
                    self.output.out("out")
                    self.output.err("err")
        """)

        r = await s.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="D")
        self.assertTrue("debug" in r)
        self.assertTrue("verbose" in r)

        # this won't call QuietAction.__call__()
        r = await s.run(CAPTAIN_QUIET_DEFAULT="D")
        self.assertFalse("debug" in r)
        self.assertFalse("verbose" in r)

        r = await s.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="DI")
        self.assertTrue("debug" in r)
        self.assertFalse("info" in r)
        self.assertFalse("out" in r)

        r = await s.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="")
        self.assertTrue("debug" in r)
        self.assertTrue("info" in r)
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

    async def test_parse_handle_args(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg('--foo', type=int)",
            "    @arg('--bar', type=int)",
            "    def handle(self, foo, bar):",
            "        print('foo: {}, bar: {}'.format(foo, bar))"
        ])

        with self.assertRaises(subprocess.CalledProcessError):
            r = await s.run("--foo 1 --bar 2 --che 3")

        r = await s.run("--foo 1 --bar 2")
        self.assertTrue("foo: 1, bar: 2" in r)

    async def test_parse_custom_action(self):
        s = FileScript("""
            import argparse

            class FooAction(argparse.Action):
                def parse_args(self, parser, arg_strings): return arg_strings
                def get_value(self, value): return int(value) + 1
                def __call__(self, parser, namespace, values, option_string):
                    setattr(namespace, self.dest, values)

            class Che(Command):
                @arg('--foo', default='1', action=FooAction)
                @arg('--bar', type=int)
                def handle(self, foo, bar):
                    print('foo: {}, bar: {}'.format(foo, bar))

            class Bam(Command):
                def handle(self, **kwargs):
                    print('kwargs: {}'.format(kwargs))
        """)

        r = await s.run("bam --foo 1 --bar 2")
        self.assertTrue("foo': '1'" in r)

        r = await s.run("che --bar 2")
        self.assertTrue("foo: 2" in r)

        r = await s.run("che --foo 1 --bar 2")
        self.assertTrue("foo: 2" in r)

    async def test_handle_quiet(self):
        s = FileScript(subcommands=True)
        r = await s.run("--help")
        self.assertTrue("--quiet" in r)

        r = await s.run("foo --help")
        self.assertTrue("subcommand description")
        self.assertTrue("--quiet" in r)

        r = await s.run("--help foo")
        self.assertTrue("--quiet" in r)

    async def test_parse_undefined_normalization(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self, **kwargs):",
            "        print('kwargs: {}'.format(kwargs))"
        ])

        r = await s.run("--foo-bar 1")
        self.assertTrue("'foo_bar':" in r)
        self.assertFalse("'foo-bar':" in r)

    def test_parse_unnamed(self):
        parser = FileScript([
            "class Default(Command):",
            "    def handle(self, foo, bar):",
            "        print('foo: {}'.format(foo))",
            "        print('bar: {}'.format(bar))",
        ]).parser

        parsed = parser.parse_args(["--bar", "1", "--foo=2"])
        self.assertEqual("2", parsed.foo)
        self.assertEqual("1", parsed.bar)

        parsed = parser.parse_args(["1", "--bar=2"])
        self.assertEqual("1", parsed.foo)
        self.assertEqual("2", parsed.bar)

        parsed = parser.parse_args(["1", "2"])
        self.assertEqual("1", parsed.foo)
        self.assertEqual("2", parsed.bar)

    async def test_help_aliases(self):
        s = FileScript([
            "class FooBar(Command):",
            "    def handle(self): pass",
            "",
            "class BarChe(Command):",
            "    def handle(self): pass",
            "",
            "class CheBoo(Command):",
            "    def handle(self): pass",
        ])

        r = await s.run("--help")
        self.assertTrue("foo-bar" in r)
        self.assertFalse("FooBar" in r)

    async def test_subcommand_variations(self):
        s = FileScript([
            "class FooBar(Command):",
            "    def handle(self): self.out('FooBar')",
            "",
            "class BarChe(Command):",
            "    def handle(self): self.out('BarChe')",
        ])

        r = await s.run("foobar")

    async def test_environ_arg_1(self):
        """
        https://github.com/Jaymon/captain/issues/77
        """
        s = FileScript([
            "class Default(Command):",
            "    @arg('--foo', '$FOO', default=1)",
            "    def handle(self, foo):",
            "        self.out(foo)",
        ])

        r = await s.run("")
        self.assertEqual("1", r)

        with self.environ(FOO="2"):
            r = await s.run("")
            self.assertEqual("2", r)

            r = await s.run("--foo=3")
            self.assertEqual("3", r)

    async def test_environ_arg_required(self):
        """Make sure environment defaults still work if the argument is marked
        as required
        """
        s = FileScript("""
            class Default(Command):
                @arg('--foo', '$FOO', required=True)
                def handle(self, foo):
                    self.out(foo)
        """)

        p = s.parser

        with self.assertRaises(argparse.ArgumentError):
            p.parse_args([""])

        with self.environ(FOO="2"):
            r = await s.run("")
            self.assertEqual("2", r)


    async def test_option_string_variations(self):
        s = FileScript([
            "class Default(Command):",
            "    foo_bar = Argument('--fb', '--fo-bo')",
            "    @arg('--remote-dir', dest='remote_directory')",
            "    def handle(self, remote_directory):",
            "        self.out(self.foo_bar)",
            "        self.out(remote_directory)",
        ])

        r = await s.run("--help")
        self.assertFalse("remote_directory" in r)
        self.assertTrue("remote-directory" in r)
        self.assertFalse("foo-bar" in r)


        v1 = "other"
        v2 = "something"
        r = await s.run(f"--foo_bar={v1} --remote-directory {v2}")
        self.assertTrue(v1 in r)
        self.assertTrue(v2 in r)

    async def test_unknown_args(self):
        s = FileScript("""
            class Default(Command):
                def handle(self, *args, **kwargs):
                    self.out(args)
                    self.out(kwargs)
                    pass
        """)

        r = await s.run("--foo 1 --bar 2 3 4")
        self.assertTrue("('3', '4')" in r)
        self.assertTrue("{'foo': '1', 'bar': '2'}" in r)

    async def test_annotation_dest_dash(self):
        """When the value could be either a positional or keyword it would
        fail with:

            TypeError: ... got an unexpected keyword argument 'foo-bar'

        This makes sure that is fixed
        """
        s = FileScript("""
            class Default(Command):
                def handle(self, foo_bar: str = "che"):
                    self.out(foo_bar)
        """)

        r = await s.run("")
        self.assertEqual("che", r)

    async def test_annotation_positional_dash(self):
        """When the value could be either a positional or keyword it would
        fail with:

            TypeError: ... got an unexpected keyword argument 'foo-bar'

        This makes sure that is fixed
        """
        s = FileScript("""
            class Default(Command):
                def handle(self, foo_bar: str, /):
                    self.out(foo_bar)
        """)

        r = await s.run("che")
        self.assertEqual("che", r)

    async def test_annotation_positional_default_value(self):
        """If the positional has a default value then it doesn't need to be
        passed in, but that only works in python if nargs=? is set, this makes
        sure this use case gets set correctly
        """
        p = FileScript("""
            class Default(Command):
                def handle(self, foo_bar: str = "", /):
                    self.out(foo_bar)
        """).parser

        r = p.parse_args([])
        self.assertEqual("", r.foo_bar)

        r = p.parse_args(["che"])
        self.assertEqual("che", r.foo_bar)

    async def test_annotation_bool_store_true(self):
        """boolean flags can't have a type, this makes sure type is removed
        if the action is inferred to be "store_true" or "store_false"
        """
        s = FileScript("""
            class Default(Command):
                def handle(self, *, foo_bar: bool = False):
                    self.out(foo_bar)
        """)

        r = await s.run("")
        self.assertEqual("False", r)

        r = await s.run("--foo-bar")
        self.assertEqual("True", r)

    async def test_required_flag_dest_different(self):
        s = FileScript("""
            class _Command(Command):
                bar_flag = Argument("--bar", type=int, required=True)

            class Foo(_Command):
                def handle(self):
                    self.out(self.bar_flag)
        """)

        r = await s.run("foo --bar=1")
        self.assertEqual(1, int(r))

    async def test_ignore_default_subcommand_args_3(self):
        s = FileScript("""
            class Default(Command):
                def handle(self, bar: str, /):
                    pass

            class Foo(Command):
                def handle(self):
                    pass
        """)

        p = s.parser

        # this is built-in behavior, "parent" commands can't have positional
        # arguments
        with self.assertRaises(argparse.ArgumentError):
            p.parse_args(["bar"])

        r = p.parse_args(["foo"])
        self.assertEqual(
            "Foo",
            r._pathfinder_node.value["command_class"].__name__,
        )

    async def test_original_values_reset(self):
        s = FileScript("""
            class Default(Command):
                def handle(self, *, che: str):
                    self.out("default")

            class Foo(Command):
                def handle(self):
                    self.out("foo")
        """)

        p = s.parser

        r = p.parse_args(["foo"])
        self.assertEqual(
            "Foo",
            r._pathfinder_node.value["command_class"].__name__,
        )

        # when a subcommand is ran, the original action values get changed,
        # these need to be restored if a parent command is ran (eg, through
        # `Command.call` or the like). This makes sure a required argument
        # causes an error if the "parent" command is ran after a subcommand
        with self.assertRaises(argparse.ArgumentError):
            p.parse_args([])

    async def test_nargs_list_1(self):
        """The positionals name is equivalent to `nargs="*"`"""
        s = FileScript("""
            class Default(Command):
                def handle(self, *args):
                    pass
        """)

        p = s.parser

        r = p.parse_args([])
        self.assertFalse("args" in r)

        r = p.parse_args(["1", "2"])
        self.assertEqual(2, len(r.args))

    async def test_nargs_list_2(self):
        """A `list` annotation on a postional is equivalent to `nargs="+"`"""
        s = FileScript("""
            class Default(Command):
                def handle(self, args: list[str], /):
                    pass
        """)

        p = s.parser

        with self.assertRaises(argparse.ArgumentError):
            p.parse_args([])

        r = p.parse_args(["1", "2"])
        self.assertEqual(2, len(r.args))

    async def test_nargs_list_3(self):
        """A `list` annotation on an optional postional is equivalent to
        `nargs="*"`"""
        s = FileScript("""
            class Default(Command):
                def handle(self, args: list[str]|None = None, /):
                    pass
        """)

        p = s.parser

        r = p.parse_args(["1", "2"])
        self.assertEqual(2, len(r.args))


        r = p.parse_args([])
        self.assertEqual([], r.args)

    async def test_keyword_list_1(self):
        """Keywords with a list annotation are equivalent to `action="append"`
        """
        s = FileScript("""
            class Default(Command):
                def handle(self, *, foos: list[str]):
                    pass
        """)

        p = s.parser

        r = p.parse_args(["--foo", "1", "--foo=2"])
        self.assertEqual(2, len(r.foos))

        with self.assertRaises(argparse.ArgumentError):
            p.parse_args([])

