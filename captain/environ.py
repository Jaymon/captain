# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os


QUIET_DEFAULT = os.environ.get("CAPTAIN_QUIET_DEFAULT", "")
"""This should be a string milar to what --quiet takes"""


WIDTH = 70
"""lots of output functions are width constrained, this is the global width they default to"""

