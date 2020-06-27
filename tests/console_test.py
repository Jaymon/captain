# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from . import testdata, TestCase, FileScript, ModuleScript




class EntryPointsTest(TestCase):
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

    def test_python37_console_scripts(self):
        """https://github.com/Jaymon/transcribe/issues/2"""
        m = ModuleScript([
            "class Default(Command):",
            "    def handle(self): print('success 3.7+')",
        ])

        path = testdata.create_file(contents=[
            #"#!{}".format(testdata.get_interpreter()), # added for tests (not in original)
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
            #"#!{}".format(testdata.get_interpreter()), # added for tests (not in original)
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
            #environ={"PYTHONPATH": "."},
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

    def xtest_stack_multi_entry_points(self):
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

    def xtest_normal_script(self):
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

    def xtest_main_script(self):
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



