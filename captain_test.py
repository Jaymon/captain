from unittest import TestCase
import os
import subprocess

import testdata

from captain import Script

class TestScript(object):

    def __init__(self, body):
        self.body = "\n".join(body)
        self.cwd = testdata.create_dir()
        self.path = testdata.create_file(
            "{}/{}.py".format(testdata.get_ascii(5), testdata.get_ascii(5)),
            self.body,
            self.cwd
        )

    def __str__(self):
        return self.path

    def run(self, arg_str=''):
        pwd = os.path.dirname(__file__)
        cmd_env = os.environ.copy()
        cmd_env['PYTHONPATH'] = pwd + os.pathsep + cmd_env.get('PYTHONPATH', '')

        cmd = "python -m captain {} {}".format(self.path, arg_str)

        r = ''
        try:
            r = subprocess.check_output(
                cmd,
                shell=True,
                stderr=subprocess.STDOUT,
                cwd=self.cwd,
                env=cmd_env
            ).rstrip()

        except subprocess.CalledProcessError, e:
            raise RuntimeError("cmd returned {} with output: {}".format(e.returncode, e.output))

        return r


class CaptainTest(TestCase):

    def test_list(self):
        script = TestScript([""])
        cwd = script.cwd
        testdata.create_files(
            {
                'foo/bar.py': "\n".join([
                    "#!/usr/bin/env python",
                    "def main():",
                    "  '''the description for bar'''",
                    "  return 0"
                ]),
                'che.py': "\n".join([
                    "#!/usr/bin/env python",
                    "def main(): return 0"
                ]),
                'bar/boo.py': "\n".join([
                    "def main():",
                    "  '''the description for boo'''",
                    "  return 0"
                ]),
                'bar/baz.py': "\n".join([
                    "#!/usr/bin/env python",
                    "if __name__ == u'__main__': pass"
                ]),
            },
            cwd
        )

        script.path = ''
        r = script.run()
        self.assertTrue('che.py' in r)
        self.assertTrue('foo/bar.py' in r)
        self.assertFalse('bar/boo.py' in r)
        self.assertFalse('bar/baz.py' in r)

    def test_help(self):
        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo=int, bar=0, *args, **kwargs):",
            "  return 0"
        ])
        r = script.run("--help")
        self.assertTrue(os.path.basename(script.path) in r)
        self.assertTrue('foo' in r)
        self.assertTrue('bar' in r)
        self.assertTrue('args' in r)


    def test_run_script(self):
        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo, bar=0, *args, **kwargs):",
            "  print args[0], kwargs['che']",
            "  return 0"
        ])
        r = script.run("--foo=1 --che=oh_yeah awesome")
        self.assertEqual('awesome oh_yeah', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo, bar=0, *args):",
            "  print args[0]",
            "  return 0"
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo=int, *args):",
            "  print args[0]",
            "  return 0"
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo=int, bar=int):",
            "  print 'foo'",
            "  return 0"
        ])
        r = script.run("--foo=1 --bar=2")
        self.assertEqual('foo', r)

        script = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        with self.assertRaises(RuntimeError):
            script.run()

class ScriptTest(TestCase):
    def test_scripts(self):
        with self.assertRaises(IOError):
            s = Script("this/is/a/bogus/path")

        script_path = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        s = Script(script_path)

    def test_is_cli(self):
        script_path = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        s = Script(script_path)
        self.assertFalse(s.is_cli())

        script_path = TestScript([
            "#!/usr/bin/env python",
            "",
            "# another python comment"
        ])

        s = Script(script_path)
        self.assertFalse(s.is_cli())

        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)
        self.assertTrue(s.is_cli())

    def test_parse(self):

        tests = [
            ("foo, bar=0, *args, **kwargs", "--foo=1 --che=oh_yeah awesome", dict(foo='1', bar=0)),
            ("foo=Baboom", '--foo=5', ValueError),
            ("foo=int", '--foo=5', dict(foo=5)),
            ("foo=1.0", '--foo=5.0', dict(foo=5.0)),
            ("foo=set()", '--foo=5', ValueError),
            #("foo=set(1, 2)", '--foo=1', dict(foo=1)), # this should set the choice argument
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
                "def main({}):".format(test_in),
                "  return 0"
            ])

            s = Script(script_path)
            if isinstance(test_assert, type) and issubclass(test_assert, Exception):
                with self.assertRaises(test_assert):
                    parser = s.parse()

            else:
                s.parse()
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
            s.parse()
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
        s.parse()
        #parser.print_help()
        self.assertEqual(desc, s.parser.description)

