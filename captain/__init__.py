"""
some other solutions I considered:
http://zacharyvoase.com/2009/12/09/django-boss/
https://github.com/zacharyvoase/django-boss
"""
import os
import argparse
import imp
#import codecs
import re
import ast
import getopt
from collections import defaultdict
import inspect
import types
import sys
import collections

from . import echo
from . import decorators
from .exception import Error, ParseError, ArgError


__version__ = '0.4.9'


def exit():
    """A stand-in for the normal sys.exit()

    all the magic happens here, when this is called at the end of a script it will
    figure out all the available commands and arguments that can be passed in,
    then handle exiting the script and returning the status code. 

    This also acts as a guard against the script being traditionally imported, so
    even if you have this at the end of the script, it won't actually exit if the
    script is traditionally imported
    """
    try:
        # http://stackoverflow.com/a/1095621/5006
        stack = inspect.stack()
        frame = stack[1]
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
                    # http://stackoverflow.com/questions/2654113/python-how-to-get-the-callers-method-name-in-the-called-method

                    m = re.match("load_entry_point\(([^\)]+)\)", loc)
                    if m:
                        # we are using a setup.py defined console_scripts entry point

                        dist, group, name = m.group(1).split("', ")
                        from pkg_resources import get_distribution

                        ep = get_distribution(dist.strip("'")).get_entry_info(group.strip("'"), name.strip("'"))
                        calling_mod = sys.modules[ep.module_name]

                    else:
                        # we called captain from a normal python script in a directory
                        # either defined through setup.py "scripts" in a package or just
                        # some script
                        calling_mod = mod

                    if calling_mod:
                        s = Script(inspect.getfile(calling_mod), module=calling_mod)
                        raw_args = sys.argv[1:]
                        ret_code = s.run(raw_args)
                        sys.exit(ret_code)

    finally:
        del frame


