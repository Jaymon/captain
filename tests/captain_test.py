# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import subprocess
import argparse

from captain import Script, echo
#from captain.client import Captain
from captain.decorators import arg, args
from captain.compat import *
from captain.parse import Parser, ScriptKwarg, CallbackInspect, UnknownParser
from captain import logging, environ

from . import testdata, TestCase, SkipTest, TestScript


# def setUpModule():
#     environ.QUIET_DEFAULT = ""


class EchoTest(TestCase):
    def setUp(self):
        logging.inject_quiet("")

    def test_err(self):
        """https://github.com/Jaymon/captain/issues/44"""
        with testdata.capture() as r:
            echo.err("foo")
        self.assertEqual("foo\n", str(r.stderr))

    def test_profile(self):
        with echo.profile():
            echo.out("profile 1")

        with echo.profile("ran in"):
            echo.out("profile 2")

    def test_prompt_prompt(self):
        class MockInput(object):
            def __call__(self, question):
                self.question = question
                return "yes"

        m = MockInput()
        mecho = testdata.patch(echo, input=m)

        mecho.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("Is this ok? (y|n) ", m.question)

        mecho.prompt("Is this ok?\n", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("Is this ok? (y|n)\n", m.question)

        mecho.prompt("Is this ok")
        self.assertEqual("Is this ok ", m.question)

        mecho.prompt("Is this ok\n")
        self.assertEqual("Is this ok\n", m.question)

    def test_prompt_answer(self):
        class MockInput(object):
            def __init__(self, v):
                self.v = v
            def __call__(self, *args, **kwargs):
                return self.v

        mecho = testdata.patch(echo, input=MockInput("Yes"))
        answer = mecho.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("y", answer)

        mecho = testdata.patch(echo, input=MockInput("no"))
        answer = mecho.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("n", answer)

        mecho = testdata.patch(echo, input=MockInput("n"))
        answer = mecho.prompt("Is this ok?", choices=["y", "n"])
        self.assertEqual("n", answer)

        mecho = testdata.patch(echo, input=MockInput("n"))
        answer = mecho.prompt("Is this ok?", choices={"y": ["yes"], "n": ["no"]})
        self.assertEqual("n", answer)

    def test_increment(self):
        """https://github.com/Jaymon/captain/issues/41"""
        for x in echo.increment(range(5)):
            echo.out(x)

    def test_prefix(self):
        for i, x in enumerate(["a", "b", "c", "d"], 1):
            with echo.prefix("{}. ", i):
                echo.out(testdata.get_words(1))
                with echo.prefix("{}. ", x):
                    echo.out(testdata.get_words(1))
                echo.out(testdata.get_words(1))

    def test_table_1(self):
        one = [1, 3, 5, 7, 9]
        two = [2, 4, 6, 8, 0]
        echo.table(one, two)

        it = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 0))
        echo.table(it)

        echo.table(range(20), range(20))

    def test_table_alignment(self):
        """https://github.com/Jaymon/captain/issues/52"""
        it = (("fooo_type", 0), ("fooooooo_name", "barrrrrr Chee Bazzzz"))
        echo.table(it, headers=["left", "right"])

    def test_table_dict(self):
        d = {
            "foo": [1, 2, 3, 4],
            "bar": [5, 6, 7],
            "che": [8, 9, 10, 11, 12],
        }

        with testdata.capture(loggers=False) as r1:
            echo.table(d)

        with testdata.capture(loggers=False) as r2:
            echo.table_from_dict(d)

        self.assertEqual(r1, r2)

    def test_table_rows(self):
        it = [
            [1, 5, 8],
            [2, 6, 9],
            [3, 7, 10],
            [4, "", 11],
            ["", "", 12],
        ]

        with testdata.capture(loggers=False) as r1:
            echo.table(it, headers=["foo", "bar", "che"])

        with testdata.capture(loggers=False) as r2:
            echo.table_from_rows(*it, headers=["foo", "bar", "che"])

        self.assertEqual(r1, r2)

    def test_table_columns(self):
        it = [[1, 2, 3, 4], [5, 6, 7], [8, 9, 10, 11, 12]]

        with testdata.capture(loggers=False) as r1:
            echo.table(*it, headers=["foo", "bar", "che"])

        with testdata.capture(loggers=False) as r2:
            echo.table_from_columns(*it, headers=["foo", "bar", "che"])

        self.assertEqual(r1, r2)

    def test_table_headers(self):
        it = ((1, 2), (3, 4))

        echo.table(it, headers=["foo", "bar"])
        echo.table(it, headers=["foo", "bar", "che"])

    def test_table_widths(self):
        widths = [5]
        echo.table([(1, 2)], widths=widths)
        echo.table([(3, 4)], widths=widths)
        widths = [0, 5]
        echo.table([(5, 6)], widths=widths)

    def test_table_unicode(self):
        l = [(1, testdata.get_unicode_words()), (2, testdata.get_unicode_words())]
        echo.table(l)

        l = [(1, [testdata.get_unicode_words()]), (2, [testdata.get_unicode_words()])]
        echo.table(l)

    def test_table_none_value(self):
        """We were getting an error in a script when passing d.items() to the table
        method with a None value"""
        d = {
            "foo": None,
            "bar": None,
            "che": None
        }

        echo.table(d.items())

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
        with echo.progress_bar(count, char="#") as pbar:
            for x in range(count):
                pbar.update(x)

        # https://github.com/Jaymon/captain/issues/27
        with echo.progress_bar(count, char="\u2588") as pbar:
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
                "if __name__ == '__main__':",
                "    captain.exit(__name__)",
            ]
        )

        r = script.run()
        self.assertEqual(1, r.count("gotcha"))

    def test_quiet_1(self):
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
                "if __name__ == '__main__':",
                "    exit(__name__)",
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

    def test_quiet_override(self):
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "from captain import echo, exit, arg",
                "",
                "@arg('--quiet', '-Q', '-q', action='store_true', help='override quiet')",
                "def main(quiet):",
                "  echo.out(quiet)",
                "if __name__ == '__main__':",
                "    exit(__name__)",
            ]
        )
        r = script.run('--help')
        self.assertTrue("override quiet" in r)
        self.assertNotRegexpMatches(r, r"-Q\s+QUIET")

        r = script.run('--quiet')
        self.assertEqual("True", r)

        script = TestScript(
            [
                "#!/usr/bin/env python",
                "from captain import echo, exit, arg",
                "",
                "@arg('--quiet', action='store_true', help='override quiet')",
                "def main(quiet):",
                "  pass",
                "if __name__ == '__main__':",
                "    exit(__name__)",
            ]
        )

        r = script.run('--help')
        self.assertRegexpMatches(r, r"--quiet\s+override\s+quiet")
        self.assertRegexpMatches(r, r"-Q\s+QUIET")

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
                "if __name__ == '__main__':",
                "    exit(__name__)",
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
                "if __name__ == '__main__':",
                "    exit(__name__)",
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
                "if __name__ == '__main__':",
                "    exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
        ])
        r = script.run()
        self.assertEqual("", r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main():",
            "  captain.echo.out('foo')",
            "  raise captain.Stop(1, 'stderr stop')",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
        ])
        r = script.run("--quiet=-W", code=1)
        self.assertEqual("stderr stop", r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main():",
            "  captain.echo.err('foo')",
            "  raise captain.Stop(0, 'stdout stop')",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
        ])

        with self.assertRaisesRegexp(RuntimeError, 'returned 1') as e:
            r = script.run()

    def test_init_module(self):
        script = TestScript(
            [
                "import captain",
                "def main():",
                "  '''the description for foo module'''",
                "  print('foo/__init__')",
                "  return 0",
                "if __name__ == '__main__':",
                "    captain.exit(__name__)"
            ],
            'foo/__init__.py'
        )
        c = testdata.ModuleCommand("foo", cwd=script.cwd)
        with self.assertRaises(RuntimeError):
            r = c.run()
        # __init__ worked with old captain, but new captain that doesn't have a
        # cap script runner, it doesn't work
        #self.assertRegexpMatches(r, 'foo/__init__')

        m = testdata.create_modules({
            "foo.__main__": [
                "import captain",
                "def main():",
                "  '''the description for foo module'''",
                "  print('foo/__main__')",
                "  return 0",
                "if __name__ == '__main__':",
                "    captain.exit(__name__)"
            ],
        })
        c2 = testdata.ModuleCommand("foo", cwd=m.path)
        r = c2.run()
        self.assertRegex(r, 'foo/__main__')

        m = testdata.create_modules({
            "foo.bar": [
                "import captain",
                "def main():",
                "  '''the description for foo module'''",
                "  return 0",
                "if __name__ == '__main__':",
                "    captain.exit(__name__)"
            ],
        })
        c3 = testdata.ModuleCommand("foo", cwd=m.path)
        with self.assertRaises(RuntimeError):
            r = c3.run()

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
                    "if __name__ == '__main__':",
                    "    captain.exit(__name__)"
                ]),
                'che.py': "\n".join([
                    "#!/usr/bin/env python",
                    "import captain",
                    "def main(): return 0",
                    "if __name__ == '__main__':",
                    "    captain.exit(__name__)"
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
                    "if __name__ == '__main__':",
                    "    captain.exit(__name__)"
                ]),
                'mod2/__main__.py': "\n".join([
                    "#!/usr/bin/env python",
                    "import captain",
                    "def main():",
                    "  '''the description for mod1'''",
                    "  return 0",
                    "if __name__ == '__main__':",
                    "    captain.exit(__name__)"
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
                    "if __name__ == '__main__':",
                    "    captain.exit(__name__)"
                ]),
            },
            cwd
        )


        #c = Captain(, cwd=self.cwd)
        #c.cmd_prefix = "captain"

        c = testdata.ModuleCommand("captain", cwd=os.getcwd())
        r = c.run(cwd)

        #script.cwd = os.getcwd()
        #script.path = "captain/__main__.py"
        #r = script.run(cwd)

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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
        ])
        r = script.run("--foo=1 --che=oh_yeah awesome")
        self.assertEqual('awesome oh_yeah', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo, bar=0, *args):",
            "  print(args[0])",
            "  return 0",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, *args):",
            "  print(args[0])",
            "  return 0",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, bar=int):",
            "  print('foo')",
            "  return 0",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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


