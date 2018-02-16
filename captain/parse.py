# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import argparse
import types
import re
import inspect
import sys
from collections import defaultdict, Callable

from .compat import *
from . import logging
from . import environ


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
            if is_py2:
                desc = inspect.getdoc(cb_method)
            else:
                # avoid method doc inheritance in py >=3.5
                desc = cb_method.__doc__
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
        #args, args_name, kwargs_name, args_defaults = getfullargspec(self.callable)
        signature = getfullargspec(self.callable)
        args = signature[0]
        args_name = signature[1]
        kwargs_name = signature[2]
        args_defaults = signature[3]
        if self.is_instance() or self.is_class():
            args = args[1:] # remove self which will always get passed in automatically

        if not args: args = []
        if not args_defaults: args_defaults = []
        return args, args_name, kwargs_name, args_defaults

    def __init__(self, callback):
        self.callback = callback

    def is_class(self):
        return inspect.isclass(self.callback)
        #return isinstance(self.callback, type)

    def is_instance(self):
        """return True if callback is an instance of a class"""
        ret = False
        val = self.callback
        if self.is_class(): return False

        ret = not inspect.isfunction(val) and not inspect.ismethod(val)
#         if is_py2:
#             ret = isinstance(val, types.InstanceType) or hasattr(val, '__dict__') \
#                 and not (hasattr(val, 'func_name') or hasattr(val, 'im_func'))
# 
#         else:
#             ret = not inspect.isfunction(val) and not inspect.ismethod(val)

        return ret

    def is_function(self):
        """return True if callback is a vanilla plain jane function"""
        if self.is_instance() or self.is_class(): return False
        return isinstance(self.callback, (Callable, classmethod))

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


class QuietAction(argparse.Action):

    OPTIONS = "DIWEC"

    DEST = "quiet"

    HELP_QUIET = ''.join([
        'Selectively turn off [D]ebug, [I]nfo, [W]arning, [E]rror, or [C]ritical, ',
        '(--quiet=DI means suppress Debug and Info), ',
        'use - to invert (--quiet=-EW means suppress everything but Error and warning)',
        'use + to change default (--quiet=+D means remove D from default value)',
    ])

    HELP_Q_LOWER = ''.join([
        'Turn off [D]ebug (-q), [I]nfo (-qq), [W]arning (-qqq), [E]rror (-qqqq), ',
        'and [C]ritical (-qqqqq)',
    ])

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.levels = self.OPTIONS
        kwargs["required"] = False
        if "-q" in option_strings:
            #kwargs["required"] = False
            kwargs["nargs"] = 0
            kwargs["default"] = None

        else:
            kwargs["const"] = self.OPTIONS
            kwargs["default"] = environ.QUIET_DEFAULT

        super(QuietAction, self).__init__(option_strings, self.DEST, **kwargs)

    def __call__(self, parser, namespace, values, option_string=""):
        #pout.v(namespace, values, option_string)

        if option_string.startswith("-q"):
            v = getattr(namespace, self.dest, "")
            if v == "":
                v = self.OPTIONS
            values = v[1:]

        else:
            if values.startswith("-"):
                # if we have a subtract then just remove those from being suppressed
                # so -E would only show errors
                values = "".join(set(self.OPTIONS) - set(values[1:].upper()))

            elif values.startswith("+"):
                # if we have an addition then just remove those from default
                # so if default="D" then +D would leave default=""
                values = "".join(set(self.default) - set(values[1:].upper()))

        setattr(namespace, self.dest, values)


class ArgParser(argparse.ArgumentParser):

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

    def find_subcommand(self):
        cmd = ""
        bits = self.callback.__name__.split("_", 1)
        if len(bits) > 1:
            cmd = bits[1]
        return cmd

    def find_parents(self, callback):
        parents = []
        cbi = CallbackInspect(callback)
        scs = cbi.inherit_args
        for sc in scs:
            parser = type(self)(callback=sc, add_help=False)
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


class Parser(ArgParser):

    def __init__(self, module=None, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)

        # only parent parsers will have the module
        self.module = module
        if module:
            version = getattr(module, "__version__", "")
            if version:
                self.add_argument(
                    "-V", "--version",
                    action='version',
                    version="%(prog)s {}".format(version)
                )

            self.add_argument(
                '--quiet', '-Q',
                action=QuietAction,
                help=QuietAction.HELP_QUIET,
            )
            self.add_argument(
                "-q",
                action=QuietAction,
                help=QuietAction.HELP_Q_LOWER,
            )

    def normalize_quiet_arg(self, arg_strings):
        """This is a hack to allow `--quiet` and `--quiet DI` to work correctly,
        basically it goes through all arg_strings and if it finds --quiet it checks
        the next argument to see if it is some combination of DIWEC, if it is then
        it combines it to `--quiet=ARG` and returns the modified arg_strings list

        :param arg_strings: list, the raw arguments
        :returns: list, the arg_strings changed if needed
        """
        action = self._option_string_actions.get("--quiet")
        if action:
            count = len(arg_strings)
            new_args = []
            i = 0
            while i < count:
                arg_string = arg_strings[i]
                if arg_string in action.option_strings:
                    if (i + 1) < count:
                        narg_string = arg_strings[i + 1]
                        if narg_string in self._option_string_actions:
                            # make sure a flag like -D isn't mistaken for a
                            # --quiet value
                            new_args.append("{}={}".format(arg_string, action.const))

                        elif re.match(r"^\-?[{}]+$".format(action.const), narg_string):
                            new_args.append("{}={}".format(arg_string, narg_string))
                            i += 1

                        else:
                            new_args.append("{}={}".format(arg_string, action.const))

                    else:
                        new_args.append("{}={}".format(arg_string, action.const))

                else:
                    new_args.append(arg_string)

                i += 1

            arg_strings = new_args

        #pout.v(arg_strings)
        return arg_strings

    def _parse_known_args(self, arg_strings, namespace):
        arg_strings = self.normalize_quiet_arg(arg_strings)
        args, unknown_args = super(Parser, self)._parse_known_args(arg_strings, namespace)

        return args, unknown_args

    def _read_args_from_files(self, arg_strings):
        arg_strings = super(Parser, self)._read_args_from_files(arg_strings)
        arg_strings = self.normalize_quiet_arg(arg_strings)
        return arg_strings


