# -*- coding: utf-8 -*-
"""
This is handy for captain scripts to be able to route their prints through and it
will obey the passed in --quiet commmand line argument automatically
"""
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import textwrap
import os
import re
from contextlib import contextmanager
from collections import Counter
import time

from .compat import *
from .logging import stdout, istdout, stderr


WIDTH = 80
"""lots of the functions are width constrained, this is the global width they default to"""


class Prefix(object):
    """This prefix is used by the out() function to put something before the string
    passed into out()"""
    current = ""
    """holds the current prefix"""

    def __init__(self, format_msg, *args, **kwargs):
        self.previous = self.get()
        self(format_msg, *args, **kwargs)

    def __call__(self, format_msg, *args, **kwargs):
        s = str(format_msg)
        if args or kwargs:
            s = format_msg.format(*args, **kwargs)
        type(self).current = s

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self(self.previous)
        return

    @classmethod
    def has(cls):
        return bool(cls.current)

    @classmethod
    def get(cls):
        return cls.current


class Progress(object):
    def __init__(self, write_method, length, **kwargs):
        self.length = length
        self.write_method = write_method

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
        self.write_method(bar + chr(8) * (len(bar) + 1))


class ProgressBar(Progress):
    def __init__(self, write_method, length, width, char="\u2588"):
        super(ProgressBar, self).__init__(write_method, length)
        self.bar_width = width - 11
        self.width = width
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


@contextmanager
def progress(length, **kwargs):
    """display a progress that can update in place

    example -- 
        total_length = 1000
        with echo.progress(total_length) as p:
            for x in range(total_length):
                # do something crazy
                p.update(x)

    length -- int -- the total size of what you will be updating progress on
    """
    quiet = False
    progress_class = kwargs.pop("progress_class", Progress)
    kwargs["write_method"] = istdout.info
    kwargs["width"] = kwargs.get("width", globals()["WIDTH"])
    kwargs["length"] = length
    pbar = progress_class(**kwargs)
    pbar.update(0)
    yield pbar
    pbar.update(length)
    br()


def progress_bar(length, **kwargs):
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
    return progress(length, **kwargs)


def increment(itr, n=1, format_msg="{}. "):
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
        with prefix(format_msg, i):
            yield v
incr=increment


def prefix(format_msg, *args, **kwargs):
    """Return a prefix instance

    :Example:
        with echo.prefix("foo "):
            echo.out("bar") # "foo bar"
    """
    return Prefix(format_msg, *args, **kwargs)


def exception(e):
    '''print an exception message to stderr (this does not honor quiet)'''
    stderr.exception(e)


def err(format_msg, *args, **kwargs):
    '''print format_msg to stderr'''
    exc_info = kwargs.pop("exc_info", False)
    stderr.warning(str(format_msg).format(*args, **kwargs), exc_info=exc_info)


def ch(c):
    """print one or more characters without a newline at the end

    example --
        for x in range(1000):
            echo.ch(".")

    c -- string -- the chars that will be output
    """
    # http://stackoverflow.com/questions/493386/how-to-print-in-python-without-newline-or-space
    #pout.v(istdout.handlers[0].stream)
    istdout.info(c)


def out(format_msg="", *args, **kwargs):
    '''print format_msg to stdout, taking into account --quiet setting'''
    logmethod = kwargs.get("logmethod", stdout.info)

    if format_msg != "":
        if Prefix.has():
            if isinstance(format_msg, basestring):
                format_msg = Prefix.get() + format_msg
            else:
                format_msg = Prefix.get() + str(format_msg)

        if isinstance(format_msg, basestring):
            if args or kwargs:
                s = format_msg.format(*args, **kwargs)
            else:
                s = format_msg
            logmethod(s)
#             width = globals()["width"]
#             s = textwrap.fill(s, width=width)
#             stdout.info(s)

        else:
            logmethod(str(format_msg))

    else:
        logmethod("")


def verbose(format_msg="", *args, **kwargs):
    '''print format_msg to stdout, taking into account --verbose flag'''
    kwargs["logmethod"] = stdout.debug
    out(format_msg, *args, **kwargs)


def hr(width=0):
    """similar to the html horizontal rule in html"""
    if not width: width = globals()["WIDTH"]
    bar("_", width=width)
    blank()


def h1(format_msg, *args, **kwargs):
    bar("*")
    h3(format_msg, *args, **kwargs)
    bar("*")


def h2(format_msg, *args, **kwargs):
    h3(format_msg, *args, **kwargs)
    bar("*")