class EntryPointTest(TestCase):
    """A test case that will test all the different ways we can enter into a captain
    script so I can easily test them and make sure they work across changes"""
#     def test_python37_script_direct(self):
#         """https://github.com/Jaymon/transcribe/issues/2"""
#         m = testdata.create_module(contents=[
#             "from captain import exit as console, echo",
#             "",
#             "def main(): echo.out('success')",
#         ])
# 
#         contents = [
#             "#!{}".format(testdata.get_interpreter()),
#             "# -*- coding: utf-8 -*-",
#             "import re",
#             "import sys",
#             "",
#             "sys.path.insert(0, '{}')".format(m.directory),
#             "",
#             "from {} import console".format(m),
#             "",
#             "if __name__ == '__main__':",
#             "    sys.argv[0] = re.sub(r'(-script\\.pyw?|\\.exe)?$', '', sys.argv[0])",
#             "    sys.exit(console())",
#         ]
# 
#         ts = TestScript(contents)
#         r = ts.run()
#         #self.assertTrue(r.endswith("success"))
#         pout.v(r)
#         #s = ts.instance

    def test_python37_script_wrapper(self):
        """https://github.com/Jaymon/transcribe/issues/2"""
        m = testdata.create_module(contents=[
            "from captain import exit, echo",
            "",
            "def main(): echo.out('success')",
            "",
            "def console():",
            "    exit(__name__)",
        ])

        contents = [
            "#!{}".format(testdata.get_interpreter()),
            "# -*- coding: utf-8 -*-",
            "import re",
            "import sys",
            "",
            "sys.path.insert(0, '{}')".format(m.directory),
            "",
            "from {} import console".format(m),
            "",
            "if __name__ == '__main__':",
            "    sys.argv[0] = re.sub(r'(-script\\.pyw?|\\.exe)?$', '', sys.argv[0])",
            "    sys.exit(console())",
        ]

        ts = TestScript(contents)
        r = ts.run()
        self.assertTrue(r.endswith("success"))

