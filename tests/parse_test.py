# -*- coding: utf-8 -*-
import subprocess
import argparse

from captain.compat import *
from captain.logging import QuietFilter
from captain.call import Command

from . import TestCase, FileScript


class ArgumentParserTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        # after this class is done testing the quiet functionality reset
        # logging
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

    def test_quiet_logging(self):
        s = FileScript([
            "import sys",
            "import logging",
            "logging.basicConfig(",
            "  format='[%(levelname)s] %(message)s',",
            "  level=logging.DEBUG,",
            "  stream=sys.stdout,",
            ")",
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

        r = s.run_process('--quiet=-C')
        self.assertRegex(r, r"^\[CRITICAL]\s+critical\s*$")

        r = s.run_process('--quiet=-I')
        self.assertEqual("[INFO] info\nout", r)

        r = s.run_process("-qqqqq")
        self.assertFalse("critical" in r)

        r = s.run_process("-qqqq")
        self.assertTrue("critical" in r)

        r = s.run_process("-qqq")
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

        r = s.run_process("-qq")
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

        r = s.run_process("-q")
        self.assertTrue("info" in r)
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

    def test_quiet_default(self):
        s = FileScript([
            "import sys",
            "import logging",
            "logging.basicConfig(",
            "  format='[%(levelname)s] %(message)s',",
            "  level=logging.DEBUG, stream=sys.stdout",
            ")",
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

        r = s.run_process("--quiet=+D", CAPTAIN_QUIET_DEFAULT="")
        self.assertTrue("debug" in r)
        self.assertTrue("info" in r)
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

        # this won't call QuietAction.__call__()
        r = s.run_process(CAPTAIN_QUIET_DEFAULT="D")
        self.assertFalse("debug" in r)
        self.assertFalse("verbose" in r)

        r = s.run_process("--quiet=+D", CAPTAIN_QUIET_DEFAULT="D")
        self.assertTrue("debug" in r)
        self.assertTrue("verbose" in r)

        r = s.run_process("--quiet=+D", CAPTAIN_QUIET_DEFAULT="DI")
        self.assertTrue("debug" in r)
        self.assertFalse("info" in r)
        self.assertFalse("out" in r)

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

