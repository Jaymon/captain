# -*- coding: utf-8 -*-
import subprocess

from . import TestCase, FileScript


class ArgTest(TestCase):
    def test_dest_positional(self):
        s = FileScript([
            "class Default(Command):",
            "    @arg('f', metavar='FOO', type=int)",
            "    def handle(self, f): print(f)",
        ])

        r = s.run("--help")
        self.assertTrue("FOO" in r)

        r = s.run("1234567")
        self.assertTrue("1234567" in r)

        s = FileScript([
            "class Default(Command):",
            "    @arg('f', type=int)",
            "    def handle(self, f): print(f)",
        ])

        r = s.run("--help")
        self.assertRegex(r, r"\s+[fF]\s+")

        r = s.run("1234567")
        self.assertTrue("1234567" in r)

