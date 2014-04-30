"""
some other solutions I considered:
http://zacharyvoase.com/2009/12/09/django-boss/
https://github.com/zacharyvoase/django-boss
"""
import sys
import os
import argparse
import imp
import codecs
import re
import ast
import getopt
from collections import defaultdict
import fnmatch
import inspect
import types

from . import echo
from . import decorators


__version__ = '0.1.6'


class ScriptArg(object):

    @property
    def parser_args(self):
        args = set(self.args)
        for a in self.other_args:
            args |= set(a)

        return list(args)

    @property
    def parser_kwargs(self):
        kwargs = dict(self.kwargs)
        for kw in self.other_kwargs:
            kwargs.update(kw)

        return kwargs

    @property
    def names(self):
        return self.args + [self.name]

    @property
    def default(self):
        r = None
        r_found = False
        if 'default' in self.kwargs:
            r = self.kwargs['default']
            r_found = True

        else:
            if 'action' in self.kwargs:
                if self.kwargs['action'] == 'store_true':
                    r = False
                    r_found = True

                elif self.kwargs['action'] == 'store_false':
                    r = True
                    r_found = True

        if not r_found:
            raise ValueError('no default found')

        return r

    def __init__(self, arg_name):
        self.name = arg_name
        self.args = list(set([
            '--{}'.format(arg_name),
            '--{}'.format(arg_name.replace('_', '-'))
        ]))
        self.kwargs = {}

        self.other_args = []
        self.other_kwargs = []

        self.required = True

    def merge_from_list(self, list_args):
        # get decorator arguments lined up for merging with found information
        args = []
        kwargs = {}
        for an in self.names:
            try:
                for la, lkw in list_args:
                    if an in la:
                        args = list(la)
                        kwargs = lkw

                        # this is not a flag argument (eg, --foo) it is a positional
                        if an == self.name:
                            self.args = []

                        raise StopIteration()

            except StopIteration:
                break

        self.other_args.append(args)
        self.other_kwargs.append(kwargs)

    def set_default(self, na):
        if isinstance(na, (type, types.FunctionType)):
            self.kwargs['type'] = na
            self.kwargs['required'] = True

        elif isinstance(na, bool):
            self.kwargs['action'] = 'store_false' if na else 'store_true'
            self.required = False

        elif isinstance(na, (int, float, str)):
            self.kwargs['type'] = type(na)
            self.kwargs['default'] = na
            self.required = False

        elif isinstance(na, (list, set)):
            na = list(na)
            self.kwargs['action'] = 'append'
            self.kwargs['required'] = True

            if len(na) > 0:
                if isinstance(na[0], type):
                    self.kwargs['type'] = na[0]

                else:
                    # we are now reverting this to a choices check
                    self.kwargs['action'] = 'store'
                    l = set()
                    ltype = None
                    for elt in na:
                        vtype = type(elt)
                        l.add(elt)
                        if ltype is None:
                            ltype = vtype

                        else:
                            if ltype is not vtype:
                                ltype = str

                    self.kwargs['choices'] = l
                    self.kwargs['type'] = ltype


