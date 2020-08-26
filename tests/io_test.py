# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import datetime

from captain.io import Output, Input
from captain.compat import *

from . import testdata, TestCase, FileScript, ModuleScript


class InputTest(TestCase):
    def create_input(self, **kwargs):
        class MockInput(object):
            def __init__(self, answer):
                self.answer = answer

            def __call__(self, question):
                self.question = question
                return self.answer

        kwargs.setdefault("stdin", MockInput(kwargs.pop("answer", "yes")))
        return Input(**kwargs)

    def test_polar(self):
        i = self.create_input(answer="y")
        i.polar("Is this ok?")
        self.assertEqual("Is this ok? (y|n) ", i.stdin.question)


    def test_prompt_prompt(self):
        i = self.create_input()

        i.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("Is this ok? (y|n) ", i.stdin.question)

        i.prompt("Is this ok?\n", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("Is this ok? (y|n)\n", i.stdin.question)

        i.prompt("Is this ok")
        self.assertEqual("Is this ok ", i.stdin.question)

        i.prompt("Is this ok\n")
        self.assertEqual("Is this ok\n", i.stdin.question)

    def test_prompt_answer(self):
        i = self.create_input(answer="yes")
        answer = i.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("y", answer)

        i = self.create_input(answer="no")
        answer = i.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})
        self.assertEqual("n", answer)

        i = self.create_input(answer="n")
        answer = i.prompt("Is this ok?", choices=["y", "n"])
        self.assertEqual("n", answer)

        i = self.create_input(answer="n")
        answer = i.prompt("Is this ok?", choices={"y": ["yes"], "n": ["no"]})
        self.assertEqual("n", answer)


