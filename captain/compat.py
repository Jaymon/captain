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
    zip_longest = itertools.izip_longest

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
    from itertools import zip_longest


Str = unicode if is_py2 else str
Bytes = str if is_py2 else bytes


class ByteString(Bytes):
    """Wrapper around a byte string b"" to make sure we have a byte string that
    will work across python versions and handle the most annoying encoding issues
    automatically
    :Example:
        # python 3
        s = ByteString("foo)
        str(s) # calls __str__ and returns self.unicode()
        unicode(s) # errors out
        bytes(s) # calls __bytes__ and returns ByteString
        # python 2
        s = ByteString("foo)
        str(s) # calls __str__ and returns ByteString
        unicode(s) # calls __unicode__ and returns String
        bytes(s) # calls __str__ and returns ByteString
    """
    def __new__(cls, val=b"", encoding=""):
        if isinstance(val, type(None)): return None

        if not encoding:
            encoding = sys.getdefaultencoding()

        if not isinstance(val, (bytes, bytearray)):
            if is_py2:
                val = unicode(val)
            else:
                val = str(val)
            #val = val.__str__()
            val = bytearray(val, encoding)

        instance = super(ByteString, cls).__new__(cls, val)
        instance.encoding = encoding
        return instance

    def __str__(self):
        return self if is_py2 else self.unicode()

    def unicode(self):
        s = self.decode(self.encoding)
        return String(s)
    __unicode__ = unicode

    def bytes(self):
        return self
    __bytes__ = bytes

    def raw(self):
        """because sometimes you need a vanilla bytes()"""
        return b"" + self


class String(Str):
    """Wrapper around a unicode string "" to make sure we have a unicode string that
    will work across python versions and handle the most annoying encoding issues
    automatically
    :Example:
        # python 3
        s = String("foo)
        str(s) # calls __str__ and returns String
        unicode(s) # errors out
        bytes(s) # calls __bytes__ and returns ByteString
        # python 2
        s = String("foo)
        str(s) # calls __str__ and returns ByteString
        unicode(s) # calls __unicode__ and returns String
        bytes(s) # calls __str__ and returns ByteString
    """
    def __new__(cls, val="", encoding=""):
        if isinstance(val, type(None)): return None

        if not encoding:
            encoding = sys.getdefaultencoding()

        if not isinstance(val, Str):
            val = ByteString(val, encoding).unicode()

        instance = super(String, cls).__new__(cls, val)
        instance.encoding = encoding
        return instance

    def __str__(self):
        return self.bytes() if is_py2 else self

    def unicode(self):
        return self
    __unicode__ = unicode

    def bytes(self):
        s = self.encode(self.encoding)
        return ByteString(s)
    __bytes__ = bytes

    def raw(self):
        """because sometimes you need a vanilla str() (or unicode() in py2)"""
        return "" + self

