# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from captain.compat import *

from . import testdata, TestCase, FileScript, ModuleScript
from .parse import (
    UnknownParser,
    EnvironParser,
)


class ArgumentParserTest(TestCase):
    def test_quiet_parsing(self):
        p = FileScript().parser

        p.add_argument('args', nargs="*")
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

        with self.assertRaises(SystemExit):
            args = p.parse_args(['--quiet', 'DWA'])

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

#         r = s.run('--help')
#         return

        r = s.run('--quiet=-WE')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

        r = s.run('')
        self.assertTrue("err" in r)
        self.assertTrue("verbose" in r)
        self.assertTrue("out" in r)

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
            "    @arg('--quiet', '-Q', '-q', action='store_true', help='override quiet')",
            "    def handle(self, quiet):",
            "        self.output.out(quiet)",
        ])
        r = s.run('--help')
        self.assertTrue("override quiet" in r)
        self.assertNotRegexpMatches(r, r"-Q\s+QUIET")

        r = s.run('--quiet')
        self.assertEqual("True", r)

        s = FileScript([
            "class Default(Command):",
            "    @arg('--quiet', action='store_true', help='override quiet')",
            "    def handle(self, quiet):",
            "        pass",
        ])

        r = s.run('--help')
        self.assertRegexpMatches(r, r"--quiet\s+override\s+quiet")
        self.assertRegexpMatches(r, r"-Q\s+_QUIET")

    def test_quiet_logging(self):
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

        r = s.run('--quiet=-C')
        self.assertRegexpMatches(r, r"^\[CRITICAL]\s+critical\s*$")

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

        with self.assertRaises(RuntimeError):
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
        self.assertTrue("foo': ['1']" in r)

    def test_handle_quiet(self):
        s = FileScript(subcommands=True)
        r = s.run("--help")
        self.assertTrue("--quiet" in r)

        r = s.run("foo --help")
        self.assertTrue("subcommand description")
        self.assertTrue("--quiet" in r)

        r = s.run("--help foo")
        self.assertTrue("--quiet" in r)


class UnknownParserTest(TestCase):
    def test_extra_args(self):
        extra_args = [
            "--foo=1",
            "--che",
            '--baz="this=that"',
            "--bar",
            "2",
            "--foo=2",
            "-z",
            "3",
            "4"
        ]

        d = UnknownParser(extra_args)
        self.assertEqual(["1", "2"], d["foo"])
        self.assertEqual(["4"], d["*"])
        self.assertEqual(["2"], d["bar"])
        self.assertEqual(["3"], d["z"])
        self.assertEqual(["this=that"], d["baz"])
        self.assertEqual([True], d["che"])

    def test_binary(self):
        extra_args = [
            b"--foo=1",
            b"--bar=2"
        ]
        d = UnknownParser(extra_args)
        self.assertEqual(["1"], d["foo"])
        self.assertEqual(["2"], d["bar"])


class EnvironParserTest(TestCase):
    def test___init__(self):
        unknown_args = [
            b'--FOO=1',
            b'--BAR=2'
        ]

        e = EnvironParser(unknown_args)
        self.assertEqual("1", e["FOO"])
        self.assertEqual("2", e["BAR"])

        unknown_args = [
            b'--FOO=1',
            b'--FOO=2',
            b'--BAR=3'
        ]

        e = EnvironParser(unknown_args)
        self.assertEqual(["1", "2"], e["FOO"])
        self.assertEqual("3", e["BAR"])

