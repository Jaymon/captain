# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
from unittest import TestCase, SkipTest
import os
import subprocess
import argparse

import testdata

from captain import Script, echo
from captain.client import Captain
from captain.decorators import arg, args
from captain.compat import *
from captain.parse import Parser, ScriptKwarg, CallbackInspect
from captain import logging, environ


def setUpModule():
    environ.QUIET_DEFAULT = ""


class TestScript(object):

    @property
    def instance(self):
        return Script(self)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        script_path = cls(*args, **kwargs)
        return script_path.instance

    @property
    def captain(self):
        return Captain(self.path, cwd=self.cwd)

    def __init__(self, body, fname=''):
        self.body = body
        if not isinstance(body, basestring):
            self.body = "\n".join(body)

        self.cwd = testdata.create_dir()

        if not fname:
            fname = "{}/{}.py".format(testdata.get_ascii(5), testdata.get_ascii(5))

        self.path = testdata.create_file(
            fname,
            self.body,
            self.cwd
        )

    def __str__(self):
        return self.path

    def run(self, arg_str='', **kwargs):
        cap = self.captain
        kwargs.setdefault("CAPTAIN_QUIET_DEFAULT", environ.QUIET_DEFAULT)
        return cap.run(arg_str, quiet=False, **kwargs)


class EchoTest(TestCase):
    def setUp(self):
        logging.inject_quiet("")

    def test_table(self):
        one = [1, 3, 5, 7, 9]
        two = [2, 4, 6, 8, 0]
        echo.table(one, two)

        it = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 0))
        echo.table(it)

        echo.table(range(20), range(20))

    def test_no_format(self):
        echo.out("this should not {fail}")

        v = None
        with self.assertRaises(KeyError):
            echo.out("this should {fail}", v)

    def test_nolines(self):
        for x in range(100):
            echo.ch(".")

    def test_progress(self):
        count = 100
        with echo.progress(count) as pbar:
            for x in range(count):
                pbar.update(x)

    def test_progress_bar(self):
        count = 100
        with echo.progress_bar(count) as pbar:
            for x in range(count):
                pbar.update(x)

    def test_quote(self):
        echo.quote("this is the string")

    def test_out_no_args(self):
        echo.out("foo {}".format("bar"))
        echo.out("this does not have any format args")
        echo.out()

    def test_bullets(self):
        lines = [testdata.get_ascii_words(4) for x in range(5)]
        echo.ul(*lines)
        echo.br()
        echo.ol(*lines)

    def test_hr(self):
        echo.out("text before")
        echo.hr()
        echo.out("text after")

    def test_headers(self):
        shorter = "this is the header"
        longer = testdata.get_ascii_words(80)

        echo.h1(shorter)
        echo.br()
        echo.h1(longer)

        echo.br()

        echo.h2(shorter)
        echo.br()
        echo.h2(longer)

        echo.br()

        echo.h3(shorter)
        echo.br()
        echo.h3(longer)

        echo.br()

    def test_non_string(self):
        a = range(5)
        echo.out(a)

    def test_blank_bar(self):
        echo.out("no args, should be one Newline")
        echo.blank()
        echo.bar()

        echo.out("passed in 5")
        echo.blank(5)
        echo.bar('=', 5)

    def test_echo_logging(self):
        """make sure you don't get double echoing when echo is imported before other
        set up logging"""
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import captain",
                "import sys",
                "import logging",
                "import captain",
                "rl = logging.getLogger()",
                "log_handler = logging.StreamHandler(stream=sys.stderr)",
                "log_formatter = logging.Formatter('[%(asctime)s] %(message)s', '%m-%dT%H:%M:%S')",
                "log_handler.setFormatter(log_formatter)",
                "rl.addHandler(log_handler)",
                "from captain import echo",
                "",
                "def main():",
                "  echo.out('gotcha')",
                "  return 0",
                "captain.exit()",
            ]
        )

        r = script.run()
        self.assertEqual(1, r.count("gotcha"))

    def test_quiet(self):
        """make sure you don't get double echoing when echo is imported before other
        set up logging"""
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "from captain import echo, exit",
                "",
                "def main():",
                "  echo.verbose('verbose')",
                "  echo.out('out')",
                "  echo.err('err')",
                "exit(__name__)",
            ]
        )

        r = script.run('--quiet=-WE')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

        r = script.run('')
        self.assertTrue("err" in r)
        self.assertTrue("verbose" in r)
        self.assertTrue("out" in r)

        r = script.run('--quiet=D')
        self.assertTrue("err" in r)
        self.assertFalse("verbose" in r)
        self.assertTrue("out" in r)

        r = script.run('--quiet')
        self.assertFalse("err" in r)
        self.assertFalse("verbose" in r)
        self.assertFalse("out" in r)

    def test_quiet_logging(self):
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import sys",
                "import logging",
                "logging.basicConfig(",
                "  format='[%(levelname)s] %(message)s',",
                "  level=logging.DEBUG, stream=sys.stdout",
                ")",
                "logger = logging.getLogger(__name__)",
                "from captain import echo, exit",
                "",
                "def main():",
                "  logger.debug('debug')",
                "  logger.info('info')",
                "  logger.warning('warning')",
                "  logger.error('error')",
                "  logger.critical('critical')",
                "  echo.verbose('verbose')",
                "  echo.out('out')",
                "  echo.err('err')",
                "exit(__name__)",
            ]
        )

        r = script.run('--quiet=-C')
        self.assertRegexpMatches(r, r"^\[CRITICAL]\s+critical\s*$")

        r = script.run('--quiet=-I')
        self.assertEqual("[INFO] info\nout", r)

    def test_quiet_default(self):
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import sys",
                "import logging",
                "logging.basicConfig(",
                "  format='[%(levelname)s] %(message)s',",
                "  level=logging.DEBUG, stream=sys.stdout",
                ")",
                "logger = logging.getLogger(__name__)",
                "from captain import echo, exit",
                "",
                "def main():",
                "  logger.debug('debug')",
                "  logger.info('info')",
                "  logger.warning('warning')",
                "  logger.error('error')",
                "  logger.critical('critical')",
                "  echo.verbose('verbose')",
                "  echo.out('out')",
                "  echo.err('err')",
                "exit(__name__)",
            ]
        )

        r = script.run(CAPTAIN_QUIET_DEFAULT="D")
        self.assertFalse("debug" in r)
        self.assertFalse("verbose" in r)

        r = script.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="D")
        self.assertTrue("debug" in r)
        self.assertTrue("verbose" in r)

        r = script.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="DI")
        self.assertTrue("debug" in r)
        self.assertFalse("info" in r)
        self.assertFalse("out" in r)

        r = script.run("--quiet=+D", CAPTAIN_QUIET_DEFAULT="")
        self.assertTrue("debug" in r)
        self.assertTrue("info" in r)
        self.assertTrue("warning" in r)
        self.assertTrue("error" in r)
        self.assertTrue("critical" in r)

    def test_ch(self):
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "from captain import echo, exit",
                "",
                "def main():",
                "  for x in range(10):",
                "    echo.ch('.')",
                "exit(__name__)",
            ]
        )

        r = script.run()
        self.assertEqual("..........", r)

        r = script.run("--quiet")
        self.assertEqual("", r)


