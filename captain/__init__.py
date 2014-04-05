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


__version__ = '0.1.4'


def arg(*parser_args, **parser_kwargs):
    def wrap(main):
        main.__dict__.setdefault('decorator_args', [])
        main.__dict__['decorator_args'].append((parser_args, parser_kwargs))
        return main

    return wrap 

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

        decorator_args = main.__dict__.get('decorator_args', [])
        args, args_name, kwargs_name, args_defaults = inspect.getargspec(main)
        arg_info['order'] = args
        default_offset = len(args) - len(args_defaults)
        #pout.v(args, args_name, kwargs_name, args_defaults, default_offset)

        for i, arg_name in enumerate(args):
            arg_args = list(set([
                '--{}'.format(arg_name),
                '--{}'.format(arg_name.replace('_', '-'))
            ]))
            arg_kwargs = {}

            # get decorator arguments lined up for merging with found information
            decorator_arg_args = []
            decorator_kwargs = {}
            arg_names = arg_args + [arg_name]
            for an in arg_names:
                for da, dkw in decorator_args:
                    if an in da:
                        decorator_arg_args = list(da)
                        decorator_kwargs = dkw

                        # this is not a flag argument (eg, --foo) it is a positional
                        if an == arg_name:
                            arg_args = []

            default_i = i - default_offset
            if default_i >= 0:
                na = args_defaults[default_i]
                if isinstance(na, (type, types.FunctionType)):
                    arg_kwargs['type'] = na
                    arg_kwargs['required'] = True

                elif isinstance(na, bool):
                    arg_kwargs['action'] = 'store_false' if na else 'store_true'
                    arg_info['optional'][arg_name] = na

                elif isinstance(na, (int, float, str)):
                    arg_kwargs['type'] = type(na)
                    arg_kwargs['default'] = na

                elif isinstance(na, (list, set)):
                    na = list(na)
                    arg_kwargs['action'] = 'append'
                    arg_kwargs['required'] = True

                    if len(na) > 0:
                        if isinstance(na[0], type):
                            arg_kwargs['type'] = na[0]

                        else:
                            # we are now reverting this to a choices check
                            arg_kwargs['action'] = 'store'
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

                            arg_kwargs['choices'] = l
                            arg_kwargs['type'] = ltype

            else:
                arg_kwargs['required'] = True

            if 'required' in arg_kwargs:
                arg_info['required'].append(arg_name)
            elif 'default' in arg_kwargs:
                arg_info['optional'][arg_name] = arg_kwargs['default']

            #pout.v(arg_args, arg_kwargs, decorator_arg_args, decorator_kwargs)

            # merge decorator arguments, decorator takes precedence
            arg_args = list(set(arg_args + decorator_arg_args))
            arg_kwargs.update(decorator_kwargs)

            parser.add_argument(*arg_args, **arg_kwargs)

        if args_name:
            parser.add_argument(args_name, nargs='*')
            arg_info['args'] = args_name

        if kwargs_name:
            parser.unknown_args = True
            arg_info['kwargs'] = kwargs_name
        else:
            parser.unknown_args = False

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

