import sys
import os
import fnmatch
import argparse

import captain
from captain.decorators import arg
from captain import echo


@arg("path", default=os.getcwd(), nargs='?', help="The path to scan for captain scripts")
@arg("-v", "--version", action='version', version="%(prog)s {}".format(captain.__version__))
def main(path):
    '''scan path directory and any subdirectories for valid captain scripts'''
    basepath = os.path.abspath(os.path.expanduser(str(path)))

    echo.h2("Available scripts in {}".format(basepath))
    echo.br()
    for root_dir, dirs, files in os.walk(basepath, topdown=True):
        for f in fnmatch.filter(files, '*.py'):
            try:
                filepath = os.path.join(root_dir, f)
                s = captain.Script(filepath)
                if s.can_run_from_cli():
                    rel_filepath = s.call_path(basepath)
                    for p in s.parsers():
                        subcommand = p.find_subcommand()
                        if subcommand:
                            echo.h3("{} {}", rel_filepath, subcommand)
                        else:
                            echo.h3(rel_filepath)

                        desc = p.description
                        if desc:
                            echo.quote(desc)

                        echo.br()

            except captain.ParseError:
                pass

captain.exit()