class CallbackInspectTest(TestCase):
    def test_instance(self):
        class MainClass(object):
            @arg("--foo")
            def __call__(self, **kwargs):
                """the description on __call__"""
                pass

        main_instance = MainClass()
        cbi = CallbackInspect(main_instance)
        self.assertTrue(cbi.is_instance())
        self.assertFalse(cbi.is_class())
        self.assertFalse(cbi.is_function())
        self.assertEqual("the description on __call__", cbi.desc)

        argspec = cbi.argspec
        self.assertEqual("kwargs", argspec[2])

        args = cbi.args
        self.assertEqual(1, len(args))

        iargs = cbi.inherit_args
        self.assertEqual(0, len(iargs))

    def test_function(self):
        @arg("--bar")
        def main_func(**kwargs):
            """the description on function"""
            pass

        cbi = CallbackInspect(main_func)
        self.assertFalse(cbi.is_instance())
        self.assertFalse(cbi.is_class())
        self.assertTrue(cbi.is_function())
        self.assertEqual("the description on function", cbi.desc)

        argspec = cbi.argspec
        self.assertEqual("kwargs", argspec[2])

        args = cbi.args
        self.assertEqual(1, len(args))

        iargs = cbi.inherit_args
        self.assertEqual(0, len(iargs))

    def test_class(self):
        class MainClass(object):
            @arg("--che")
            def __call__(self, **kwargs):
                """the description on __call__"""
                pass

        cbi = CallbackInspect(MainClass)
        self.assertFalse(cbi.is_instance())
        self.assertTrue(cbi.is_class())
        self.assertFalse(cbi.is_function())
        self.assertEqual("the description on __call__", cbi.desc)

        argspec = cbi.argspec
        self.assertEqual("kwargs", argspec[2])

        args = cbi.args
        self.assertEqual(1, len(args))

        iargs = cbi.inherit_args
        self.assertEqual(0, len(iargs))

    def test_method(self):
        class MainClass(object):
            @arg("--foo")
            def __call__(self, **kwargs):
                """the description on __call__"""
                pass

        cbi = CallbackInspect(MainClass.__call__)
        self.assertFalse(cbi.is_instance())
        self.assertFalse(cbi.is_class())
        self.assertTrue(cbi.is_function())
        self.assertEqual("the description on __call__", cbi.desc)

    def test_inheritance(self):
        class MainClass1(object):
            @arg("--foo")
            @arg("--bar")
            def __call__(self, **kwargs): pass

        class MainClass2(object):
            @args(MainClass1)
            @arg("--che")
            def __call__(self, **kwargs): pass

        class MainClass3(object):
            @args(MainClass1.__call__, MainClass2)
            @arg("--baz")
            def __call__(self, **kwargs): pass

        p = Parser(callback=MainClass2())
        hm = p.format_help()
        for k in ["--foo", "--bar", "--che"]:
            self.assertTrue(k in hm)

        p = Parser(callback=MainClass3())
        hm = p.format_help()
        for k in ["--foo", "--bar", "--che", "--baz"]:
            self.assertTrue(k in hm)


