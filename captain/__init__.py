"""
some other solutions I considered:
http://zacharyvoase.com/2009/12/09/django-boss/
https://github.com/zacharyvoase/django-boss
"""
import os
import argparse
import imp
import codecs
import re
import ast
import getopt
from collections import defaultdict
import inspect
import types
import sys

from . import echo
from . import decorators
from .exception import Error, ParseError


__version__ = '0.4.0'


def exit():
#     import sys
#     exc_info = sys.exc_info()
#     pout.v(exc_info)

    # TODO -- make this a classmethod of Script? 
    # TODO -- check to see if there is only 2 frames, error out if more than 2,
    # basically, we don't want to run if the module that called this was imported
    # from a module that wasn't __main__

    try:
        frame = inspect.stack()[1]
        calling_mod = inspect.getmodule(frame[0])
        main_mod = sys.modules.get("__main__", None)
        if main_mod:
            if calling_mod is main_mod:
                s = Script(inspect.getfile(calling_mod), module=calling_mod)
                raw_args = sys.argv[1:]
                ret_code = s.run(raw_args)
                sys.exit(ret_code)

    finally:
        del frame


class ScriptKwarg(object):

    @property
    def required(self):
        kwargs = self.parser_kwargs

        if 'required' in kwargs:
            ret = kwargs['required']
        else:
            try:
                self.default
            except ValueError:
                ret = True
            else:
                ret = False

        return ret

    @property
    def default(self):
        r = None
        r_found = False
        kwargs = self.parser_kwargs
        if 'default' in kwargs:
            r = kwargs['default']
            r_found = True

        else:
            if 'action' in kwargs:
                if kwargs['action'] == 'store_true':
                    r = False
                    r_found = True

                elif kwargs['action'] == 'store_false':
                    r = True
                    r_found = True

        if not r_found:
            raise ValueError('no default found')

        return r

    def __init__(self, arg_name, **kwargs):
        arg_name = arg_name.lstrip("-")
        self.name = arg_name

        self.parser_args = set()
        self.merge_args([
            '--{}'.format(arg_name),
            '--{}'.format(arg_name.replace('_', '-')),
            '--{}'.format(arg_name.replace('-', '_'))
        ])

        self.parser_kwargs = {}
        self.merge_kwargs(kwargs)

    def merge_args(self, args):
        if args:
            self.parser_args.update(set(args))

    def merge_kwargs(self, kwargs):
        """these kwargs come from the @arg decorator, they are then merged into any
        keyword arguments that were automatically generated from the main function
        introspection"""
        if kwargs:
            self.parser_kwargs.update(kwargs)

        self.parser_kwargs['dest'] = self.name

        # special handling of any passed in values
        if 'default' in kwargs:
            # NOTE -- this doesn't use .set_default() because that is meant to
            # parse from the function definition so it actually has different syntax
            # than what the .set_default() method does. eg, @arg("--foo", default=[1, 2]) means
            # that the default value should be an array with 1 and 2 in it, where main(foo=[1, 2])
            # means foo should be constrained to choices=[1, 2]
            self.parser_kwargs["default"] = kwargs["default"]
            self.parser_kwargs["required"] = False

        elif 'action' in kwargs:
            if kwargs['action'] in set(['store_false', 'store_true']):
                self.parser_kwargs['required'] = False

        else:
            self.parser_kwargs.setdefault("required", True)

    def merge_from_list(self, list_args):
        """find any matching parser_args from list_args and merge them into this
        instance

        list_args -- list -- an array of (args, kwargs) tuples
        """
        def xs(name, parser_args, list_args):
            """build the generator of matching list_args"""
            for args, kwargs in list_args:
                if len(set(args) & parser_args) > 0:
                    yield args, kwargs

                else:
                    if 'dest' in kwargs:
                        if kwargs['dest'] == name:
                            yield args, kwargs

        for args, kwargs in xs(self.name, self.parser_args, list_args):
            self.merge_args(args)
            self.merge_kwargs(kwargs)

    def set_default(self, na):
        """this is used for introspection from the main() method when there is an
        argument with a default value, this figures out how to set up the ArgParse
        arguments"""
        kwargs = {}
        if isinstance(na, (type, types.FunctionType)):
            # if foo=some_func then some_func(foo) will be ran if foo is passed in
            kwargs['type'] = na
            kwargs['required'] = True
            kwargs["default"] = argparse.SUPPRESS

        elif isinstance(na, bool):
            # if false then passing --foo will set to true, if True then --foo will
            # set foo to False
            kwargs['action'] = 'store_false' if na else 'store_true'
            kwargs['required'] = False

        elif isinstance(na, (int, float, str)):
            # for things like foo=int, this says that any value of foo is an integer
            kwargs['type'] = type(na)
            kwargs['default'] = na
            kwargs['required'] = False

        elif isinstance(na, (list, set)):
            # list is strange, [int] would mean we want a list of all integers, if
            # there is a value in the list: ["foo", "bar"] then it would mean only
            # those choices are valid
            na = list(na)
            kwargs['action'] = 'append'
            kwargs['required'] = True

            if len(na) > 0:
                if isinstance(na[0], type):
                    kwargs['type'] = na[0]

                else:
                    # we are now reverting this to a choices check
                    kwargs['action'] = 'store'
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

                    kwargs['choices'] = l
                    kwargs['type'] = ltype

        #self.merge_kwargs(kwargs)
        self.parser_kwargs.update(kwargs)


