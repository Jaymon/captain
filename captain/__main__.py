import sys
import os
import fnmatch
import argparse

import captain


def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Command line script running', add_help=False)
    #parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("-v", "--version", action='version', version="%(prog)s {}".format(captain.__version__))
    parser.add_argument("--quiet", action='store_true', dest='quiet')
    #parser.add_argument('args', nargs=argparse.REMAINDER, help='all other arguments')
    parser.add_argument('script', metavar='SCRIPT', nargs='?', help='The script you want to run')

    args, command_args = parser.parse_known_args()

    captain.echo.quiet = args.quiet

    ret_code = 0

    if args.script:

        # set up the path, basically, python does different things depending on how a script
        # is called from the command line:
        #   1)  python -m path.to.module -- this would add the current working directory to
        #       the path, basically ""
        #
        #   2)  python path/to/module.py -- this would include the directory that contains
        #       the script, so "path/to"
        #
        # because either could be expected, we're going to do them both
        path_2 = os.path.abspath(os.path.expanduser(os.path.dirname(args.script)))
        sys.path.insert(0, path_2)
        path_1 = ""
        sys.path.insert(0, path_1)

        s = captain.Script(args.script)
        try:
            ret_code = s.run(command_args)
            if not ret_code:
                ret_code = 0

        except Exception as e:
            captain.echo.exception(e)
            ret_code = 1

    else:
        basepath = os.getcwd()
        captain.echo.out("Available scripts in {}:".format(basepath))
        for root_dir, dirs, files in os.walk(basepath, topdown=True):
            for f in fnmatch.filter(files, '*.py'):
                filepath = os.path.join(root_dir, f)
                s = captain.Script(filepath)
                if s.is_cli():
                    rel_filepath = s.call_path(basepath)
                    captain.echo.out("\t{}".format(rel_filepath))
                    desc = s.description
                    if desc:
                        for l in desc.split("\n"):
                            print "\t\t{}".format(l)

                    print ""

    return ret_code


sys.exit(console())