class Script(object):

    function_name = 'main'

    @property
    def description(self):
        self.parse()
        return self._description

    @property
    def parser(self):
        if hasattr(self, '_parser'): return self._parser

        arg_info = {
            'order': [],
            'required': [],
            'optional': {},
            'args': None,
            'kwargs': None
        }

        self.parse()
        m = self.module

        for name, func in inspect.getmembers(m, inspect.isfunction):
            if name == self.function_name:
                main = func
                break

        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description
        )

        all_arg_names = set()
        decorator_args = main.__dict__.get('decorator_args', [])
        args, args_name, kwargs_name, args_defaults = inspect.getargspec(main)
        if not args: args = []
        if not args_defaults: args_defaults = []
        arg_info['order'] = args
        default_offset = len(args) - len(args_defaults)
        #pout.v(args, args_name, kwargs_name, args_defaults, default_offset)

        for i, arg_name in enumerate(args):
            a = ScriptArg(arg_name)
            a.merge_from_list(decorator_args)

            default_i = i - default_offset
            if default_i >= 0:
                na = args_defaults[default_i]
                a.set_default(na)

            if a.required:
                arg_info['required'].append(a.name)

            else:
                arg_info['optional'][a.name] = a.default

            #pout.v(a.parser_args, a.parser_kwargs)
            parser_args = a.parser_args
            all_arg_names |= set(parser_args)
            parser.add_argument(*parser_args, **a.parser_kwargs)

        if args_name:
            parser.add_argument(args_name, nargs='*')
            arg_info['args'] = args_name

        if kwargs_name:
            parser.unknown_args = True
            arg_info['kwargs'] = kwargs_name

        else:
            parser.unknown_args = False

        # pick up any stragglers
        for da, dkw in decorator_args:
            if da[0] not in all_arg_names:
                parser.add_argument(*da, **dkw)

        self._parser = parser
        self.arg_info = arg_info
        return self._parser

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def module(self):
        """load the module so we can actually run the script's function"""
        # http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
        module = imp.load_source('captain_script', self.path)
        return module

    @property
    def body(self):
        """get the contents of the script"""
        if not hasattr(self, '_body'):
            with codecs.open(self.path, 'r+', 'utf-8') as fp:
                self._body = fp.read()
        return self._body

    def __init__(self, script_path):
        self.parsed = False
        self.path = self.normalize_path(script_path)

    def normalize_path(self, path):
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

    def __call__(self, *args, **kwargs):
        """this wraps around the script's function, it is functionally equivalent
        to import the script and running function_name manually"""
        module = self.module
        return getattr(module, self.function_name)(*args, **kwargs)

    def run(self, raw_args):
        """parse and import the script, and then run the script's main function"""
        parser = self.parser
        args = []
        kwargs = dict(self.arg_info['optional'])

        parsed_args = []
        if parser.unknown_args:
            parsed_args, parsed_unknown_args = parser.parse_known_args(raw_args)

            # **kwargs have to be in --key=val form
            # http://stackoverflow.com/a/12807809/5006
            d = defaultdict(list)
            for k, v in ((k.lstrip('-'), v) for k,v in (a.split('=') for a in parsed_unknown_args)):
                d[k].append(v)

            for k in (k for k in d if len(d[k])==1):
                d[k] = d[k][0]

            kwargs.update(d)

        else:
            parsed_args = parser.parse_args(raw_args)

        # http://parezcoydigo.wordpress.com/2012/08/04/from-argparse-to-dictionary-in-python-2-7/
        kwargs.update(vars(parsed_args))

        # because of how args works, we need to make sure the kwargs are put in correct
        # order to be passed to the function, otherwise our real *args won't make it
        # to the *args variable
        for k in self.arg_info['order']:
            args.append(kwargs.pop(k))

        # now that we have the correct order, tack the real *args on the end so they
        # get correctly placed into the function's *args variable
        if self.arg_info['args']:
            args.extend(kwargs.pop(self.arg_info['args']))

        #pout.v(parsed_args, args, kwargs, self.arg_info)
        return self(*args, **kwargs)

    def is_cli(self):
        """return True if this is an actual cli script"""
        ret = True
        try:
            self.parse()
        except ValueError, e:
            ret = False

        return ret

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
        """load the script and set the parser and argument info"""
        if self.parsed: return

        # http://stackoverflow.com/questions/17846908/proper-shebang-for-python-script
        body = self.body
        if not re.match("^#!.*?python.*$", body, re.I | re.MULTILINE):
            raise ValueError(
                "no shebang! Please add this as first line: #!/usr/bin/env python"
            )

        found_main = False
        ast_tree = ast.parse(self.body, self.path)
        for n in ast.walk(ast_tree):
            if isinstance(n, ast.FunctionDef):
                if n.name == self.function_name:
                    found_main = True
                    self._description = ''
                    if n.body:
                        doc = n.body[0]
                        if isinstance(doc, ast.Expr) and isinstance(doc.value, ast.Str):
                            self._description = doc.value.s

        if not found_main:
            raise ValueError("no main function found")

        self.parsed = True


def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Command line script running', add_help=False)
    #parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("-v", "--version", action='version', version="%(prog)s {}".format(__version__))
    parser.add_argument("--quiet", action='store_true', dest='quiet')
    #parser.add_argument('args', nargs=argparse.REMAINDER, help='all other arguments')
    parser.add_argument('script', metavar='SCRIPT', nargs='?', help='The script you want to run')

    args, command_args = parser.parse_known_args()

    echo.quiet = args.quiet

    ret_code = 0

    if args.script:
        s = Script(args.script)
        ret_code = s.run(command_args)

    else:
        basepath = os.getcwd()
        print "Available scripts in {}:".format(basepath)
        for root_dir, dirs, files in os.walk(basepath, topdown=True):
            for f in fnmatch.filter(files, '*.py'):
                filepath = os.path.join(root_dir, f)
                s = Script(filepath)
                if s.is_cli():
                    rel_filepath = s.call_path(basepath)
                    print "\t{}".format(rel_filepath)
                    desc = s.description
                    if desc:
                        for l in desc.split("\n"):
                            print "\t\t{}".format(l)

                    print ""

    return ret_code