class OutputTest(TestCase):
    def test_err(self):
        """https://github.com/Jaymon/captain/issues/44"""
        o = Output()
        with testdata.capture() as r:
            o.err("foo")
        self.assertEqual("foo\n", str(r.stderr))

    def test_prefix(self):
        o = Output()
        for i, x in enumerate(["a", "b", "c", "d"], 1):
            with o.prefix("{}. ", i):
                o.out(testdata.get_words(1))
                with o.indent("{}- ", x):
                    o.out(testdata.get_words(1))
                o.out(testdata.get_words(1))

    def test_increment(self):
        """https://github.com/Jaymon/captain/issues/41"""
        o = Output()
        with testdata.capture() as r:
            for x in o.increment(range(5)):
                o.out(x)
        self.assertTrue("1. " in r)
        self.assertTrue("5. " in r)

        with testdata.capture() as r:
            for x in o.incr(range(5)):
                o.out(x)
            o.out("=======")
        self.assertTrue("1. " in r)
        self.assertTrue("5. " in r)
        self.assertFalse(" =======" in r)

    def test_profile(self):
        o = Output()
        with o.profile():
            o.out("profile 1")

        with testdata.capture() as r:
            with o.profile("foo"):
                o.out("profile 2")
        self.assertTrue("foo in" in r)

        with testdata.capture() as r:
            with o.profile(quiet=True) as p:
                pass
        p.stop_time += 10
        self.assertEqual("10.0s", p.elapsed())

    def test_no_format(self):
        o = Output()
        o.out("this should not {fail}")

        v = None
        with self.assertRaises(KeyError):
            o.out("this should {fail}", v)

    def test_inline(self):
        o = Output()
        with testdata.capture() as r:
            for x in range(10):
                o.inline(".")

        self.assertTrue(".........." in r)

    def test_non_string(self):
        o = Output()
        a = list(range(5))
        o.out(a)

    def test_blank_bar(self):
        o = Output()
        o.out("no args, should be one Newline")
        o.br()
        o.bar()

        o.out("passed in 5")
        o.blank(5)
        o.bar("=", 5)

    def test_out_no_args(self):
        o = Output()
        o.out("foo {}".format("bar"))
        o.out("this does not have any format args")
        o.out("")

    def test_hr(self):
        o = Output()
        o.out("text before")
        o.hr()
        o.out("text after")

    def test_quote(self):
        o = Output()

        with testdata.capture() as r:
            o.quote("line 1\nline 2\nline 3")
        self.assertTrue("  line 1" in r)
        self.assertTrue("  line 2" in r)
        self.assertTrue("  line 3" in r)

        with testdata.capture() as r:
            o.quote("this is the string")
        self.assertTrue("  this" in r)

    def test_headers(self):
        o = Output()
        shorter = "this is the header"
        longer = testdata.get_ascii_words(80)

        o.h1(shorter)
        o.br()
        o.h1(longer)

        o.br()

        o.h2(shorter)
        o.br()
        o.h2(longer)

        o.br()

        o.h3(shorter)
        o.br()
        o.h3(longer)

        o.br()

    def test_box(self):
        o = Output()
        s = testdata.get_words(80)
        o.box(s)

    def test_bullets(self):
        o = Output()
        lines = [testdata.get_ascii_words(4) for x in range(5)]
        o.ul(*lines)
        o.br()
        o.ol(*lines)

    def test_table_1(self):
        o = Output()
        one = [1, 3, 5, 7, 9]
        two = [2, 4, 6, 8, 0]
        o.table(one, two)

        it = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 0))
        o.table(it)

        o.table(range(20), range(20))

    def test_table_alignment(self):
        """https://github.com/Jaymon/captain/issues/52"""
        o = Output()
        it = (("fooo_type", 0), ("fooooooo_name", "barrrrrr Chee Bazzzz"))
        o.table(it, headers=["left", "right"])

    def test_table_dict(self):
        o = Output()
        d = {
            "foo": [1, 2, 3, 4],
            "bar": [5, 6, 7],
            "che": [8, 9, 10, 11, 12],
        }
        with testdata.capture(loggers=False) as r1:
            o.table(d)

        d = {
            "foo": "[1, 2, 3, 4]",
            "bar": "[5, 6, 7]",
            "che": "[8, 9, 10, 11, 12]",
        }
        with testdata.capture(loggers=False) as r2:
            o.table(d)

        self.assertNotEqual(r1, r2)

    def test_table_rows(self):
        o = Output()
        it = [
            [1, 5, 8],
            [2, 6, 9],
            [3, 7, 10],
            [4, "", 11],
            ["", "", 12],
        ]

        with testdata.capture(loggers=False) as r1:
            o.table(it, headers=["foo", "bar", "che"])

        with testdata.capture(loggers=False) as r2:
            o.table_from_rows(*it, headers=["foo", "bar", "che"])

        self.assertEqual(r1, r2)

    def test_table_columns(self):
        o = Output()
        it = [[1, 2, 3, 4], [5, 6, 7], [8, 9, 10, 11, 12]]

        with testdata.capture(loggers=False) as r1:
            o.table(*it, headers=["foo", "bar", "che"])

        with testdata.capture(loggers=False) as r2:
            o.table_from_columns(*it, headers=["foo", "bar", "che"])

        self.assertEqual(r1, r2)

    def test_table_headers(self):
        o = Output()
        it = ((1, 2), (3, 4))

        o.table(it, headers=["foo", "bar"])
        o.table(it, headers=["foo", "bar", "che"])

    def test_table_widths(self):
        o = Output()
        widths = [5]
        o.table([(1, 2)], widths=widths)
        o.table([(3, 4)], widths=widths)
        widths = [0, 5]
        o.table([(5, 6)], widths=widths)

    def test_table_unicode(self):
        o = Output()
        l = [(1, testdata.get_unicode_words()), (2, testdata.get_unicode_words())]
        o.table(l)

        l = [(1, [testdata.get_unicode_words()]), (2, [testdata.get_unicode_words()])]
        o.table(l)

    def test_table_none_value(self):
        """We were getting an error in a script when passing d.items() to the table
        method with a None value"""
        o = Output()
        d = {
            "foo": None,
            "bar": None,
            "che": None
        }

        o.table(d)

    def test_progress_n(self):
        o = Output()
        count = 100
        with o.progress(count) as p:
            for x in range(count):
                p.update(x)

    def test_progress_bar(self):
        o = Output()
        count = 100
        with o.progress_bar(count, char="#") as pbar:
            for x in range(count):
                pbar.update(x)

        # https://github.com/Jaymon/captain/issues/27
        with o.progress_bar(count, char="\u2588") as pbar:
            for x in range(count):
                pbar.update(x)



