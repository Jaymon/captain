"""
This is handy for captain scripts to be able to route their prints through and it
will obey the passed in --quiet commmand line argument automatically
"""

import sys
import logging

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

quiet = True


def exception(e):
    '''print an exception message to stderr (this does not honor quiet)'''
    stderr.exception(e)


def err(format_msg, *args, **kwargs):
    '''print format_msg to stderr'''
    global quiet
    if quiet: return

    stderr.info(format_msg.format(*args, **kwargs))


def out(format_msg, *args, **kwargs):
    '''print format_msg to stdout, taking into account verbosity level'''
    global quiet
    if quiet: return

    if isinstance(format_msg, basestring):
        stdout.info(format_msg.format(*args, **kwargs))

    else:
        stdout.info(str(format_msg))


def bar(sep='-', count=80):
    out(sep * count)


def blank(count=1):
    """print out a blank newline"""
    for x in xrange(count):
        out('')


def banner(*lines, **kwargs):
    """prints a banner

    sep -- string -- the character that will be on the line on the top and bottom
        and before any of the lines, defaults to *
    count -- integer -- the line width, defaults to 80
    """
    sep = kwargs.get("sep", "*")
    count = kwargs.get("count", 80)

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
            c = String(c)
            cl = len(c) 
            if cl > row_counts[i]:
                row_counts[i] = cl

    for rows in itertools.izip(*columns):
        row = [prefix]
        for i, c in enumerate(rows):
            c = String(c)
            row.append("{}{}".format(c, " " * ((row_counts[i] + buf_count) - len(c))))

        ret.append("".join(row).rstrip())

    out(os.linesep.join(ret))

