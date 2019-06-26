# -*- coding: utf-8 -*-

import sys

# Syntax sugar.
_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py2:
    basestring = basestring
    unicode = unicode
    range = xrange # range is now always an iterator
    input = raw_input

    import itertools
    zip = itertools.izip

    # NOTE -- getargspace isn't a full mapping of getfullargspec
    from inspect import getargspec as getfullargspec

    from collections import Iterable, Mapping
    import __builtin__ as builtins


elif is_py3:
    basestring = (str, bytes)
    unicode = str
    input = input

    from inspect import getfullargspec

    from collections.abc import Iterable, Mapping
    import builtins

