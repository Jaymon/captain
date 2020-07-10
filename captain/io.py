# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import textwrap
import os
import re
from contextlib import contextmanager
from collections import Counter
import time
import io

from .compat import *
from . import environ
from . import logging


class Input(io.IOBase):
    """An instance of this class will be available in a handle() method using
    self.input, it allows you to prompt for user input"""
    def __init__(self, stdin=None, **kwargs):
        self.stdin = stdin or input

    def polar(self, question):
        """Ask a yes/no question

        :Example:
            def handle(self):
                answer = self.input.polar("Are you interested?")

        https://en.wikipedia.org/wiki/Yes%E2%80%93no_question

        :param question: string, the string that will take y/n as an answer
        :returns: boolean, True if yes, False if no
        """
        answer = self.prompt(
            question,
            choices={
                "y": ["yes", "y", "ye", "yeah", "yup"],
                "n": ["no", "n", "nah"]
            },
            type=lambda v: v.strip().lower()
        )
        return True if answer.startswith("y") else False

    def yesno(self, question):
        return self.polar(question)

    def prompt(self, question, choices=None, type=lambda v: v.strip().lower()):
        """echo a prompt to the user and wait for an answer

        :Example:
            def handle(self):
                answer = self.input.prompt(
                    "Is this ok?",
                    choices={
                        "y": ["yes", "y"],
                        "n": ["no", "n"]
                    }
                )

        :param question: string, the prompt for the user
        :param choices: list|dict, if given, only exit when prompt matches one of the choices
        :param ignore_case: boolean, True if answer case doesn't matter
        :param type: callable, any answer will be ran through this as type(answer)
        :returns: string, the answer that was given by the user
        """
        if not type:
            type = lambda: x

        if choices:
            if isinstance(choices, Mapping):
                for k in list(choices.keys()):
                    choices[k] = set(type(v) for v in choices[k])

                choices[k].add(type(k))

            else: # choices is a Sequence
                d = {}
                for v in choices:
                    d[v] = set([type(v)])
                choices = d

        m = re.search(r"(\s*)$", question)
        whitespace = m.group(1)
        if not whitespace:
            whitespace = " "

        question = question.rstrip()

        if choices:
            question = "{} ({}){}".format(question, "|".join(choices.keys()), whitespace)

        else:
            question = "{}{}".format(question, whitespace)

        while True:
            answer = type(self.stdin(question))

            if choices:
                found = False
                for k, v in choices.items():
                    if answer in v:
                        answer = k
                        found = True
                        break

                if found:
                    break

            else:
                break

        return answer