class CaptainTest(TestCase):
    def test_stop(self):

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main():",
            "  raise captain.Stop(0)",
            "captain.exit()"
        ])
        r = script.run()
        self.assertEqual("", r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main():",
            "  captain.echo.out('foo')",
            "  raise captain.Stop(1, 'stderr stop')",
            "captain.exit()"
        ])
        r = script.run("--quiet=-W", code=1)
        self.assertEqual("stderr stop", r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main():",
            "  captain.echo.err('foo')",
            "  raise captain.Stop(0, 'stdout stop')",
            "captain.exit()"
        ])
        r = script.run("--quiet=-I")
        self.assertEqual("stdout stop", r)

    def test_raised_exception(self):
        """I want to make sure exception handling is handled correctly"""
        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main():",
            "  raise ValueError('boom_error')",
            "  return 0",
            "captain.exit()"
        ])

        with self.assertRaisesRegexp(RuntimeError, 'returned 1') as e:
            r = script.run()

    def test_init_module(self):
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import captain",
                "def main():",
                "  '''the description for foo module'''",
                "  print('foo/__init__')",
                "  return 0",
                "captain.exit()"
            ],
            'foo/__init__.py'
        )

        script.path = 'foo'
        with self.assertRaises(RuntimeError):
            r = script.run()
        # __init__ worked with old captain, but new captain that doesn't have a
        # cap script runner, it doesn't work
        #self.assertRegexpMatches(r, 'foo/__init__')

        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import captain",
                "def main():",
                "  '''the description for foo module'''",
                "  print('foo/__main__')",
                "  return 0",
                "captain.exit()"
            ],
            'foo/__main__.py'
        )

        script.path = 'foo'
        c = script.captain
        c.script = 'foo'
        r = c.run()
        self.assertRegexpMatches(r, 'foo/__main__')

        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import captain",
                "def main():",
                "  '''the description for foo module'''",
                "  return 0",
                "captain.exit()"
            ],
            'foo/bar.py'
        )

        script.path = 'foo'
        c = script.captain
        c.script = 'foo'
        with self.assertRaises(RuntimeError):
            r = c.run()

    def test_list(self):
        #raise SkipTest("")
        script = TestScript([""])
        cwd = script.cwd
        #cwd = testdata.create_dir()
        testdata.create_files(
            {
                'foo/bar.py': "\n".join([
                    "#!/usr/bin/env python",
                    "import captain",
                    "def main():",
                    "  '''the description for bar'''",
                    "  return 0",
                    "captain.exit()"
                ]),
                'che.py': "\n".join([
                    "#!/usr/bin/env python",
                    "import captain",
                    "def main(): return 0",
                    "captain.exit()"
                ]),
                'bar/boo.py': "\n".join([
                    "def main():",
                    "  '''the description for boo'''",
                    "  return 0",
                ]),
                'bar/baz.py': "\n".join([
                    "#!/usr/bin/env python",
                    "if __name__ == '__main__': pass"
                ]),
                'mod1/__init__.py': "\n".join([
                    "#!/usr/bin/env python",
                    "import captain",
                    "def main():",
                    "  '''the description for mod1'''",
                    "  return 0",
                    "captain.exit()"
                ]),
                'mod2/__main__.py': "\n".join([
                    "#!/usr/bin/env python",
                    "import captain",
                    "def main():",
                    "  '''the description for mod1'''",
                    "  return 0",
                    "captain.exit()"
                ]),
                'mod3/multi.py': "\n".join([
                    "import captain",
                    "def main_multi1():",
                    "  '''the 1 description'''",
                    "  pass",
                    "def main_multi2():",
                    "  '''the 2 description'''",
                    "  pass",
                    "def main_multi3():",
                    "  '''the 3 description'''",
                    "  pass",
                    "captain.exit()"
                ]),
            },
            cwd
        )


        #c = Captain(, cwd=self.cwd)
        #c.cmd_prefix = "captain"

        script.cwd = os.getcwd()
        script.path = "captain/__main__.py"
        r = script.run(cwd)

        self.assertTrue('che.py' in r)
        self.assertTrue('foo/bar.py' in r)
        self.assertFalse('bar/boo.py' in r)
        self.assertFalse('bar/baz.py' in r)

        self.assertTrue('mod1' in r)
        self.assertFalse('__init__' in r)
        self.assertTrue('mod2' in r)
        self.assertFalse('__main__' in r)

        self.assertTrue("multi1" in r)
        self.assertTrue("multi2" in r)
        self.assertTrue("multi3" in r)

    def test_help(self):
        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, bar=0, *args, **kwargs):",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--help")
        self.assertTrue(os.path.basename(script.path) in r)
        self.assertTrue('foo' in r)
        self.assertTrue('bar' in r)
        self.assertTrue('args' in r)

    def test_run_script(self):
        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo, bar=0, *args, **kwargs):",
            "  print('{} {}'.format(args[0], kwargs['che']))",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 --che=oh_yeah awesome")
        self.assertEqual('awesome oh_yeah', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo, bar=0, *args):",
            "  print(args[0])",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, *args):",
            "  print(args[0])",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, bar=int):",
            "  print('foo')",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 --bar=2")
        self.assertEqual('foo', r)

        script = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])
        r = script.run()
        self.assertEqual('', r)
        # now a script with no captain.exit() just returns ""
        #with self.assertRaises(RuntimeError):
        #    script.run()


