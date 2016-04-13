"""
This is handy for captain scripts to be able to route their prints through and it
will obey the passed in --quiet commmand line argument automatically
"""

import sys
import logging
import textwrap
import itertools
import os
import re
from contextlib import contextmanager


# configure loggers
log_formatter = logging.Formatter('%(message)s')

stdout = logging.getLogger('{}.stdout'.format(__name__))
if len(stdout.handlers) == 0:
    stdout.propagate = False
    stdout.setLevel(logging.DEBUG)
    log_handler = logging.StreamHandler(stream=sys.stdout)
    log_handler.setFormatter(log_formatter)
    stdout.addHandler(log_handler)

stderr = logging.getLogger('{}.stderr'.format(__name__))
if len(stderr.handlers) == 0:
    # we want to propogate error messages up through the chain, this allows us to
    # do things like attach a logging handler that will do more important things
    # with exceptions and the like
    stderr.propagate = True 
    stderr.setLevel(logging.DEBUG)
    log_handler = logging.StreamHandler(stream=sys.stderr)
    log_handler.setFormatter(log_formatter)
    stderr.addHandler(log_handler)


quiet = False
"""set this to True to suppress stdout output, stderr will not be affected"""


debug = False
"""set this to true to make verbose function print output"""


width = 80
"""lots of the functions are width constrained, this is the global width they default to"""


class Progress(object):
    def __init__(self, stream, length, quiet, **kwargs):
        self.length = length
        self.stream = stream
        self.quiet = quiet

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
        if self.quiet: return
        bar = self.get_progress(current)
        self.stream.write(bar + chr(8) * (len(bar) + 1))
        self.stream.flush()


class ProgressBar(Progress):
    def __init__(self, stream, length, width, quiet):
        super(ProgressBar, self).__init__(stream, length, quiet)
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
    global quiet
    progress_class = kwargs.pop("progress_class", Progress)
    kwargs["stream"] = sys.stdout
    kwargs["width"] = kwargs.get("width", globals()["width"])
    kwargs["length"] = length
    kwargs["quiet"] = quiet
    pbar = progress_class(**kwargs)
    pbar.update(0)
    yield pbar
    pbar.update(length)
    pbar.stream.write("\n")


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
    stderr.info(str(format_msg).format(*args, **kwargs), exc_info=exc_info)


def ch(c):
    """print one or more characters without a newline at the end, while this does
    respect --quiet, it does not use the stdout logger, that's because the loggers
    automatically add the newline and there's nothing I can easily do about it.

    example --
        for x in range(1000):
            echo.ch(".")

    c -- string -- the chars that will be output
    """
    global quiet
    if quiet: return
    # http://stackoverflow.com/questions/493386/how-to-print-in-python-without-newline-or-space
    sys.stdout.write(c)
    sys.stdout.flush()

def out(format_msg="", *args, **kwargs):
    '''print format_msg to stdout, taking into account --quiet setting'''
    global quiet
    if quiet: return

    if format_msg != "":
        if isinstance(format_msg, basestring):
            s = format_msg.format(*args, **kwargs)
            stdout.info(s)
#             width = globals()["width"]
#             s = textwrap.fill(s, width=width)
#             stdout.info(s)

        else:
            stdout.info(str(format_msg))

    else:
        stdout.info("")


def verbose(format_msg="", *args, **kwargs):
    '''print format_msg to stdout, taking into account --verbose flag'''
    global debug
    if not debug: return
    out(format_msg, *args, **kwargs)


def hr(width=0):
    """similar to the html horizontal rule in html"""
    if not width: width = globals()["width"]
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
    wrapper.width = globals()["width"]
    wrapper.initial_indent = "* "
    wrapper.subsequent_indent = "* "
    if args or kwargs:
        h = wrapper.fill(format_msg.format(*args, **kwargs))
    else:
        h = wrapper.fill(format_msg)

    out(h)


def blank(count=1): br(count) # DEPRECATED - 2-27-16 - use br
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
    width = globals()["width"]
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
    if not width: width = globals()["width"]
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
    count = kwargs.get("width", globals()["width"])

    out(sep * count)
    if lines:
        out(sep)

        for line in lines:
            out("{} {}".format(sep, line))

        out(sep)
        out(sep * count)


def columns(*columns, **kwargs):
    """
    format columned data so we can easily print it out on a console, this just takes
    columns of data and it will format it into properly aligned columns, it's not
    fancy, but it works for most type of strings that I need it for, like server name
    lists.

    other formatting options:
        http://stackoverflow.com/a/8234511/5006

    *columns -- each column is a list of values you want in each row of the column
    **kwargs --
        prefix -- string -- what you want before each row (eg, a tab)
        buf_count -- integer -- how many spaces between longest col value and its neighbor

    return -- string
    """
    ret = []
    prefix = kwargs.get('prefix', '')
    buf_count = kwargs.get('buf_count', 2)
    row_counts = [0] * len(columns)

    for rows in itertools.izip(*columns):
        for i, c in enumerate(rows):
            cl = len(c) 
            if cl > row_counts[i]:
                row_counts[i] = cl

    for rows in itertools.izip(*columns):
        row = [prefix]
        for i, c in enumerate(rows):
            row.append("{}{}".format(c, " " * ((row_counts[i] + buf_count) - len(c))))

        ret.append("".join(row).rstrip())

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
            answer = input("{}: ".format(question))

        else:
            answer = raw_input("{}: ".format(question))

        if not choices or answer in choices:
            break

    return answer