class CallbackInspect(object):
    """Provides some handy helper introspection methods for dealing with the command
    callback function/method

    for the most part, the main command can either be a function or a class instance
    with a __call__, but when inheriting args (using the @args decorator) there are
    actually 2 other types: method and uninstantiated class, this makes sure when
    data is being pulled out of the callback it uses the proper function/method that
    will actually be called when the callback is ran
    """
    @property
    def args(self):
        args = self.get('decorator_args', [])
        return args

    @property
    def inherit_args(self):
        args = self.get('inherit_args', [])
        return args

    @property
    def desc(self):
        desc = inspect.getdoc(self.callback)
        if not desc:
            cb_method = self.callable
            desc = inspect.getdoc(cb_method)
        if not desc: desc = ''
        return desc

    @property
    def callable(self):
        if self.is_instance():
            ret = self.callback.__call__
        elif self.is_class():
            #ret = self.callback.__init__
            ret = self.callback.__call__
        else:
            ret = self.callback
        return ret

    @property
    def argspec(self):
        args, args_name, kwargs_name, args_defaults = inspect.getargspec(self.callable)
        if self.is_instance() or self.is_class():
            args = args[1:] # remove self which will always get passed in automatically

        if not args: args = []
        if not args_defaults: args_defaults = []
        return args, args_name, kwargs_name, args_defaults

    def __init__(self, callback):
        self.callback = callback

    def is_class(self):
        return isinstance(self.callback, type)

    def is_instance(self):
        """return True if callback is an instance of a class"""
        val = self.callback
        if self.is_class(): return False
        return isinstance(val, types.InstanceType) or hasattr(val, '__dict__') \
            and not (hasattr(val, 'func_name') or hasattr(val, 'im_func'))

    def is_function(self):
        """return True if callback is a vanilla plain jane function"""
        if self.is_instance() or self.is_class(): return False
        return isinstance(self.callback, (collections.Callable, classmethod))

    def get(self, key, default_val=None):
        if self.is_instance():
            ret = self.callback.__call__.__dict__.get(key, default_val)
        elif self.is_class():
            #ret = self.callback.__init__.__dict__.get(key, default_val)
            ret = self.callback.__call__.__dict__.get(key, default_val)
        else:
            ret = self.callback.__dict__.get(key, default_val)

        return ret


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

    def __init__(self, *arg_names, **kwargs):
        # find the longest name
        longest_name = ""
        self.parser_args = set()

        for arg_name in arg_names:
            if len(longest_name) < len(arg_name):
                longest_name = arg_name.lstrip("-")

            if len(arg_name) > 2:
                arg_name = arg_name.lstrip("-")
                self.merge_args([
                    '--{}'.format(arg_name),
                    '--{}'.format(arg_name.replace('_', '-')),
                    '--{}'.format(arg_name.replace('-', '_'))
                ])

            else:
                # we've got a -N type argument
                self.merge_args([arg_name])

        self.name = longest_name.replace('-', '_')
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

            elif kwargs['action'] in set(['version']):
                self.parser_kwargs.pop('required', False)

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

    def find_subcommand(self):
        cmd = ""
        bits = self.callback.__name__.split("_", 1)
        if len(bits) > 1:
            cmd = bits[1]
        return cmd

    def __init__(self, callback=None, **kwargs):
        if callback:
            parents = self.find_parents(callback)
            if parents:
                kwargs.setdefault("parents", parents)

            kwargs.setdefault("description", self.find_desc(callback))

        # https://docs.python.org/2/library/argparse.html#conflict-handler
        kwargs.setdefault("conflict_handler", 'resolve')
        # https://hg.python.org/cpython/file/2.7/Lib/argparse.py
        # https://docs.python.org/2/library/argparse.html#formatter-class
        # http://stackoverflow.com/questions/12151306/argparse-way-to-include-default-values-in-help
        kwargs.setdefault("formatter_class", argparse.ArgumentDefaultsHelpFormatter)

        super(ArgParser, self).__init__(**kwargs)

        self.arg_info = {
            'order': [],
            'required': [],
            'optional': {},
            'args': None,
            'kwargs': None
        }

        if callback:
            self.callback = callback
            self.set_defaults(main_callback=callback)
            self.find_args()

    def find_parents(self, callback):
        parents = []
        cbi = CallbackInspect(callback)
        scs = cbi.inherit_args
        for sc in scs:
            parser = type(self)(sc, add_help=False)
            parents.append(parser)
        return parents

    def parse_callback_args(self, raw_args):
        args = []
        arg_info = self.arg_info
        kwargs = dict(arg_info['optional'])

        parsed_args = []
        unknown_args = getattr(self, "unknown_args", False)
        if unknown_args:
            parsed_args, parsed_unknown_args = self.parse_known_args(raw_args)

            # **kwargs have to be in --key=val form
            # http://stackoverflow.com/a/12807809/5006
            d = defaultdict(list)
            for k, v in ((k.lstrip('-'), v) for k,v in (a.split('=') for a in parsed_unknown_args)):
                d[k].append(v)

            for k in (k for k in d if len(d[k])==1):
                d[k] = d[k][0]

            kwargs.update(d)

        else:
            parsed_args = self.parse_args(raw_args)

        # http://parezcoydigo.wordpress.com/2012/08/04/from-argparse-to-dictionary-in-python-2-7/
        kwargs.update(vars(parsed_args))

        # because of how args works, we need to make sure the kwargs are put in correct
        # order to be passed to the function, otherwise our real *args won't make it
        # to the *args variable
        for k in arg_info['order']:
            args.append(kwargs.pop(k))

        # now that we have the correct order, tack the real *args on the end so they
        # get correctly placed into the function's *args variable
        if arg_info['args']:
            args.extend(kwargs.pop(arg_info['args']))

        return args, kwargs

    def find_desc(self, callback):
        cbi = CallbackInspect(callback)
        return cbi.desc

    def find_args(self):
        arg_info = self.arg_info
        main = self.callback
        cbi = CallbackInspect(main)
        all_arg_names = set()
        decorator_args = cbi.args
        args, args_name, kwargs_name, args_defaults = cbi.argspec

        arg_info['order'] = args
        default_offset = len(args) - len(args_defaults)
        #pout.v(args, args_name, kwargs_name, args_defaults, default_offset)
        #pout.v(args, decorator_args)

        # build a list of potential *args, basically, if an arg_name matches exactly
        # then it is an *arg and we shouldn't mess with it in the function
        comp_args = set()
        for da in decorator_args:
            comp_args.update(da[0])

        for i, arg_name in enumerate(args):
            if arg_name in comp_args: continue

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

            # if the callback arg is just a value, respect the parent parser's config
            if "default" not in a.parser_kwargs \
            and "action" not in a.parser_kwargs \
            and "choices" not in a.parser_kwargs:
                keys = self._option_string_actions.keys()
                found_arg = False
                for pa in a.parser_args:
                    if pa in keys:
                        found_arg = True
                        break

                if not found_arg:
                    self.add_argument(*a.parser_args, **a.parser_kwargs)

            else:
                # we want to override parent parser
                self.add_argument(*a.parser_args, **a.parser_kwargs)

        self.unknown_args = False
        if self.add_help:
            if args_name:
                a = ScriptArg(args_name, nargs='*')
                a.merge_from_list(decorator_args)
                all_arg_names |= a.parser_args
                self.add_argument(*a.parser_args, **a.parser_kwargs)
                arg_info['args'] = args_name

            if kwargs_name:
                self.unknown_args = True
                arg_info['kwargs'] = kwargs_name

        # pick up any stragglers
        for da, dkw in decorator_args:
            if da[0] not in all_arg_names:
                arg_name = da[0]
                if arg_name.startswith("-"):
                    a = ScriptKwarg(*da)
                else:
                    a = ScriptArg(*da)

                a.merge_kwargs(dkw)
                self.add_argument(*a.parser_args, **a.parser_kwargs)

        self.arg_info = arg_info


