from unittest import TestCase
import os
import subprocess

import testdata

from commands import Script, ScriptArg

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

    def run(arg_str=''):
        pwd = os.path.dirname(__file__)
        cmd = "python {}/commands.py {} {}".format(pwd, self.path, arg_str)

        r = ''
        try:
            r = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, cwd=self.cwd).rstrip()

        except subprocess.CalledProcessError, e:
            raise RuntimeError("cmd returned {} with output: {}".format(e.returncode, e.output))

        return r


def run(script, arg_str, cwd):
    pwd = os.path.dirname(__file__)
    cmd = "python {}/commands.py {} {}".format(pwd, script, arg_str)

    r = ''
    try:
        r = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, cwd=cwd).rstrip()

    except subprocess.CalledProcessError, e:
        raise RuntimeError("cmd returned {} with output: {}".format(e.returncode, e.output))

    return r


def get_script(body):
    cwd = testdata.create_dir()
    script = testdata.create_file(
        "{}/{}.py".format(testdata.get_ascii(5), testdata.get_ascii(5)),
        "\n".join(body),
        cwd
    )

    return script, cwd


class CommandsTest(TestCase):

    def test_run_script(self):
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

    def test_validate(self):
        script_path = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        with self.assertRaises(ValueError):
            s = Script(script_path)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "",
            "# another python comment"
        ])

        with self.assertRaises(ValueError):
            s = Script(script_path)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)
        self.assertTrue(s)

    def test_get_args(self):

        tests = [
            # TODO -- check float
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
                    parser = s.get_args()

            else:
                parser = s.get_args()
                args = parser.parse_args(test_out.split())
                for k, v in test_assert.iteritems():
                    self.assertEqual(v, getattr(args, k))

            # test whether parser knows it shouldn't fail on unknown args
            script_path = TestScript([
                "#!/usr/bin/env python",
                "def main(**kwargs): return 0"
            ])

            s = Script(script_path)
            parser = s.get_args()
            self.assertTrue(parser.unknown_args)


        # make sure docblock works as description
        desc = 'this is the docblock'
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(**kwargs):",
            "  '''{}'''".format(desc),
            "  pass"
        ])

        s = Script(script_path)
        parser = s.get_args()
        #parser.print_help()
        self.assertEqual(desc, parser.description)

#class ScriptArgTest(TestCase):
#    def test_args(self):
#        a = 
#



