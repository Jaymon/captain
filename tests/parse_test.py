# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from captain.parse import Parser, ScriptKwarg, CallbackInspect, UnknownParser

from . import testdata, TestCase, SkipTest, TestScript


class ArgTest(TestCase):
#     def test_inheritance(self):
#         """https://github.com/Jaymon/captain/issues/29"""
#         script_path = TestScript([
#             "from captain import arg, args, exit",
#             "",
#             "class Foo(int): pass",
#             "@arg('--foo', type=Foo)",
#             "def main_one(foo): pass",
#             "",
#             "@args(main_one)",
#             "@arg('--foo', default='')",
#             "def main_two(**kwargs): print(type(kwargs['foo']))",
#             "exit()",
#         ])
#         r = script_path.run("two --foo=2")

    def test_arg_length(self):
        """https://github.com/Jaymon/captain/issues/49"""
        script_path = TestScript([
            "from captain import arg, exit",
            '@arg("--ts", type=int)',
            "def main(ts):",
            "    print(ts)",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ])
        r = script_path.run("--ts=1")
        self.assertEqual("1", r)

        script_path = TestScript([
            "from captain import arg, exit",
            '@arg("--ts", type=int)',
            '@arg("--fb", type=int)',
            "def main(ts, fb):",
            "    print(ts)",
            "    print(fb)",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ])
        r = script_path.run("--ts=1 --fb=3")
        self.assertEqual("1\n3", r)

    def test_dest(self):
        """https://github.com/Jaymon/captain/issues/40"""
        script_path = TestScript([
            "from captain import arg, exit",
            '@arg("--out", dest="stream", help="this should be in stream variable")',
            "def main(stream, **kwargs):",
            "    print(stream)",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ])
        r = script_path.run("--out=stream")
        self.assertEqual("stream", r)

        script_path = TestScript([
            "from captain import arg, exit",
            '@arg("--out", dest="stream", help="this should be in stream variable")',
            "def main(**kwargs):",
            "    print(kwargs['stream'])",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ])
        r = script_path.run("--out=stream")
        self.assertEqual("stream", r)

    def test_arg_normalization(self):
        script_path = TestScript([
            "import captain",
            "@captain.decorators.arg('--foo-bar')",
            "def main(**kwargs):",
            "    print(kwargs['foo_bar'])",
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            #"exit()"
            "if __name__ == '__main__':",
            "    exit(__name__)"
        ])

        s = script_path.instance
        parser = s.parser

        with self.assertRaises(RuntimeError):
            # this should fail because final-dir is not a valid argument
            r = script_path.run("--output-file=foobar --final-dir=/tmp --print-lines")

        s = script_path.instance
        parser = s.parser

        r = script_path.run("")

    def test_help_1(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "from captain import echo, exit, arg",
            "@arg('--foo', '-f')",
            "@arg('arg', metavar='ARG')",
            "def main(**kargs):",
            "    '''this is the help description'''",
            "    print(args)",
            "    print(kwargs)",
            "    return 0",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ])
        r = script_path.run('--help')

    def test_help_2(self):
        script_path = TestScript([
            "from captain import exit",
            "def main():",
            "    '''line 1",
            "",
            "    line 3'''",
            "    return 0",
            "if __name__ == '__main__':",
            "    exit(__name__)",
        ])
        r = script_path.run('--help')
        self.assertTrue("line 1\n\nline 3" in r)

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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
        ])
        s = script_path.instance

        dests = set(["help", "max_count", "recv_timeout", "max_unsync_count", "quiet_inject", "verbose"])
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)",
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
            "    exit(__name__)",
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
            "if __name__ == '__main__':",
            "    captain.exit(__name__)"
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
            "    exit(__name__)",
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
            "    exit(__name__)",
            "",
            "if __name__ == '__main__':",
            "    console()",
        ])
        r = script.run()
        self.assertTrue("success" in r)

    def test_exit_aliases(self):
        for n in ["exit", "Captain", "console", "cli"]:
            script = TestScript([
                "from captain import {}".format(n),
                "def main(): pass",
                "if __name__ == '__main__':",
                "    {}()".format(n),
            ])
            r = script.instance
            self.assertTrue(r.can_run_from_cli())

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


class ParserTest(TestCase):
    def test_subcommand_kwargs(self):
        s = TestScript([
            "@arg('names', metavar='NAME', nargs='?', default='bar')",
            "def main_foo(names, **kwargs):",
            "    pout.v(kwargs, names)",
            "    return 0",
        ])
        s.run("foo --che=1 baz=2")

    def test_quiet(self):
        p = Parser(module=self)
        p.add_argument('args', nargs="*")
        #rquiet = p._option_string_actions["--quiet"].OPTIONS
        rargs = ["arg1", "arg2"]

        args = p.parse_args(['-qqq', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("EC", args.quiet_inject)

        args = p.parse_args(['-q', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("IWEC", args.quiet_inject)

        args = p.parse_args(['--quiet', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIWEC", args.quiet_inject)

        args = p.parse_args(['--quiet=DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", args.quiet_inject)

        args = p.parse_args(['--quiet', 'DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", args.quiet_inject)

        args = p.parse_args(['-Q', 'DIW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual("DIW", args.quiet_inject)

        args = p.parse_args(['--quiet=-EC', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("DIW"), set(args.quiet_inject))

        args = p.parse_args(['-Q=-C', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("DIWE"), set(args.quiet_inject))

        args = p.parse_args(['--quiet', '-DW', 'arg1', 'arg2'])
        self.assertEqual(rargs, args.args)
        self.assertEqual(set("IEC"), set(args.quiet_inject))

        args = p.parse_args(['--quiet', 'DWarg', 'arg1', 'arg2'])
        self.assertEqual(["DWarg"] + rargs, args.args)
        self.assertEqual("DIWEC", args.quiet_inject)

        p = Parser(module=self)

        args = p.parse_args(['--quiet'])
        self.assertEqual("DIWEC", args.quiet_inject)

        args = p.parse_args(['--quiet', 'DWI'])
        self.assertEqual("DWI", args.quiet_inject)

        with self.assertRaises(SystemExit):
            args = p.parse_args(['--quiet', 'DWA'])
            self.assertEqual("DWI", args.quiet_inject)

        p = Parser(module=self)
        p.add_argument('-D', action="store_true")

        args = p.parse_args(['--quiet', '-D'])
        self.assertEqual("DIWEC", args.quiet_inject)
        self.assertTrue(args.D)


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

