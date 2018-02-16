# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os


QUIET_DEFAULT = os.environ.get("CAPTAIN_QUIET_DEFAULT", "D")
"""By default, it's just better to suppress debug logging, but you can manipulate
this value to whatever you want"""