class ScriptKwargTest(TestCase):
    def test_default(self):
        s = ScriptKwarg('foo')
        s.set_default(True)
        self.assertTrue(s.default)

    def test_names(self):
        s = ScriptKwarg("foo")
        args = ("--foo", "--foo-id", "--foo-email")
        l = [(args, {})]
        s.merge_from_list(l)
        self.assertEqual(set(args), s.parser_args)

    def test_custom_standard_type(self):
        class FooType(str):
            def __new__(cls, d):
                d = "HAPPY" + d
                return super(FooType, cls).__new__(cls, d)

        s = ScriptKwarg("footype")
        s.merge_kwargs({
            "type": FooType
        })

        parser = argparse.ArgumentParser()
        parser.add_argument(*s.parser_args, **s.parser_kwargs)
        args = parser.parse_args(["--footype", "/foo/bar/che"])
        self.assertTrue(args.footype.startswith("HAPPY"))



class ArgTest(TestCase):
    def test_dest(self):
        """https://github.com/Jaymon/captain/issues/40"""
        script_path = TestScript([
            "from captain import arg, exit",
            '@arg("--out", dest="stream", help="this should be in stream variable")',
            "def main(stream, **kwargs):",
            "    print(stream)",
            "exit()",
        ])
        r = script_path.run("--out=stream")
        self.assertEqual("stream", r)

        script_path = TestScript([
            "from captain import arg, exit",
            '@arg("--out", dest="stream", help="this should be in stream variable")',
            "def main(**kwargs):",
            "    print(kwargs['stream'])",
            "exit()",
        ])
        r = script_path.run("--out=stream")
        self.assertEqual("stream", r)

    def test_arg_normalization(self):
        script_path = TestScript([
            "import captain",
            "@captain.decorators.arg('--foo-bar')",
            "def main(**kwargs):",
            "    print(kwargs['foo_bar'])",
            "captain.exit()",
        ])

        r = script_path.run("--foo-bar=1")
        self.assertEqual('1', r)


    def test_args_class___call__(self):
        script_path = TestScript([
            "import captain",
            "from captain.decorators import arg, args",
            "",
            "class BaseMain(object):",
            "    @arg('--foo')",
            "    @arg('--bar')",
            "    def __call__(self, **kwargs): pass",
            "",
            "class MainCommand(BaseMain):",
            "    ",
            "    @args(BaseMain)",
            "    @arg('--che')",
            "    def __call__(self, **kwargs): pass",
            "",
            "main = MainCommand()",
            "captain.exit(__name__)",
        ])

        r = script_path.run("--help")
        for k in ["--foo", "--bar", "--che"]:
            self.assertTrue(k in r)

    def test_arg_in_main(self):
        script_path = TestScript([
            "import captain",
            "@captain.decorators.arg('foo', nargs=1)",
            "def main(foo):",
            "    print(foo)",
            "captain.exit()",
        ])

        with self.assertRaises(RuntimeError):
            script_path.run("")

        r = script_path.run("bar")
        self.assertTrue("bar" in r)

    def test_custom_type(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain.decorators import arg",
            "from captain import echo",
            "",
            "class Directory(str):",
            "    def __new__(cls, d):",
            "        #pout.v(cls)",
            "        #pout.v(Directory)",
            "        #pout.v(cls)",
            "        #pout.v(issubclass(cls, Directory))",
            "        return super(Directory, cls).__new__(cls, d)",
            "",
            "@arg('--dir', '-d', dest='indir', type=Directory)",
            "def main(indir):",
            "    print(indir)",
            "    return 0",
            "captain.exit()",
        ])

        r = script_path.run("--dir=/tmp")
        self.assertTrue("/tmp" in r)

    def test___call___decorator(self):
        script_path = TestScript([
            "from captain import exit",
            "from captain.decorators import arg",
            "from captain import echo",
            "class BahPleaseWork(object):",
            "    @arg('--output-file', default='')",
            "    @arg('--output-dir', default='/tmp')",
            "    @arg('--print-lines', action='store_true')",
            "    @arg('--no-zip-output', action='store_true')",
            "    def __call__(self, output_file, output_dir, print_lines, no_zip_output):",
            "        echo.out('self={}, output_file={}, output_dir={}, print_lines={}, no_zip_output={}',",
            "            self, output_file, output_dir, print_lines, no_zip_output",
            "        )",
            "main = BahPleaseWork()",
            "exit()"
        ])

        s = script_path.instance
        parser = s.parser

        with self.assertRaises(RuntimeError):
            # this should fail because final-dir is not a valid argument
            r = script_path.run("--output-file=foobar --final-dir=/tmp --print-lines")

        s = script_path.instance
        parser = s.parser

        r = script_path.run("")

    def test_help(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "from captain import echo",
            "from captain.decorators import arg ",
            "@arg('--foo', '-f')",
            "@arg('arg', metavar='ARG')",
            "def main(**kargs):",
            "    '''this is the help description'''",
            "    print(args)",
            "    print(kwargs)",
            "    return 0",
        ])
        r = script_path.run('--help')

    def test_decorator(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain.decorators import arg",
            "@arg('--foo', default=True)",
            "@arg('--bar', '-b', default='bar')",
            "@arg('--boom', default='boom')",
            "@arg('a')",
            "def main(foo, bar, che=1, baz=2, *args, **kwargs):",
            "  print(args[0])",
            "  return 0",
            "captain.exit()",
        ])
        s = script_path.instance
        parser = s.parser
        #pout.v(s.arg_info)

        a = "aaaaaaaa"
        r = script_path.run(a)
        self.assertTrue(a in r)

    def test_arg_and_main(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "from captain.decorators import arg",
            '@arg("--foo", "--foo-id", "--foo-email", default="")',
            '@arg("--bar", "--bar-id", default=0, type=int)',
            '@arg("che_keys", nargs="+")',
            "def main(foo, bar, *che_keys):",
            "    return 0",
        ])
        s = script_path.instance
        p = s.parser
        self.assertEqual(0, len(p.arg_info['required']))
        self.assertTrue('foo' in p.arg_info['optional'])
        self.assertTrue('bar' in p.arg_info['optional'])

    def test_issue_1(self):
        """this test makes sure issue 1 is fixed, which is actually very similar to issue 6"""
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain import echo",
            "from captain.decorators import arg",
            "@arg('--push_environment', '--push-environment', type=str, choices=['dev', 'prod'])",
            "def main(**kwargs):",
            "    echo.out(kwargs)",
            "    return 0",
            "captain.exit()",
        ])
        s = script_path.instance
        parser = s.parser
        with self.assertRaises(RuntimeError):
            r = script_path.run('')

    def test_issue_3(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "from captain import echo",
            "from captain.decorators import arg",
            "def main():",
            "    echo.out('hello world')",
        ])
        r = script_path.run('--quiet')
        self.assertEqual("", r)

    def test_issue_5(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain import echo",
            "from captain.decorators import arg",
            '@arg("--foo", type=int, dest="max_foo", default=5)',
            "def main(max_foo):",
            "    echo.out(max_foo)",
            "captain.exit()"
        ])
        r = script_path.run('')
        self.assertEqual("5", r)

    def test_issue_6(self):
        # https://github.com/firstopinion/captain/issues/6
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain.decorators import arg",
            "from captain import echo",
            '@arg("--count")',
            "def main(count):",
            "    echo.out('foo')",
            "    return 0",
            "captain.exit()"
        ])
        with self.assertRaises(RuntimeError):
            r = script_path.run('')


    def test_issue_7(self):
        # https://github.com/firstopinion/captain/issues/7
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain.decorators import arg",
            '@arg("--count", type=int, dest="max_count")',
            '@arg("--recv-timeout", type=int, dest="recv_timeout")',
            '@arg("--unsync-count", type=int, dest="max_unsync_count", default=5)',
            "def main(max_count, recv_timeout, max_unsync_count=5):",
            "    return 0",
            "captain.exit()"
        ])
        s = script_path.instance

        dests = set(["help", "max_count", "recv_timeout", "max_unsync_count", "quiet", "verbose"])
        parser = s.parser
        for a in parser._actions:
            self.assertTrue(a.dest in dests)

        #pout.v(parser)
        #parser.print_help()
        #pout.v(s.arg_info)

    def test_failing_arg_parse(self):
        """one of our internal tests started failing on a setup similar to below, it
        was failing because it wasn't passing in --at even though --at has a default
        value"""
        script_path = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "from captain.decorators import arg",
            "from captain import echo",
            "@arg('--a_t', '--a-t', default=['e', 'a'], type=str, action='append')",
            "@arg('--p_e', '--p-e', type=str, choices=['d', 'p'])",
            "def main(a_t, p_e):",
            "    echo.out(a_t)",
            "    echo.out(p_e)",
            "    return 0",
            "captain.exit()",
        ])
        r = script_path.run('--p-e=d')
        self.assertTrue("['e', 'a']" in r)


