# -*- coding: utf-8 -*-
import subprocess

from captain.compat import *
from captain.logging import QuietFilter
from captain.parse import Router
from captain.call import Command

from . import testdata, TestCase, FileScript, ModuleScript


class RouterTest(TestCase):
    def test_only_default(self):
        p = self.create_module([
            "from captain import Command",
            "",
            "class Default(Command):",
            "    def handle(self, *args, **kwargs):",
            "        self.output.out('default')",
        ])

        r = Router(command_prefixes=[p])

        parsed = r.parser.parse_args(["foo", "--one=1", "--two=2"])
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

        r = Router(command_prefixes=[p])

        parsed = r.parser.parse_args(["foo", "--one=1", "--two=2"])
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
#             "cli": [
#                 "from captain import Application",
#                 "application = Application()",
#                 "application()",
#             ],
        })

        r = Router(paths=[p])

        tree = r.pathfinder.get(["che", "boo"])
        self.assertIsNotNone(tree[""]["parser"])

        tree = r.pathfinder.get(["foo", "bar"])
        self.assertIsNotNone(tree[""]["parser"])

        tree = r.pathfinder.get(["foo"])
        self.assertIsNotNone(tree[""]["parser"])


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

        with self.assertRaises(SystemExit):
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

    def test_quiet_1(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self):",
            "        self.output.verbose('verbose')",
            "        self.output.out('out')",
            "        self.output.err('err')",
        ])

        r = s.run('')
        self.assertTrue("err" in r)
        self.assertTrue("verbose" in r)
        self.assertTrue("out" in r)

        r = s.run('--quiet=-WE')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

        r = s.run('--quiet=D')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertTrue("out" in r)

        r = s.run('--quiet')
        self.assertFalse("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

    def test_quiet_override(self):
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
        r = s.run('--help')
        self.assertTrue("override quiet" in r)
        self.assertNotRegex(r, r"-Q\s+QUIET")

        r = s.run('--quiet')
        self.assertEqual("True", r)

        s = FileScript([
            "class Default(Command):",
            "    @arg('--quiet', action='store_true', help='override quiet')",
            "    def handle(self, quiet):",
            "        pass",
        ])

        r = s.run('--help')
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

        r = s.run('--quiet=-C')
        self.assertRegex(r, r"^\[CRITICAL]\s+critical\s*$")

        r = s.run('--quiet=-I')
        self.assertEqual("[INFO] info\nout", r)

        r = s.run("-qqqqq")
        self.assertFalse("critical" in r)

        r = s.run("-qqqq")
        self.assertTrue("critical" in r)

        r = s.run("-qqq")
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

        r = s.run("-qq")
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

        r = s.run("-q")
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

        r = s.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="")
        self.assertTrue("debug" in r)
        self.assertTrue("info" in r)
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

        # this won't call QuietAction.__call__()
        r = s.run(CAPTAIN_QUIET_DEFAULT="D")
        self.assertFalse("debug" in r)
        self.assertFalse("verbose" in r)

        r = s.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="D")
        self.assertTrue("debug" in r)
        self.assertTrue("verbose" in r)

        r = s.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="DI")
        self.assertTrue("debug" in r)
        self.assertFalse("info" in r)
        self.assertFalse("out" in r)

    def test_parse_handle_args(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg('--foo', type=int)",
            "    @arg('--bar', type=int)",
            "    def handle(self, foo, bar):",
            "        print('foo: {}, bar: {}'.format(foo, bar))"
        ])

        with self.assertRaises(subprocess.CalledProcessError):
            r = s.run("--foo 1 --bar 2 --che 3")

        r = s.run("--foo 1 --bar 2")
        self.assertTrue("foo: 1, bar: 2" in r)

    def test_parse_custom_action(self):
        s = FileScript([
            "import argparse",
            "",
            "class FooAction(argparse.Action):",
            "    def parse_args(self, parser, arg_strings): return arg_strings",
            "    def get_value(self, value): return int(value) + 1",
            "    def __call__(self, parser, namespace, values, option_string):",
            "        setattr(namespace, self.dest, values)",
            "",
            "class Che(Command):",
            "    @arg('--foo', default='1', action=FooAction)",
            "    @arg('--bar', type=int)",
            "    def handle(self, foo, bar):",
            "        print('foo: {}, bar: {}'.format(foo, bar))",
            "",
            "class Bam(Command):",
            "    def handle(self, **kwargs):",
            "        print('kwargs: {}'.format(kwargs))",
        ])

        r = s.run("che --bar 2")
        self.assertTrue("foo: 2" in r)

        r = s.run("che --foo 1 --bar 2")
        self.assertTrue("foo: 2" in r)

        r = s.run("bam --foo 1 --bar 2")
        self.assertTrue("foo': '1'" in r)

    def test_handle_quiet(self):
        s = FileScript(subcommands=True)
        r = s.run("--help")
        self.assertTrue("--quiet" in r)

        r = s.run("foo --help")
        self.assertTrue("subcommand description")
        self.assertTrue("--quiet" in r)

        r = s.run("--help foo")
        self.assertTrue("--quiet" in r)

    def test_group_simple(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg('--foo', type=int, group='bar')",
            "    @arg('--che', action='store_true', group='bar')",
            "    @arg('--baz', type=int)",
            "    def handle(self, bar, baz):",
            "        print('bar group: {}, baz: {}'.format(bar, baz))",
        ])

        r = s.run("--foo=1 --che --baz=3")
        self.assertTrue("bar group: Namespace(foo=1, che=True), baz: 3" in r)

        r = s.run("--help")
        self.assertTrue("bar:" in r)

    def test_group_multiword(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg('--foo', type=int, group='Bar Bam')",
            "    @arg('--che', action='store_true', group='Bar Bam')",
            "    def handle(self, bar_bam):",
            "        print('bar_bam group: {}'.format(bar_bam))",
            "        print('bar_bam foo: {}'.format(bar_bam.foo))",
            "        print('bar_bam che: {}'.format(bar_bam.che))",
        ])

        r = s.run("--foo=1 --che")
        self.assertTrue("bar_bam group: Namespace(foo=1, che=True)" in r)
        self.assertTrue("bar_bam foo: 1" in r)
        self.assertTrue("bar_bam che: True" in r)

        r = s.run("--help")
        self.assertTrue("Bar Bam:" in r)

    def test_parse_undefined_normalization(self):
        s = FileScript([
            "class Default(Command):",
            "    def handle(self, **kwargs):",
            "        print('kwargs: {}'.format(kwargs))"
        ])

        r = s.run("--foo-bar 1")
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

        parsed = parser.parse_args(["1", "--foo=2"])
        self.assertEqual("2", parsed.foo)
        self.assertEqual("1", parsed.bar)

        parsed = parser.parse_args(["1", "2"])
        self.assertEqual("1", parsed.foo)
        self.assertEqual("2", parsed.bar)

    def test_help_aliases(self):
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

        r = s.run("--help")
        self.assertTrue("foobar" in r)
        self.assertTrue("foo-bar" not in r)

