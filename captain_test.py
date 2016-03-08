from unittest import TestCase, SkipTest
import os
import subprocess
import argparse

import testdata

from captain import Script, ScriptArg, ScriptKwarg, echo
from captain.client import Captain


class TestScript(object):

    @property
    def instance(self):
        return Script(self)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        script_path = cls(*args, **kwargs)
        return script_path.instance

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

    def run(self, arg_str=''):
        pwd = os.path.dirname(__file__)
        cmd_env = os.environ.copy()
        cmd_env['PYTHONPATH'] = pwd + os.pathsep + cmd_env.get('PYTHONPATH', '')
        c = Captain(self.path, cwd=self.cwd)
        r = ""
        for line in c.run(arg_str, env=cmd_env):
            c.flush(line)
            r += line.strip()
        return r


class EchoTest(TestCase):
    def setUp(self):
        echo.quiet = False

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


class CaptainTest(TestCase):
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
                "  print 'foo/__init__'",
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
                "  print 'foo/__main__'",
                "  return 0",
                "captain.exit()"
            ],
            'foo/__main__.py'
        )

        script.path = 'foo'
        r = script.run()
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
        with self.assertRaises(RuntimeError):
            r = script.run()

    def test_import(self):
        script = TestScript([
            "print '1'",
            "import foo.bar",
            "print '2'",
            "if __name__ == '__main__':",
            "  print '3'",
        ])

        testdata.create_module("foo.bar", "\n".join([
            "import captain",
            "def main():",
            "  '''the description for bar'''",
            "  return 0",
            "captain.exit()"
        ]), tmpdir=script.cwd)

        r = script.run()
        self.assertEqual("123", r)

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
                    "if __name__ == u'__main__': pass"
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
            "  print args[0], kwargs['che']",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 --che=oh_yeah awesome")
        self.assertEqual('awesome oh_yeah', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo, bar=0, *args):",
            "  print args[0]",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, *args):",
            "  print args[0]",
            "  return 0",
            "captain.exit()",
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "import captain",
            "def main(foo=int, bar=int):",
            "  print 'foo'",
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
    def test_arg_in_main(self):
        script_path = TestScript([
            "import captain",
            "@captain.decorators.arg('foo', nargs=1)",
            "def main(foo):",
            "    print foo",
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
            "    print indir",
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

        with self.assertRaises(RuntimeError):
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
            "    print args, kwargs",
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
            "  print args[0]",
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


class ScriptTest(TestCase):
#     def test_description(self):
#         script_path = TestScript([
#             "import captain",
#             "from captain import echo",
#             "__version__ = '0.1'",
#             "def main_foo():",
#             "  '''description for foo'''",
#             "  echo.out('foo out')",
#             "  echo.verbose('foo verbose')",
#             "def main_bar():",
#             "  '''description for bar'''",
#             "  echo.out('bar out')",
#             "  echo.verbose('bar verbose')",
#             "captain.exit()",
#         ])
#         s = Script(script_path)
#         pout.v(s.description)

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
            "  def __call__(self, *args, **kwargs):",
            "    return 0"
        ])
        s = Script(script_path)
        p = s.parser
        self.assertEqual('', p.description)

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

        r = script_path.run("--quiet --verbose foo")
        self.assertEqual("", r)

        with self.assertRaises(RuntimeError):
            r = script_path.run("foo --quiet --verbose")

        r = script_path.run("--verbose foo")
        self.assertTrue("foo verbose" in r)
        self.assertTrue("foo out" in r)

        r = script_path.run("--verbose bar")
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
                for k, v in test_assert.iteritems():
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