#     def test_stack_single_entry_points(self):
#         module_d = testdata.create_modules({
#             "msmcli": "",
#             "msmcli.__main__": [
#                 "from captain import exit as console, echo",
#                 "def main():",
#                 "    echo.out('success')",
#                 "    return 0",
#                 "",
#                 "if __name__ == '__main__':",
#                 "    console()",
#             ],
#         })
# 
#         script = TestScript([
#             "#!/usr/bin/python",
#             "import sys",
#             "sys.path.append('{}')".format(module_d),
#             "from msmcli.__main__ import console",
#             "",
#             "def load_entry_point(*args):",
#             "    return console",
#             "",
#             "import pkg_resources",
#             "class GDFake(object):",
#             "    def __call__(self, *args, **kwargs):",
#             "        return self",
#             "    def get_entry_info(self, *args, **kwargs):",
#             "        class o(object):",
#             "            module_name = 'msmcli.__main__'",
#             "        return o()",
#             "pkg_resources.get_distribution = GDFake()",
#             ""
#             "#from pkg_resources import load_entry_point",
#             "",
#             "if __name__ == '__main__':",
#             "    sys.exit(",
#             "        load_entry_point('msmcli==0.0.1', 'console_scripts', 'msmcli')()",
#             "    )",
#         ])
# 
#         r = script.run()
#         pout.v(r)
#         self.assertTrue("success" in r)

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
                "    exit(__name__)",
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
        self.assertTrue(r.endswith("success"))

    def test_normal_script(self):
        """https://github.com/Jaymon/transcribe/issues/2"""
        contents = [
            "from captain import exit, echo",
            "",
            "def main(): echo.out('success')",
            "",
            "exit(__name__)",
        ]

        ts = TestScript(contents)
        r = ts.run()
        self.assertTrue(r.endswith("success"))

    def test_main_script(self):
        """https://github.com/Jaymon/transcribe/issues/2"""
        contents = [
            "from captain import exit, echo",
            "",
            "def main(): echo.out('success')",
            "",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ]

        ts = TestScript(contents)
        r = ts.run()
        self.assertTrue(r.endswith("success"))