class Output(io.IOBase):
    """An instance of this class will be available in a handle() method using
    self.output, it contains handy outputting format methods

    This is handy for captain scripts to be able to route their prints through and it
    will obey the passed in --quiet commmand line argument automatically"""
    def __init__(self, stdout=None, stderr=None, **kwargs):
        self.stdout = stdout or logging.stdout
        self.stderr = stderr or logging.stderr
        self._prefix = kwargs.pop("prefix", "")
        self._suffix = kwargs.pop("suffix", "\n")
        self.width = kwargs.pop("width", environ.WIDTH)

    @contextmanager
    def prefix(self, format_msg, *args, **kwargs):
        prefix_orig = self._prefix
        try:
            self._prefix = format_msg.format(*args, **kwargs)
            yield self

        finally:
            self._prefix = prefix_orig

    def indent(self, format_msg="  ", *args, **kwargs):
        return self.prefix(format_msg, *args, **kwargs)

    def increment(self, itr, n=1, format_msg="{}. "):
        """Similar to enumerate but will set format_msg.format(n) into the prefix on
        each iteration

        :Example:
            for v in increment(["foo", "bar"]):
                echo.out(v) # 1. foo\n2. bar

        :param itr: iterator, any iterator you want to set a numeric prefix on on every
            iteration
        :param n: integer, the starting integer for the numeric prefix
        :param format_msg: string, this will basically do: format_msg.format(n) so there
            should only be one set of curly brackets
        :returns: yield generator
        """
        for i, v in enumerate(itr, n):
            self._prefix = format_msg.format(i)
            yield v

    def incr(self, *args, **kwargs):
        return self.increment(*args, **kwargs)

    @contextmanager
    def progress(self, length=100, **kwargs):
        """display a progress that can update in place

        example -- 
            total_length = 1000
            with echo.progress(total_length) as p:
                for x in range(total_length):
                    # do something crazy
                    p.update(x)

        length -- int -- the total size of what you will be updating progress on
        """
        progress_class = kwargs.pop("progress_class", Progress)
        kwargs["output"] = self
        kwargs["length"] = length
        pbar = progress_class(**kwargs)
        pbar.update(0)
        yield pbar
        pbar.update(length)

    def progress_bar(self, length=100, **kwargs):
        """display a progress bar

        example -- 
            total_length = 1000
            with echo.progress_bar(total_length) as bar:
                for x in range(total_length):
                    # do something crazy
                    bar.update(x)

        length -- int -- the total size of what you will be iterating on
        """
        kwargs["progress_class"] = ProgressBar
        return self.progress(length, **kwargs)

    @contextmanager
    def profile(self, format_msg="", *args, **kwargs):
        """context manager to print out how long it ran

        :Example:
            with echo.profile():
                # do stuff

        :param msg: string, the message you want to display with the elapsed time
        """
        start = time.time()
        yield self
        stop = time.time()
        elapsed = round(abs(stop - start) * 1000.0, 1)

        if format_msg:
            format_msg +=  " in {:.1f} ms"
        else:
            format_msg =  "{:.1f} ms"

        args = list(args)
        args.append(elapsed)

        self.out(format_msg, *args, **kwargs)

    def critical(self, format_msg, *args, **kwargs):
        kwargs.setdefault("logmethod", self.stderr.critical)
        return self.write(format_msg, *args, **kwargs)

    def crit(self, format_msg, *args, **kwargs):
        return self.critical(format_msg, *args, **kwargs)

    def exception(self, e):
        '''print an exception message to stderr ERROR'''
        self.stderr.exception(e)

    def exc(self, e):
        return self.exception(e)

    def error(self, format_msg, *args, **kwargs):
        kwargs.setdefault("logmethod", self.stderr.error)
        return self.write(format_msg, *args, **kwargs)

    def err(self, format_msg, *args, **kwargs):
        '''print format_msg to stderr ERROR'''
        return self.error(format_msg, *args, **kwargs)

    def warning(self, format_msg, *args, **kwargs):
        '''print format_msg to stderr WARNING'''
        kwargs.setdefault("logmethod", self.stderr.warning)
        return self.write(format_msg, *args, **kwargs)

    def warn(self, format_msg, *args, **kwargs):
        return self.warning(format_msg, *args, **kwargs)

    def info(self, format_msg, *args, **kwargs):
        '''print format_msg to stdout INFO'''
        kwargs.setdefault("logmethod", self.stdout.info)
        return self.write(format_msg, *args, **kwargs)

    def out(self, format_msg, *args, **kwargs):
        '''print format_msg to stdout INFO'''
        return self.info(format_msg, *args, **kwargs)

    def debug(self, format_msg, *args, **kwargs):
        '''print format_msg to stdout DEBUG'''
        kwargs.setdefault("logmethod", self.stdout.debug)
        return self.write(format_msg, *args, **kwargs)

    def verbose(self, format_msg, *args, **kwargs):
        '''print format_msg to stdout INFO'''
        return self.debug(format_msg, *args, **kwargs)

    def format(self, format_msg, *args, **kwargs):
        prefix = kwargs.pop("prefix", self._prefix)
        suffix = kwargs.pop("suffix", self._suffix)

        if isinstance(format_msg, basestring):
            format_msg = prefix + format_msg + suffix
        else:
            format_msg = prefix + String(format_msg) + suffix

        if args or kwargs:
            s = format_msg.format(*args, **kwargs)
        else:
            s = format_msg

        return s

    def write(self, format_msg, *args, **kwargs):
        '''print format_msg to stdout, taking into account --quiet setting'''
        logmethod = kwargs.pop("logmethod", self.stdout.info)
        exc_info = kwargs.pop("exc_info", False)

        if format_msg == "":
            kwargs.setdefault("prefix", "")

        s = self.format(format_msg, *args, **kwargs)
        logmethod(s, exc_info=exc_info)

    def raw(self, s, **kwargs):
        stream = self.stderr.handlers[0].stream
        logmethod = kwargs.pop("logmethod", self.stderr.info)
        logmethod(s)

    def inline(self, format_msg, *args, **kwargs):
        """print one or more characters without a newline at the end

        example --
            for x in range(1000):
                echo.inline(".")
        """
        # http://stackoverflow.com/questions/493386/how-to-print-in-python-without-newline-or-space
        kwargs.setdefault("prefix", "")
        kwargs.setdefault("suffix", "")
        self.write(format_msg, *args, **kwargs)

    def hr(self, sep="-", width=0):
        """similar to the html horizontal rule in html"""
        self.bar(sep=sep, width=width)

    def bar(self, sep='*', width=0):
        width = width or self.width
        self.info(sep * width)

    def h1(self, format_msg, *args, **kwargs):
        kwargs.setdefault("prefix", "# ")
        self.h3(format_msg, *args, **kwargs)

    def h2(self, format_msg, *args, **kwargs):
        kwargs.setdefault("prefix", "## ")
        self.h3(format_msg, *args, **kwargs)

    def h3(self, format_msg, *args, **kwargs):
        #kwargs.setdefault("prefix", "* ")
        kwargs.setdefault("prefix", "### ")
        self.write(format_msg, *args, **kwargs)

    def box(self, format_msg, *args, **kwargs):
        width = kwargs.pop("width", self.width)
        s = self.format(format_msg, *args, **kwargs)
        sep = kwargs.pop("sep", "*")
        prefix = "{} ".format(sep)

        wrapper = textwrap.TextWrapper(
            initial_indent=prefix,
            subsequent_indent=prefix,
            width=width - len(prefix),
        )
        s = wrapper.fill(s)

        self.bar(sep=sep, width=width)
        self.write(s)
        self.bar(sep=sep, width=width)

    def banner(self, format_msg, *args, **kwargs):
        self.box(format_msg, *args, **kwargs)

    def br(self, count=1):
        """print out a blank newline"""
        for x in range(count):
            self.write("")

    def blank(self, count=1):
        return self.br(count=count)

    def newline(self, count=1):
        return self.br(count=count)

    def quote(self, format_msg, *args, **kwargs):
        prefix = kwargs.pop("prefix", "  ")

        msg = self.format(format_msg, *args, **kwargs)

        width = kwargs.pop("width", self.width)
        width -= len(prefix)

        if is_py2:
            lines = []
            for line in msg.splitlines():
                lines.append(prefix + line)
            s = "\n".join(lines)

        else:
            s = textwrap.indent(msg, prefix)

        self.write(s)

    def ul(self, *lines):
        """unordered list"""
        self.bullets(*lines, numbers=True)

    def ol(self, *lines):
        """ordered list"""
        self.bullets(*lines, numbers=False)

    def bullets(self, *lines, **kwargs):
        numbers = kwargs.get("numbers", False)
        if len(lines) == 1:
            if not isinstance(lines[0], basestring):
                if isinstance(lines[0], (list, tuple)):
                    lines = lines[0]

                else:
                    try:
                        lines = list(lines[0])

                    except TypeError:
                        pass

        if numbers:
            bullet_lines = ["{}.".format(i) for i in range(1, len(lines) + 1)]

        else:
            bullet_lines = ["*"] * len(lines)

        self.table(bullet_lines, lines, column_delim="", widths=[len(bullet_lines[-1]) + 2])

    def row(self, row, **kwargs):
        """This is more of a specialty version of table that just prints one row

        this is handy for when you are iterating through data and don't want to print
        it all at the end but would rather print it one row at a time

        :param row: list, the columns of the row you want to print
        :param **kwargs: dict, all the options in table()
        """
        return self.table([row], **kwargs)

    def columns(self, *columns, **kwargs):
        self.table(*columns, **kwargs)

    def table(self, *columns, **kwargs):
        """
        format columned data so we can easily print it out on a console, this just takes
        columns of data and it will format it into properly aligned columns, it's not
        fancy, but it works for most type of strings that I need it for, like server name
        lists.

        other formatting options:
            http://stackoverflow.com/a/8234511/5006

        other packages that probably do this way better:
            https://stackoverflow.com/a/26937531/5006

        :Example:
            >>> echo.table([(1, 2), (3, 4), (5, 6), (7, 8), (9, 0)])
            1  2
            3  4
            5  6
            7  8
            9  0
            >>> echo.table([1, 3, 5, 7, 9], [2, 4, 6, 8, 0])
            1  2
            3  4
            5  6
            7  8
            9  0

        :param *columns: dict|list of lists| *lists, can either be a list of rows or
            multiple lists representing each column in the table, or a dict where the
            keys are the headers and the values are the columns corresponding to that
            header
        :param **kwargs: dict
            prefix -- string -- what you want before each row (eg, a tab)
            #buf_count -- integer -- how many spaces between longest col value and its neighbor
            headers -- list -- the headers you want, must match column count
            widths -- list -- the widths of each column you want to use, this doesn't have
                to match column count, so you can do something like [0, 5] to set the
                minimum width of the second column to 5
            width -- int -- similar to widths except it will set this minimum value for all columns
            column_delim -- string -- what goes between each column, defaults to " | "
            header_delim -- string, what goes between headers and content rows
        """
        ret = []

        headers = kwargs.get("headers", [])
        prefix = kwargs.get('prefix', '')
        #buf_count = kwargs.get('buf_count', 2)
        column_delim = kwargs.get("column_delim", " | ")
        header_delim = kwargs.get("header_delim", "-")
        if len(columns) == 1:
            # input is a list of rows or dict of columns
            if isinstance(columns[0], Mapping):
                # columns are a dict, so keys will be headers and values will be
                # the columns
                all_lists = True
                for v in columns[0].values():
                    if not isinstance(v, list):
                        all_lists = False
                        break

                if all_lists:
                    headers = list(columns[0].keys())
                    columns = list(zip_longest(*columns[0].values(), fillvalue=""))
                else:
                    columns = list(zip_longest(columns[0].keys(), columns[0].values(), fillvalue=""))

            else:
                # columns are a list of rows
                columns = list(columns[0])

        else:
            # input is a bunch of columns
            # without the list the zip iterator gets spent
            columns = list(zip_longest(*columns, fillvalue=""))

        if headers:
            columns.insert(0, headers)

        # columns should now consist of a list of lists where each list is a row in
        # the table, so len(columns) would give the number of rows and
        # len(columns[0]) would give the number of columns


        # we have to go through all the rows and calculate the max width of each
        # column of each row
        width = int(kwargs.get("width", 0))
        widths = kwargs.get("widths", [])
        row_counts = Counter()
        for i in range(len(widths)):
            row_counts[i] = int(widths[i])

        for row in columns:
            for i, c in enumerate(row):
                c = "None" if c is None else String(c)
                row_counts[i] = max(row_counts[i], len(c), width)

        def rowstr(row, prefix, row_counts, column_delim):
            row_format = prefix + column_delim
            cols = list(map(String, row))
            for i in range(len(row_counts)):
                if len(cols) > i:
                    cols.append("")

                c = cols[i]
                # build the format string for each row, we use the row_counts found
                # above to decide how much padding each column should get
                # https://stackoverflow.com/a/9536084/5006
                if not c or re.match(r"^\d+(?:\.\,\d+)?$", c):
                    # right align digits
                    #row_format += "{:>" + str(row_counts[i]) + "}" + (" " * buf_count)
                    row_format += "{:>" + str(row_counts[i]) + "}" + column_delim
                    #row_format += "{:>" + str(row_counts[i] + (buf_count if i > 0 else 0)) + "}"
                    #row_format += "{:>" + str(row_counts[i]) + "}"
                else:
                    # left align
                    #row_format += "{:<" + str(row_counts[i] + buf_count) + "}"
                    #row_format += "{:<" + str(row_counts[i]) + "}" + (" " * buf_count)
                    row_format += "{:<" + str(row_counts[i]) + "}" + column_delim

            return row_format.strip().format(*map(lambda x: "None" if x is None else String(x), cols))

        if headers:
            # we pop the headers from the columns because we had to put it into the
            # columns so we could correctly calculate widths
            ret.append(rowstr(columns.pop(0), prefix, row_counts, column_delim))

            # we need to figure out exactly how long the table is
            delim_count = (sum(row_counts.values()) + (len(column_delim) * (len(row_counts) + 1)))
            delim_count -= (len(column_delim) - len(column_delim.lstrip())) # left side of table
            delim_count -= (len(column_delim) - len(column_delim.rstrip())) # right side of table
            ret.append(prefix + (header_delim * delim_count))

        for row in columns:
            ret.append(rowstr(row, prefix, row_counts, column_delim))

        self.out("\n".join(ret))


    def table_from_rows(self, *rows, **kwargs):
        """makes a table from the passed in rows

        :param *rows: list, each passed in list will be one row
        :param **kwargs: see table()
        """
        return self.table(rows, **kwargs)
    rows_table = table_from_rows
    row_table = table_from_rows
    table_rows = table_from_rows
    table_row = table_from_rows

    def table_from_dict(self, d, **kwargs):
        """makes a table from a dict

        :param d: dict, keys are headers, values are columns
        :param **kwargs: see table()
        """
        return self.table(d, **kwargs)
    dict_table = table_from_dict
    table_dict = table_from_dict

    def table_from_columns(self, *columns, **kwargs):
        """makes a table from the passed in columns

        :param *rows: list, each passed in list will be one column
        :param **kwargs: see table()
        """
        return self.table(*columns, **kwargs)
    table_from_cols = table_from_columns
    columns_table = table_from_columns
    column_table = table_from_columns
    col_table = table_from_columns
    cols_table = table_from_columns
    table_columns = table_from_columns
    table_column = table_from_columns
    table_col = table_from_columns
    table_cols = table_from_columns


