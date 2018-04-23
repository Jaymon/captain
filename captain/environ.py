# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os


QUIET_DEFAULT = os.environ.get("CAPTAIN_QUIET_DEFAULT", "D")
"""By default, this suppresses debug but you can manipulate this value to whatever
you want, this should be a string milar to what --quiet takes, the reason we suppress
DEBUG by default is because it will turn debug on for every logger in a default 
captain run (meaning you haven't configured any loggers separately) and so having
debug on by default can result in a lot of extraneous logging from installed modules"""