class ScriptArg(ScriptKwarg):
    def __init__(self, *args, **kwargs):
        super(ScriptArg, self).__init__(*args, **kwargs)
        self.parser_args = set([self.name])
        kwargs.setdefault("nargs", "?")
        self.merge_kwargs(kwargs)

    def merge_kwargs(self, kwargs):
        super(ScriptArg, self).merge_kwargs(kwargs)
        self.parser_kwargs.pop("dest")
        self.parser_kwargs.pop("required")


class ArgParser(argparse.ArgumentParser):
    def __init__(self, prog, callback):
        super(ArgParser, self).__init__(
            prog=prog,
            description=self.find_desc(callback),
            # https://hg.python.org/cpython/file/2.7/Lib/argparse.py
            # https://docs.python.org/2/library/argparse.html#formatter-class
            # http://stackoverflow.com/questions/12151306/argparse-way-to-include-default-values-in-help
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        self.callback = callback
        self.find_args()

    def find_desc(self, callback):
        desc = inspect.getdoc(callback)
        if not desc:
            if not inspect.isfunction(callback):
                cb_method = getattr(callback, '__call__', None)
                desc = inspect.getdoc(cb_method)

        if not desc: desc = ''
        return desc

    def find_args(self):
        arg_info = {
            'order': [],
            'required': [],
            'optional': {},
            'args': None,
            'kwargs': None
        }

        main = self.callback
        self.add_argument("--quiet", action='store_true', dest='quiet')

        all_arg_names = set()
        if inspect.isfunction(main):
            decorator_args = main.__dict__.get('decorator_args', [])
            args, args_name, kwargs_name, args_defaults = inspect.getargspec(main)
        else:
            decorator_args = main.__call__.__dict__.get('decorator_args', [])
            args, args_name, kwargs_name, args_defaults = inspect.getargspec(main.__call__)
            args = args[1:] # remove self which will always get passed in automatically

        if not args: args = []
        if not args_defaults: args_defaults = []
        arg_info['order'] = args
        default_offset = len(args) - len(args_defaults)
        #pout.v(args, args_name, kwargs_name, args_defaults, default_offset)

        for i, arg_name in enumerate(args):
            a = ScriptKwarg(arg_name)

            # set the default if it is available
            default_i = i - default_offset
            if default_i >= 0:
                na = args_defaults[default_i]
                a.set_default(na)

            a.merge_from_list(decorator_args)

            if a.required:
                arg_info['required'].append(a.name)

            else:
                arg_info['optional'][a.name] = a.default

            #pout.v(a.parser_args, a.parser_kwargs)
            all_arg_names |= a.parser_args
            self.add_argument(*a.parser_args, **a.parser_kwargs)

        if args_name:
            a = ScriptArg(args_name, nargs='*')
            a.merge_from_list(decorator_args)
            all_arg_names |= a.parser_args
            self.add_argument(*a.parser_args, **a.parser_kwargs)
            arg_info['args'] = args_name

        if kwargs_name:
            self.unknown_args = True
            arg_info['kwargs'] = kwargs_name

        else:
            self.unknown_args = False

        # pick up any stragglers
        for da, dkw in decorator_args:
            if da[0] not in all_arg_names:
                arg_name = da[0]
                if arg_name.startswith("-"):
                    a = ScriptKwarg(arg_name)
                else:
                    a = ScriptArg(arg_name)

                a.merge_kwargs(dkw)
                self.add_argument(*a.parser_args, **a.parser_kwargs)

        self.arg_info = arg_info


class Script(object):

    function_name = 'main'

    @property
    def default(self):
        cmd = None
        if self.function_name in self.callbacks:
            cmd = self.function_name

        return cmd

    @property
    def subcommands(self):
        cmds = []
        for function_name in self.callbacks:
            bits = function_name.split("_", 2)
            if len(bits) > 1:
                cmds.append(bits[1])
                #name = bits[1] if len(bits) > 1 else self.function_name

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
            with codecs.open(self.path, 'r', 'utf-8') as fp:
                self._body = fp.read()
        return self._body

#     @property
#     def callback(self):
#         try:
#             return self.callbacks[self.subcommand]
# 
#         except KeyError as e:
#             raise AttributeError("no callback {} found in script {}".format(
#                 self.subcommand,
#                 self.path
#             ))

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

#     def __call__(self, *args, **kwargs):
#         """this wraps around the script's function, it is functionally equivalent
#         to import the script and running function_name manually"""
# 
#         echo.quiet = kwargs.pop("quiet", False)
#         return self.callback(*args, **kwargs)

    def run(self, raw_args):
        """parse and import the script, and then run the script's main function"""

        # first we decide what command to run


        name = self.function_name
        subcommands = self.subcommands
        if subcommands:

            # TODO -- if no raw_args passed in and there contains subcommands, run default

            parser = argparse.ArgumentParser(description='Captain script', add_help=False)
            parser.add_argument(
                'command',
                metavar='COMMAND',
                nargs='?',
                choices=subcommands,
                help="The command you want to run"
            )

            args, raw_args = parser.parse_known_args(raw_args)
            name = "{}_{}".format(self.function_name, args.command)

        parser = self.parser(name)
        args = []
        kwargs = dict(parser.arg_info['optional'])

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
        for k in parser.arg_info['order']:
            args.append(kwargs.pop(k))

        # now that we have the correct order, tack the real *args on the end so they
        # get correctly placed into the function's *args variable
        if parser.arg_info['args']:
            args.extend(kwargs.pop(parser.arg_info['args']))

        #pout.v(parsed_args, args, kwargs, parser.arg_info)
        echo.quiet = kwargs.pop("quiet", False)
        return self.callbacks[name](*args, **kwargs)

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

    def parser(self, name=""):
        if not name: name = self.function_name
        parser_name = "parser_{}".format(name)
        parser = getattr(self, parser_name, None)
        if not parser:
            callback = self.callbacks[name]
            parser = ArgParser(self.name, callback)
            setattr(self, parser_name, parser)

        return parser

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
                ns = n.names[0]
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

        # TODO -- check for captain.exit() in the module
        # it might be better to have like a cli parse method that checks for captain.exit()

        self.parsed = True
        return len(self.callbacks) > 0


