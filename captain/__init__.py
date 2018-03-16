# -*- coding: utf-8 -*-
"""
some other solutions I considered:
http://zacharyvoase.com/2009/12/09/django-boss/
https://github.com/zacharyvoase/django-boss
"""
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import imp
import re
import ast
import inspect
import sys
import collections

from . import echo
from . import decorators
from .exception import Error, ParseError, ArgError
from .compat import *
from .parse import ArgParser, Parser


__version__ = '2.0.1'


def discover_if_calling_mod():
    calling_mod = None
    try:
        # http://stackoverflow.com/a/1095621/5006
        stack = inspect.stack()
        frame = stack[2]
        main_mod = sys.modules.get("__main__", None)
        if main_mod:

            mod = inspect.getmodule(frame[0])
            if mod is not main_mod:
                for f in stack[2:]:
                    fm = inspect.getmodule(f[0])
                    if fm is not mod:
                        mod = fm
                        frame = f
                        break

#             pout.b()
#             for f in stack:
#                 pout.v(inspect.getmodule(f[0]).__name__, f[4][0].strip())

            # now we have found what should be the __main__ mod, we bail if it isn't
            if mod is main_mod:
                loc = frame[4][0].strip()

                if not re.match("import\s+", loc, re.I):

                    # this might be more portable
                    # sys._getframe().f_back.f_code.co_name
                    # http://stackoverflow.com/questions/2654113/

                    m = re.match("load_entry_point\(([^\)]+)\)", loc)
                    if m:
                        # we are using a setup.py defined console_scripts entry point

                        dist, group, name = m.group(1).split("', ")
                        from pkg_resources import get_distribution

                        ep = get_distribution(dist.strip("'")).get_entry_info(
                            group.strip("'"),
                            name.strip("'")
                        )
                        calling_mod = sys.modules[ep.module_name]

                    else:
                        # we called captain from a normal python script in a directory
                        # either defined through setup.py "scripts" in a package or just
                        # some script
                        calling_mod = mod

    finally:
        del frame

    return calling_mod


def exit(mod_name=""):
    """A stand-in for the normal sys.exit()

    all the magic happens here, when this is called at the end of a script it will
    figure out all the available commands and arguments that can be passed in,
    then handle exiting the script and returning the status code. 

    :Example:

        from captain import exit
        exit(__name__)

    This also acts as a guard against the script being traditionally imported, so
    even if you have this at the end of the script, it won't actually exit if the
    script is traditionally imported
    """
    if mod_name and mod_name == "__main__":
        calling_mod = sys.modules.get("__main__", None)

    else:
        calling_mod = discover_if_calling_mod()

    if calling_mod:
        s = Script(inspect.getfile(calling_mod), module=calling_mod)
        raw_args = sys.argv[1:]
        ret_code = s.run(raw_args)
        sys.exit(ret_code)


