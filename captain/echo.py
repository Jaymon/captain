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
    stderr.propagate = False
    stderr.setLevel(logging.DEBUG)
    log_handler = logging.StreamHandler(stream=sys.stderr)
    log_handler.setFormatter(log_formatter)
    stderr.addHandler(log_handler)

quiet = True

def exception(e):
    '''print an exception message to stderr'''
    global quiet
    if quiet: return

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

#def console_out(format_str, *args, **kwargs):
#    sys.stderr.write(format_str.format(*args, **kwargs))
#    sys.stderr.write(os.linesep)
#
#def console_debug(*args, **kwargs):
#    if debug:
#        console_out(*args, **kwargs)
#
