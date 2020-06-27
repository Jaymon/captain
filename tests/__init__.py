# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

import testdata
from testdata.test import TestCase, SkipTest

from captain import logging, environ


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
        #return Captain(self.path, cwd=self.cwd)
        return testdata.FileCommand(self.path, cwd=self.cwd)

    def __init__(self, body, fname=''):
        self.body = body
        if not isinstance(body, basestring):
            self.body = "\n".join(body)

        if "from captain" not in self.body or "import captain" not in self.body:
            self.body = "\n".join([
                #"#!/usr/bin/env python",
                "from captain import arg, args, echo",
                "import captain",
                "",
                "",
            ]) + self.body


        if "__name__ == " not in self.body:
            self.body += "\n".join([
                "",
                "",
                "if __name__ == '__main__':",
                "    captain.exit(__name__)",
            ])

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