class ExitTest(TestCase):
    """Various tests to make sure the exit() method is working as expected"""
    def test_submodule_main(self):
        script = TestScript([
            "from __future__ import print_function",
            "from captain import exit",
            "from che import main_foo, main_bar",
            #"from che import main_bar",
            "if __name__ == '__main__':",
            "  exit(__name__)",
        ])

        modpath = testdata.create_module("che", [
            "from __future__ import print_function",
            "def main_foo(): print('foo ran')",
            "def main_bar(): print('bar ran')",
        ], tmpdir=script.cwd)

        r = script.run("foo")
        self.assertTrue("foo ran" in r)

        r = script.run("bar")
        self.assertTrue("bar ran" in r)

    def test_stack_import(self):
        script = TestScript([
            "from __future__ import print_function",
            #"print('foo 1', end='')",
            "print('success 1')",
            "import foo.bar",
            "print('success 2')",
            "if __name__ == '__main__':",
            "  print('success 3')",
        ])

        testdata.create_module("foo.bar", "\n".join([
            "import captain",
            "def main():",
            "  '''the description for bar'''",
            "  return 0",
            #"if __name__ == '__main__':",
            #"  captain.exit()"
            "captain.exit()"
        ]), tmpdir=script.cwd)

        r = script.run()
        for x in range(1, 4):
            self.assertTrue("success {}".format(x) in r)

    def test_stack_single_script(self):
        script = TestScript([
            "from captain import exit, echo",
            "def main():",
            "    echo.out('success')",
            "    return 0",
            "",
            "if __name__ == '__main__':",
            "    exit()",
        ])
        r = script.run()
        self.assertTrue("success" in r)

    def test_stack_multi_script(self):
        script = TestScript([
            "from captain import exit, echo",
            "def main():",
            "    echo.out('success')",
            "    return 0",
            "",
            "def console():",
            "    exit()",
            "",
            "if __name__ == '__main__':",
            "    console()",
        ])
        r = script.run()
        self.assertTrue("success" in r)

    def test_stack_single_entry_points(self):
        module_d = testdata.create_modules({
            "msmcli": "",
            "msmcli.__main__": [
                "from captain import exit as console, echo",
                "def main():",
                "    echo.out('success')",
                "    return 0",
                "",
                "if __name__ == '__main__':",
                "    console()",
            ],
        })

        script = TestScript([
            "#!/usr/bin/python",
            "import sys",
            "sys.path.append('{}')".format(module_d),
            "from msmcli.__main__ import console",
            "",
            "def load_entry_point(*args):",
            "    return console",
            "",
            "import pkg_resources",
            "class GDFake(object):",
            "    def __call__(self, *args, **kwargs):",
            "        return self",
            "    def get_entry_info(self, *args, **kwargs):",
            "        class o(object):",
            "            module_name = 'msmcli.__main__'",
            "        return o()",
            "pkg_resources.get_distribution = GDFake()",
            ""
            "#from pkg_resources import load_entry_point",
            "",
            "if __name__ == '__main__':",
            "    sys.exit(",
            "        load_entry_point('stockton==0.0.1', 'console_scripts', 'stockton')()",
            "    )",
        ])

        r = script.run()
        self.assertTrue("success" in r)

    def test_stack_multi_entry_points(self):
        """there was a bug in captain where multiple levels of calls would cause
        captain.exit to not pick up that it is a captain script, this only happened
        from an entry_point script installed with setup.py"""
        module_d = testdata.create_modules({
            "msmcli": "",
            "msmcli.__main__": [
                "from captain import exit, echo",
                "def main():",
                "    echo.out('success')",
                "    return 0",
                "",
                "def console():", # and console calls captain.exit, this is the multi
                "    exit()",
                "",
                "if __name__ == '__main__':",
                "    console()", # notice main calls console
            ],
        })

        script = TestScript([
            "#!/usr/bin/python",
            "import sys",
            "sys.path.append('{}')".format(module_d),
            "from msmcli.__main__ import console",
            "",
            "def load_entry_point(*args):",
            "    return console",
            "",
            "import pkg_resources",
            "class GDFake(object):",
            "    def __call__(self, *args, **kwargs):",
            "        return self",
            "    def get_entry_info(self, *args, **kwargs):",
            "        class o(object):",
            "            module_name = 'msmcli.__main__'",
            "        return o()",
            "pkg_resources.get_distribution = GDFake()",
            ""
            "#from pkg_resources import load_entry_point",
            "",
            "if __name__ == '__main__':",
            "    sys.exit(",
            "        load_entry_point('stockton==0.0.1', 'console_scripts', 'stockton')()",
            "    )",
        ])

        r = script.run()
        self.assertTrue("success" in r)