class Progress(object):
    def __init__(self, output, length, **kwargs):
        self.length = length
        self.output = output

    def get_percentage(self, current):
        fill = float(current) / float(self.length)
        percentage = "[{:3.2f}%]".format(fill * 100.0)
        return percentage

    def get_progress(self, current):
        # http://stackoverflow.com/a/5676884/5006
        # http://stackoverflow.com/a/22776/5006
        bar = "{current: >{justify}}/{length} {percentage: >10}".format(
        #bar = "{: >10} {: >10}".format(
            current=current,
            justify=len(str(self.length)) + 1,
            length=self.length,
            percentage=self.get_percentage(current)
        )
        return bar

    def update(self, current):
        bar = self.get_progress(current)
        #self.output.err(bar + chr(8) * (len(bar) + 1), suffix="")
        self.output.out(bar + chr(8) * (len(bar) + 1), suffix="")


class ProgressBar(Progress):
    def __init__(self, output, length, char="\u2588"):
        super(ProgressBar, self).__init__(output, length)
        self.bar_width = self.output.width - 11
        self.char = char

    def get_progress(self, current):
        # http://stackoverflow.com/a/21008062/5006
        fill = float(current) / float(self.length)
        bar_length = int(self.bar_width * fill)
        bar = "[{}{}]{: >10}".format(
            self.char * bar_length,
            " " * (self.bar_width - bar_length),
            self.get_percentage(current)
        )
        return bar

