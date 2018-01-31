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

from .compat import *
from .logging import stdout, istdout, stderr


WIDTH = 80
"""lots of the functions are width constrained, this is the global width they default to"""


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
    def __init__(self, write_method, length, width):
        super(ProgressBar, self).__init__(write_method, length)
        self.bar_width = width - 11
        self.width = width

    def get_progress(self, current):
        # http://stackoverflow.com/a/21008062/5006
        fill = float(current) / float(self.length)
        bar_length = int(self.bar_width * fill)
        bar = "[{}{}]{: >10}".format(
            "#" * bar_length,
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
    if args or kwargs:
        h = wrapper.fill(format_msg.format(*args, **kwargs))
    else:
        h = wrapper.fill(format_msg)

    out(h)


def blank(count=1): br(count)
def br(count=1):
    """print out a blank newline"""
    for x in range(count):
        out("")


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


def columns(*columns, **kwargs): return table(*columns, **kwargs)
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

    :param *columns: can either be a list of rows or multiple lists representing each
        column in the table
    :param **kwargs: dict
        prefix -- string -- what you want before each row (eg, a tab)
        buf_count -- integer -- how many spaces between longest col value and its neighbor
    """
    ret = []
    prefix = kwargs.get('prefix', '')
    buf_count = kwargs.get('buf_count', 2)
    if len(columns) == 1:
        columns = list(columns[0])
    else:
        # without the list the zip iterator gets spent, I'm sure I can make this
        # better
        columns = list(zip(*columns))

    # we have to go through all the rows and calculate the length of each
    # column of each row
    row_counts = Counter()
    for row in columns:
        for i, c in enumerate(row):
            cl = len(str(c))
            if cl > row_counts[i]:
                row_counts[i] = cl

    # build the format string for each row, we use the row_counts found above to
    # decide how much padding each column should get
    # https://stackoverflow.com/a/9536084/5006
    row_format = prefix
    for i in range(len(row_counts)):
        row_format += "{:<" + str(row_counts[i] + buf_count) + "}"

    # actually go through and format each row
    for row in columns:
        ret.append(row_format.format(*row))

    out(os.linesep.join(ret))


def prompt(question, choices=None):
    """echo a prompt to the user and wait for an answer

    question -- string -- the prompt for the user
    choices -- list -- if given, only exit when prompt matches one of the choices
    return -- string -- the answer that was given by the user
    """

    if not re.match("\s$", question):
        question = "{}: ".format(question)

    while True:
        if sys.version_info[0] > 2:
            answer = input(question)

        else:
            answer = raw_input(question)

        if not choices or answer in choices:
            break

    return answer

