# -*- coding: utf-8 -*-

from . import testdata, TestCase, FileScript, ModuleScript


class EntryPointsTest(TestCase):
    """A test case that will test all the different ways we can enter into a
    captain script so I can easily test them and make sure they work across
    changes"""
    def test_python37_console_scripts(self):
        """https://github.com/Jaymon/transcribe/issues/2"""
        m = ModuleScript([
            "class Default(Command):",
            "    def handle(self): print('success 3.7+')",
        ])

        path = testdata.create_file(contents=[
            "# -*- coding: utf-8 -*-",
            "import re",
            "import sys",
            "",
            "sys.path.insert(0, '{}')".format(m.cwd), # added for tests (not in original)
            "",
            "from {} import handle".format(m.path),
            "",
            "if __name__ == '__main__':",
            "    sys.argv[0] = re.sub(r'(-script\\.pyw?|\\.exe)?$', '', sys.argv[0])",
            "    sys.exit(handle())",
        ])
        s = testdata.Command(
            "{} {}".format(testdata.get_interpreter(), path),
            cwd=m.cwd,
            #environ={"PYTHONPATH": "."},
        )

        s.run()

    def test_python27_console_scripts(self):

        m = ModuleScript([
            "class Default(Command):",
            "    def handle(self): print('success 2.7')",
        ])

        path = testdata.create_file(contents=[
            "import sys",
            "sys.path.append('{}')".format(m.cwd), # added for tests (not in original)
            "from {} import handle as handle".format(m.path),
            "",
            "def load_entry_point(*args):",
            "    return handle",
            "",
            "import pkg_resources",
            "class GDFake(object):",
            "    def __call__(self, *args, **kwargs):",
            "        return self",
            "    def get_entry_info(self, *args, **kwargs):",
            "        class o(object):",
            "            module_name = '{}'".format(m.path),
            "        return o()",
            "pkg_resources.get_distribution = GDFake()",
            ""
            "#from pkg_resources import load_entry_point",
            "",
            "if __name__ == '__main__':",
            "    sys.exit(",
            "        load_entry_point('{name}==0.0.1', 'console_scripts', '{name}')()".format(name=m.path.name),
            "    )",
        ])
        s = testdata.Command(
            "{} {}".format(testdata.get_interpreter(), path),
            cwd=m.cwd,
        )

        s.run()

    def test_script_file(self):
        """A normal <NAME>.py file"""

        s = FileScript([
            "class Default(Command):",
            "    def handle(self): print('success script file')",
        ])

        s.run()

    def test_script_main(self):
        """A <MODULE_NAME>.__main__.py file"""

        m = ModuleScript([
            "class Default(Command):",
            "    def handle(self): print('success script __main__')",
        ])

        s = testdata.Command(
            "{} -m {}".format(testdata.get_interpreter(), m.path),
            cwd=m.cwd,
        )

        s.run()