class Script(object):

    function_name = 'main'

#     @property
#     def description(self):
#         lines = []
#         line.append(self.name)
# 
#         parser = self.parser
#         #pout.v(parser)
#         subparsers = parser._subparsers
#         if subparsers:
#             group_actions = subparsers._group_actions[0]
#             pout.v(group_actions._name_parser_map.keys())
# 
# 

        #subcommands = parser._name_parser_map
        #pout.v(subcommands)
        #self._get_formatter()._format_args(action, None)

# def format_usage(self):
#         formatter = self._get_formatter()
#         formatter.add_usage(self.usage, self._actions,
#                             self._mutually_exclusive_groups)
#         return formatter.format_help()
# def format_help(self)
# for action_group in self._action_groups:
#             formatter.start_section(action_group.title)
#             formatter.add_text(action_group.description)
#             formatter.add_arguments(action_group._group_actions)
#             formatter.end_section()

    @property
    def parser(self):
        """return the parser for the current name"""
        module = self.module

        def add_args(parser, m):
            version = getattr(m, "__version__", "")
            if version:
                parser.add_argument(
                    "-V", "--version",
                    action='version',
                    version="%(prog)s {}".format(version)
                )

            parser.add_argument("--quiet", action='store_true', dest='quiet')
            parser.add_argument("--verbose", "-v", action='store_true', dest='verbose')

        subcommands = self.subcommands
        if subcommands:
            module_desc = inspect.getdoc(self.module)
            parser = ArgParser(description=module_desc)
            add_args(parser, module)
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
            parser = ArgParser(callback=self.callbacks[self.function_name])
            add_args(parser, module)

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
        echo.quiet = kwargs.pop("quiet", False)
        echo.debug = kwargs.pop("verbose", False)

        try:
            ret_code = callback(*args, **kwargs)
            ret_code = int(ret_code) if ret_code else 0

        except ArgError as e:
            # https://hg.python.org/cpython/file/2.7/Lib/argparse.py#l2374
            echo.err("{}: error: {}", parser.prog, e.message)
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
        s.add(u"{}.{}".format(called_module, called_func))

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
                        call = u"{}.{}".format(
                            ast_name.asname if ast_name.asname is not None else ast_name.name,
                            called_func
                        )
                        s.add(call)

        return s