class Script(object):

    function_name = 'main'

    @property
    def parser(self):
        """return the parser for the current name"""
        module = self.module

        subcommands = self.subcommands
        if subcommands:
            module_desc = inspect.getdoc(module)
            parser = Parser(description=module_desc, module=module)
            subparsers = parser.add_subparsers()

            for sc_name, callback in subcommands.items():
                sc_name = sc_name.replace("_", "-")
                cb_desc = inspect.getdoc(callback)
                sc_parser = subparsers.add_parser(
                    sc_name,
                    callback=callback,
                    help=cb_desc
                )

        else:
            parser = Parser(callback=self.callbacks[self.function_name], module=module)

        return parser

    @property
    def default(self):
        cmd = None
        if self.function_name in self.callbacks:
            cmd = self.function_name

        return cmd

    @property
    def subcommands(self):
        cmds = {}
        for function_name, callback in self.callbacks.items():
            bits = function_name.split("_", 1)
            if len(bits) > 1:
                cmds[bits[1]] = callback

        return cmds

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def module_name(self):
        name, ext = os.path.splitext(self.name)
        return name

    @property
    def module(self):
        """load the module so we can actually run the script's function"""
        # we have to guard this value because:
        # https://thingspython.wordpress.com/2010/09/27/another-super-wrinkle-raising-typeerror/
        if not hasattr(self, '_module'):
            if "__main__" in sys.modules:
                mod = sys.modules["__main__"]
                path = self.normalize_path(mod.__file__)
                if os.path.splitext(path) == os.path.splitext(self.path):
                    self._module = mod

                else:
                    # http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
                    self._module = imp.load_source('captain_script', self.path)
                    #self._module = imp.load_source(self.module_name, self.path)

        return self._module

    @property
    def body(self):
        """get the contents of the script"""
        if not hasattr(self, '_body'):
            self._body = inspect.getsource(self.module)
        return self._body

    def __init__(self, script_path, module=None):
        self.parsed = False
        self.path = self.normalize_path(script_path)
        if module:
            self._module = module
        self.parse()

    @classmethod
    def normalize_path(cls, path):
        path = os.path.abspath(os.path.expanduser(str(path)))
        is_valid = True
        if not os.path.isfile(path):
            is_valid = False
            if os.path.isdir(path):
                for basename in ['__main__.py', '__init__.py']:
                    filepath = os.path.join(path, basename)
                    if os.path.isfile(filepath):
                        path = filepath
                        is_valid = True

        if not is_valid:
            raise IOError("{} does not exist".format(path))

        return path

    def run(self, raw_args):
        """parse and import the script, and then run the script's main function"""
        parser = self.parser
        args, kwargs = parser.parse_callback_args(raw_args)

        #pout.v(args, kwargs)
        callback = kwargs.pop("main_callback")
        levels = kwargs.pop("quiet", "")
        logging.inject_quiet(levels)

        try:
            ret_code = callback(*args, **kwargs)
            ret_code = int(ret_code) if ret_code else 0

        except ArgError as e:
            # https://hg.python.org/cpython/file/2.7/Lib/argparse.py#l2374
            echo.err("{}: error: {}", parser.prog, str(e))
            ret_code = 2

        return ret_code

    def call_path(self, basepath):
        """return that path to be able to call this script from the passed in
        basename

        example -- 
            basepath = /foo/bar
            self.path = /foo/bar/che/baz.py
            self.call_path(basepath) # che/baz.py

        basepath -- string -- the directory you would be calling this script in
        return -- string -- the minimum path that you could use to execute this script
            in basepath
        """
        rel_filepath = self.path
        if basepath:
            rel_filepath = os.path.relpath(self.path, basepath)

        basename = self.name
        if basename in set(['__init__.py', '__main__.py']):
            rel_filepath = os.path.dirname(rel_filepath)

        return rel_filepath

    def parse(self):
        """load the script and set the parser and argument info

        I feel that this is way too brittle to be used long term, I think it just
        might be best to import the stupid module, the thing I don't like about that
        is then we import basically everything, which seems bad?
        """
        if self.parsed: return

        self.callbacks = {}

        # search for main and any main_* callable objects
        regex = re.compile("^{}_?".format(self.function_name), flags=re.I)
        mains = set()
        body = self.body
        ast_tree = ast.parse(self.body, self.path)
        for n in ast_tree.body:
            if hasattr(n, 'name'):
                if regex.match(n.name):
                    mains.add(n.name)

            if hasattr(n, 'value'):
                ns = n.value
                if hasattr(ns, 'id'):
                    if regex.match(ns.id):
                        mains.add(ns.id)

            if hasattr(n, 'targets'):
                ns = n.targets[0]
                if hasattr(ns, 'id'):
                    if regex.match(ns.id):
                        mains.add(ns.id)

            if hasattr(n, 'names'):
                for ns in n.names:
                    if hasattr(ns, 'name'):
                        if regex.match(ns.name):
                            mains.add(ns.name)

                    if getattr(ns, 'asname', None):
                        if regex.match(ns.asname):
                            mains.add(ns.asname)

        if len(mains) > 0:
            module = self.module
            for function_name in mains:
                cb = getattr(module, function_name, None)
                if cb and callable(cb):
                    self.callbacks[function_name] = cb

        else:
            raise ParseError("no main function found")

        self.parsed = True
        return len(self.callbacks) > 0

    def can_run_from_cli(self):
        """return True if this script can be run from the command line"""
        ret = False
        ast_tree = ast.parse(self.body, self.path)
        calls = self._find_calls(ast_tree, __name__, "exit")
        for call in calls:
            if re.search("{}\(".format(re.escape(call)), self.body):
                ret = True
                break

        return ret

    def _find_calls(self, ast_tree, called_module, called_func):
        '''
        scan the abstract source tree looking for possible ways to call the called_module
        and called_func

        borrowed from pout

        ast_tree -- _ast.* instance -- the internal ast object that is being checked, returned from compile()
            with ast.PyCF_ONLY_AST flag
        called_module -- string -- we are checking the ast for imports of this module
        called_func -- string -- we are checking the ast for aliases of this function
        return -- set -- the list of possible calls the ast_tree could make to call the called_func
        ''' 
        s = set()

        # always add the default call, the set will make sure there are no dupes...
        s.add("{}.{}".format(called_module, called_func))

        if hasattr(ast_tree, 'body'):
            # further down the rabbit hole we go
            if isinstance(ast_tree.body, collections.Iterable):
                for ast_body in ast_tree.body:
                    s.update(self._find_calls(ast_body, called_module, called_func))

        elif hasattr(ast_tree, 'names'):
            # base case
            if hasattr(ast_tree, 'module'):
                # we are in a from ... import ... statement
                if ast_tree.module == called_module:
                    for ast_name in ast_tree.names:
                        if ast_name.name == called_func:
                            s.add(unicode(ast_name.asname if ast_name.asname is not None else ast_name.name))

            else:
                # we are in a import ... statement
                for ast_name in ast_tree.names:
                    if hasattr(ast_name, 'name') and (ast_name.name == called_module):
                        call = "{}.{}".format(
                            ast_name.asname if ast_name.asname is not None else ast_name.name,
                            called_func
                        )
                        s.add(call)

        return s