class ScriptTest(TestCase):
    def test_can_run_from_cli(self):
        script_path = TestScript([
            "from captain import exit as ex",
            "def main(): pass",
            "ex()",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())

        script_path = TestScript([
            "import captain as admiral",
            "def main(): pass",
            "admiral.exit()",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())


        script_path = TestScript([
            "from captain import exit",
            "def main(): pass",
            "exit()",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())

        script_path = TestScript([
            "def main(): pass",
        ])
        s = Script(script_path)
        self.assertFalse(s.can_run_from_cli())

        script_path = TestScript([
            "import captain",
            "def main(): pass",
        ])
        s = Script(script_path)
        self.assertFalse(s.can_run_from_cli())

        script_path = TestScript([
            "import captain",
            "def main(): pass",
            "captain.exit()",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())

    def test_custom_version(self):

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "@captain.decorators.arg('-V', '--version', action='version', version='0.1')",
            "def main(): pass",
            "captain.exit()",
        ])
        r = script.run("--version")
        self.assertTrue("0.1" in r)

    def test_default_version(self):
        script_path = TestScript([
            "import captain",
            "__version__ = '0.1.1'",
            "def main_bar(): return 0",
            "captain.exit()",
        ])
        r = script_path.run("-V")
        self.assertTrue("0.1.1" in r)

    def test_parser_inherit(self):
        script_path = TestScript([
            "import captain",
            "from captain.decorators import arg, args",
            "@arg('--one', default=True)",
            "@arg('--two', default=True)",
            "def main_foo(*args, **kwargs): return 0",
            "",
            "@args(main_foo)",
            "@arg('--three', default=True)",
            "def main_bar(*args, **kwargs): return 0",
            "captain.exit()",
        ])
        r = script_path.run("bar --help")
        self.assertTrue("--one" in r)
        self.assertTrue("--two" in r)
        self.assertTrue("--three" in r)

    def test_parser(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "from captain.decorators import arg",
            "class FooBar(object):",
            "  @arg('--test', default=False)",
            "  def __call__(self, *args, **kwargs):",
            "    '''this would be the description'''",
            "    return 0",
            "main = FooBar()"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual("this would be the description", p.description)
        self.assertTrue("--test" in p._option_string_actions)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(foo, bar, che=1, baz=2, *args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)
        p = s.parser
        #pout.v(p._option_string_actions.keys())
        for k in ["--foo", "--bar", "--che", "--baz"]:
            self.assertTrue(k in p._option_string_actions)

    def test_parse_main_class(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "class main(object):",
            "  def __call__(self, *args, **kwargs):",
            #"    ''''''", # py3.5 does inheritance on doc strings unless overridden
            "    return 0"
        ])
        s = Script(script_path)
        p = s.parser

        script_path = TestScript([
            "#!/usr/bin/env python",
            "class FooBar(object):",
            "  def __call__(self, *args, **kwargs):",
            "    '''this would be the description'''",
            "    return 0",
            "main = FooBar()"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual('this would be the description', p.description)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "class FooBar(object):",
            "  def __call__(self, *args, **kwargs):",
            "    '''this would be the description'''",
            "    return 0",
            "main = FooBar()"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual('this would be the description', p.description)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "class main(object):",
            "  '''class description'''",
            "  def __call__(self, *args, **kwargs):",
            "    return 0"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual('class description', p.description)

    def test_parse_simple(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual('', p.description)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  '''this is the description'''",
            "  return 0"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual('this is the description', p.description)

    def test_parse_multi_main(self):
        script_path = TestScript([
            "def main_foo(): return 0",
            "def main_bar(): return 0",
            "def main_che(): return 0",
            "def main(): return 0"
        ])
        s = Script(script_path)
        self.assertEqual(4, len(s.callbacks))

    def test_inheritance_args_passing(self):

        script_path = TestScript([
            "import captain",
            "from captain import echo",
            "from captain.decorators import arg, args",
            "",
            "@arg('--foo', type=int, choices=[1, 2])",
            "def main_one(): pass",
            "",
            "@args(main_one)",
            "def main_two(foo):",
            "  echo.out(foo)",
            "",
            "@args(main_one)",
            "def main_three(foo=[4,5]):",
            "  echo.out(foo)",
            "",
            "@args(main_one)",
            "@arg('--foo', type=int, choices=[5, 6])",
            "def main_four(foo):",
            "  echo.out(foo)",
            "",
            "captain.exit()",
        ])

        with self.assertRaises(RuntimeError):
            r = script_path.run("two --foo=4")

        r = script_path.run("two --foo=2")
        self.assertEqual("2", r)

        with self.assertRaises(RuntimeError):
            r = script_path.run("three --foo=2")

        r = script_path.run("three --foo=4")
        self.assertEqual("4", r)

        with self.assertRaises(RuntimeError):
            r = script_path.run("four --foo=2")

        r = script_path.run("four --foo=6")
        self.assertEqual("6", r)


        script_path = TestScript([
            "import captain",
            "from captain import echo",
            "from captain.decorators import arg, args",
            "",
            "@arg('--foo', type=int, choices=[1, 2])",
            "def main_one(): pass",
            "",
            "@arg('--foo', type=int, choices=[3, 4])",
            "@arg('--bar', action='store_true')",
            "def main_two(foo, bar): pass",
            "",
            "@args(main_one, main_two)",
            "def main_three(foo, bar):",
            "  echo.out(foo)",
            "  echo.out(bar)",
            "",
            "captain.exit()",
        ])

        r = script_path.run("three --help")
        self.assertTrue("{3,4}" in r)
        self.assertTrue("--bar" in r)

    def test_run_multi_main(self):
        script_path = TestScript([
            "import captain",
            "from captain import echo",
            "__version__ = '0.1'",
            "def main_foo():",
            "  '''description for foo'''",
            "  echo.out('foo out')",
            "  echo.verbose('foo verbose')",
            "def main_bar():",
            "  '''description for bar'''",
            "  echo.out('bar out')",
            "  echo.verbose('bar verbose')",
            "captain.exit()",
        ])

        r = script_path.run("--quiet foo")
        self.assertEqual("", r)

        with self.assertRaises(RuntimeError):
            r = script_path.run("foo --quiet")

        r = script_path.run("foo")
        self.assertTrue("foo verbose" in r)
        self.assertTrue("foo out" in r)

        r = script_path.run("bar")
        self.assertTrue("bar verbose" in r)
        self.assertTrue("bar out" in r)

        r = script_path.run("--help")
        self.assertTrue("{foo,bar}" in r)

        with self.assertRaises(RuntimeError):
            r = script_path.run()

    def test_multi_main_underscores(self):
        script_path = TestScript([
            "from captain import echo",
            "def main_foo_bar():",
            #"  echo.out('foo_bar')",
            "  return 5",
            "def main_che_bar_baz_foo():",
            #"  echo.out('che')",
            "  return 6",
        ])
        s = Script(script_path)

        self.assertTrue("foo_bar" in s.subcommands)

        r = s.run(["foo-bar"])
        self.assertEqual(5, r)

        #r = s.run(["foo_bar"])
        #self.assertEqual(5, r)

        #r = s.run(["che_bar_baz_foo"])
        #self.assertEqual(6, r)

        r = s.run(["che-bar-baz-foo"])
        self.assertEqual(6, r)

    def test_argerror(self):
        script_path = TestScript([
            "from captain import echo, exit, ArgError",
            "def main(foo=0, bar=0):",
            "  if not foo and not bar:",
            "    raise ArgError('either foo or bar is needed')",
            "exit()",
        ])
        s = Script(script_path)
        r = s.run([])
        self.assertEqual(2, r)

        r = s.run(["--bar=5"])
        self.assertEqual(0, r)


    def test_scripts(self):
        with self.assertRaises(IOError):
            s = Script("this/is/a/bogus/path")

        script_path = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        s = Script(script_path)

#     def test_is_cli(self):
#         tests = [
#             [True, [
#                 "#!/usr/bin/env python",
#                 "from datetime import datetime as main",
#             ]],
#             [False, [
#                 "#!/usr/bin/env python",
#                 "",
#                 "# another python comment"
#             ]],
#             [True, [
#                 "#!/usr/bin/env python",
#                 "def foo(*args, **kwargs):",
#                 "  return 0",
#                 "main = foo",
#             ]],
#             [True, [
#                 "#!/usr/bin/env python",
#                 "class Foo(object):",
#                 "  def __call__(self, *args, **kwargs):",
#                 "    return 0",
#                 "",
#                 "main = Foo()",
#             ]],
#             [False, [
#                 "def main(*args, **kwargs):",
#                 "  return 0"
#             ]],
#             [True, [
#                 "#!/usr/bin/env python",
#                 "def main(*args, **kwargs):",
#                 "  return 0"
#             ]],
#         ]
# 
#         for expected, script_lines in tests:
#             script_path = TestScript(script_lines)
#             s = Script(script_path)
#             self.assertEqual(expected, s.is_cli())

    def test_parse_bad(self):
        """makes sure bad input is caught in parsing"""
        tests = [
            ("foo=int", ''),
            ("foo=[int]", ''),
            ("foo=[1, 2]", '--foo=3'),
        ]

        for test_in, test_out in tests:
            s = TestScript([
                "#!/usr/bin/env python",
                "import captain",
                "def main({}):".format(test_in),
                "  return 0",
                "captain.exit()",
            ])

            with self.assertRaises(RuntimeError):
                s.run(test_out)

    def test_parse_good(self):
        tests = [
            ("foo=[1, 2]", '--foo=2', dict(foo=2)),
            (
                "count=1, dry_run=False, matches_per=5, match_all=False, testing=False",
                '--match-all --testing',
                dict(count=1, dry_run=False, matches_per=5, match_all=True, testing=True)
            ),
            ("foo, bar=0, *args, **kwargs", "--foo=1 --che=oh_yeah awesome", dict(foo='1', bar=0)),
            ("foo=baboom", '--foo=5', dict(foo=5)),
            ("foo=int", '--foo=5', dict(foo=5)),
            ("foo=1.0", '--foo=5.0', dict(foo=5.0)),
            ("foo=set()", '--foo=5', dict(foo=['5'])),
            ("foo=set([1, 2])", '--foo=1', dict(foo=1)),
            ("*args", '1 2', dict(args=['1', '2'])),
            ("foo=[int]", '--foo=5 --foo=6', dict(foo=[5, 6])),
            ("foo=[]", '--foo=1 --foo=2', dict(foo=['1', '2'])),
            ("foo=True", '--foo', dict(foo=False)),
            ("foo=False", '--foo', dict(foo=True)),
            ("foo=False, bar=0", '--bar=10', dict(foo=False, bar=10)),
            ("foo=0, bar=''", '--foo=10 --bar=happy', dict(foo=10, bar='happy')),
        ]

        for test_in, test_out, test_assert in tests:
            script_path = TestScript([
                "#!/usr/bin/env python",
                "import captain",
                "def baboom(v): return int(v)",
                "",
                "def main({}):".format(test_in),
                "  return 0",
                "captain.exit()",
            ])

            s = Script(script_path)
            if isinstance(test_assert, type) and issubclass(test_assert, Exception):
                with self.assertRaises(test_assert):
                    parser = s.parse()

            else:
                parser = s.parser
                args, _ = parser.parse_known_args(test_out.split())
                for k, v in test_assert.items():
                    self.assertEqual(v, getattr(args, k))

        # test whether parser knows it shouldn't fail on unknown args
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(**kwargs): return 0"
        ])

        s = Script(script_path)
        self.assertTrue(s.parser.unknown_args)


        # make sure docblock works as description
        desc = 'this is the docblock'
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(**kwargs):",
            "  '''{}'''".format(desc),
            "  pass"
        ])

        s = Script(script_path)
        self.assertEqual(desc, s.parser.description)


class ParserTest(TestCase):
    def test_quiet(self):
        p = Parser(module=self)
        p.add_argument('args', nargs="*")
        #rquiet = p._option_string_actions["--quiet"].OPTIONS
        rargs = ["arg1", "arg2"]

        args = p.parse_args(['-qqq', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("EC", args.quiet)

        args = p.parse_args(['-q', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("IWEC", args.quiet)

        args = p.parse_args(['--quiet', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIWEC", args.quiet)

        args = p.parse_args(['--quiet=DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", args.quiet)

        args = p.parse_args(['--quiet', 'DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", args.quiet)

        args = p.parse_args(['-Q', 'DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", args.quiet)

        args = p.parse_args(['--quiet=-EC', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("DIW"), set(args.quiet))

        args = p.parse_args(['-Q=-C', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("DIWE"), set(args.quiet))

        args = p.parse_args(['--quiet', '-DW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("IEC"), set(args.quiet))

        args = p.parse_args(['--quiet', 'DWarg', 'arg1', 'arg2'])
        self.assertEqual(["DWarg"] + rargs, args.args)
        self.assertEqual("DIWEC", args.quiet)

        p = Parser(module=self)

        args = p.parse_args(['--quiet'])
        self.assertEqual("DIWEC", args.quiet)

        args = p.parse_args(['--quiet', 'DWI'])
        self.assertEqual("DWI", args.quiet)

        with self.assertRaises(SystemExit):
            args = p.parse_args(['--quiet', 'DWA'])
            self.assertEqual("DWI", args.quiet)

        p = Parser(module=self)
        p.add_argument('-D', action="store_true")

        args = p.parse_args(['--quiet', '-D'])
        self.assertEqual("DIWEC", args.quiet)
        self.assertTrue(args.D)

