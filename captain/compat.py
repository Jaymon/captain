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

    import itertools
    zip = itertools.izip

    # NOTE -- getargspace isn't a full mapping of getfullargspec
    from inspect import getargspec as getfullargspec


elif is_py3:
    basestring = (str, bytes)
    unicode = str

    from inspect import getfullargspec

