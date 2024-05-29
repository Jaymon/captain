# -*- coding: utf-8 -*-

from captain.compat import *
from captain.logging import QuietFilter
from captain.parse import Router
from captain.call import Command

from . import testdata, TestCase, FileScript, ModuleScript




class RouterTest(TestCase):

    def test_default_only(self):
        p = self.create_module([
            "from captain import Command",
            "",
            "class Default(Command):",
            "    def handle(self):",
            "        self.output.out('default')",
        ])

        r = Router(command_prefixes=[p])

        pout.v(r.parser)


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

        pout.v(p)

        r = Router(Command, [], paths=[p])






class ArgumentParserTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        # after this class is done testing the quiet functionality reset logging
        QuietFilter.reset()

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
        self.assertRegexpMatches(r, r"-Q\s+<QUIET")

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
        self.assertTrue("bar group: {'foo': 1, 'che': True}, baz: 3" in r)

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
        self.assertTrue("bar_bam group: {'foo': 1, 'che': True}" in r)
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