class ScriptTest(TestCase):
    def test_can_run_from_cli(self):
        script_path = TestScript([
            "from captain import exit as ex",
            "def main(): pass",
            "if __name__ == '__main__':",
            "    ex()",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())

        script_path = TestScript([
            "import captain as admiral",
            "def main(): pass",
            "if __name__ == '__main__':",
            "    admiral.exit(__name__)",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())


        script_path = TestScript([
            "from captain import exit",
            "def main(): pass",
            "if __name__ == '__main__':",
            "    exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
        ])
        s = Script(script_path)
        self.assertTrue(s.can_run_from_cli())

    def test_custom_version(self):

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "@captain.decorators.arg('-V', '--version', action='version', version='0.1')",
            "def main(): pass",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
        ])
        r = script.run("--version")
        self.assertTrue("0.1" in r)

    def test_default_version(self):
        script_path = TestScript([
            "import captain",
            "__version__ = '0.1.1'",
            "def main_bar(): return 0",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
        self.assertTrue("{foo,bar}" in r or "{bar,foo}" in r)

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
            "if __name__ == '__main__':",
            "    exit(__name__)",
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
                "if __name__ == '__main__':",
                "    captain.exit(__name__)",
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
                "if __name__ == '__main__':",
                "    captain.exit(__name__)",
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