def h3(format_msg, *args, **kwargs):
    wrapper = textwrap.TextWrapper()
    wrapper.width = globals()["WIDTH"]
    wrapper.initial_indent = "* "
    wrapper.subsequent_indent = "* "

    if not isinstance(format_msg, basestring):
        format_msg = str(format_msg)

    if args or kwargs:
        h = wrapper.fill(format_msg.format(*args, **kwargs))
    else:
        h = wrapper.fill(format_msg)

    out(h)


def br(count=1):
    """print out a blank newline"""
    for x in range(count):
        out("")
blank = br
newline = br


def ul(*lines):
    """unordered list"""
    bullets(*lines, numbers=True)


def ol(*lines):
    """ordered list"""
    bullets(*lines, numbers=False)


def quote(format_msg, *args, **kwargs):
    if args or kwargs:
        msg = format_msg.format(*args, **kwargs)
    else:
        msg = format_msg

    default_indent = "    "
    width = globals()["WIDTH"]
    width -= len(default_indent) 

    wrapper = textwrap.TextWrapper()
    wrapper.width = width
    wrapper.initial_indent = default_indent
    wrapper.subsequent_indent = default_indent
    s = wrapper.fill(msg)
    indent(s, indent=default_indent)


def indent(msg, indent="    "):
    out(indent + msg)


def bar(sep='*', width=0):
    if not width: width = globals()["WIDTH"]
    out(sep * width)


def bullets(*lines, **kwargs):
    numbers = kwargs.get("numbers", False)
    if numbers:
        bullet_lines = ["{}.".format(i) for i in range(1, len(lines) + 1)]

    else:
        bullet_lines = ["*"] * len(lines)

    columns(bullet_lines, lines)


def banner(*lines, **kwargs):
    """prints a banner

    sep -- string -- the character that will be on the line on the top and bottom
        and before any of the lines, defaults to *
    count -- integer -- the line width, defaults to 80
    """
    sep = kwargs.get("sep", "*")
    count = kwargs.get("width", globals()["WIDTH"])

    out(sep * count)
    if lines:
        out(sep)

        for line in lines:
            out("{} {}".format(sep, line))

        out(sep)
        out(sep * count)


def row(row, **kwargs):
    """This is more of a specialty version of table that just prints one row

    this is handy for when you are iterating through data and don't want to print
    it all at the end but would rather print it one row at a time

    :param row: list, the columns of the row you want to print
    :param **kwargs: dict, all the options in table()
    """
    return table([row], **kwargs)

def table(*columns, **kwargs):
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
            headers = list(columns[0].keys())
            columns = list(zip_longest(*columns[0].values(), fillvalue=""))
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
            row_counts[i] = max(row_counts[i], len(String(c)), width)

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

        return row_format.strip().format(*cols)

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

    out(os.linesep.join(ret))
columns = table


def table_from_dict(d, **kwargs):
    """makes a table from a dict

    :param d: dict, keys are headers, values are columns
    :param **kwargs: see table()
    """
    return table(d, **kwargs)
dict_table = table_from_dict
table_dict = table_from_dict


def table_from_rows(*rows, **kwargs):
    """makes a table from the passed in rows

    :param *rows: list, each passed in list will be one row
    :param **kwargs: see table()
    """
    return table(rows, **kwargs)
rows_table = table_from_rows
row_table = table_from_rows
table_rows = table_from_rows
table_row = table_from_rows


def table_from_columns(*columns, **kwargs):
    """makes a table from the passed in columns

    :param *rows: list, each passed in list will be one column
    :param **kwargs: see table()
    """
    return table(*columns, **kwargs)
table_from_cols = table_from_columns
columns_table = table_from_columns
column_table = table_from_columns
col_table = table_from_columns
cols_table = table_from_columns
table_columns = table_from_columns
table_column = table_from_columns
table_col = table_from_columns
table_cols = table_from_columns


@contextmanager
def profile(msg=""):
    """context manager to print out how long it ran

    :Example:
        with echo.profile():
            # do stuff

    :param msg: string, the message you want to display with the elapsed time
    """
    start = time.time()
    yield
    stop = time.time()
    elapsed = round(abs(stop - start) * 1000.0, 1)
    if msg:
        msg = msg.rstrip() + " "
    out("{}{:.1f} ms", msg, elapsed)


def prompt(question, choices=None, type=lambda v: v.lower()):
    """echo a prompt to the user and wait for an answer

    :Example:
        answer = echo.prompt("Is this ok?", choices={"y": ["yes", "y"], "n": ["no", "n"]})

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
        answer = type(input(question))

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

