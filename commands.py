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

__version__ = '0.1'


class Script(object):

    function_name = 'main'

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def module(self):
        """load the module so we can actually run the script's function"""
        module = imp.load_source('commands_script', self.path)
        return module

    @property
    def body(self):
        """get the contents of the script"""
        if not hasattr(self, '_body'):
            with codecs.open(self.path, 'r+', 'utf-8') as fp:
                self._body = fp.read()
        return self._body

    @property
    def description(self):
        self.parse()
        return self.parser.description

    def __init__(self, script_path):
        self.parser = None
        self.arg_info = None
        self.path = os.path.abspath(os.path.expanduser(str(script_path)))
        if not os.path.isfile(self.path):
            raise IOError("{} does not exist".format(self.path))

    def __call__(self, *args, **kwargs):
        """this wraps around the script's function, it is functionally equivalent
        to import the script and running function_name manually"""
        module = self.module
        return getattr(module, self.function_name)(*args, **kwargs)

    def run(self, raw_args):
        """parse and import the script, and then run the script's main function"""
        self.parse()
        args = []
        kwargs = dict(self.arg_info['optional'])

        parsed_args = []
        if self.parser.unknown_args:
            parsed_args, parsed_unknown_args = self.parser.parse_known_args(raw_args)

            # **kwargs have to be in --key=val form
            # http://stackoverflow.com/a/12807809/5006
            d = defaultdict(list)
            for k, v in ((k.lstrip('-'), v) for k,v in (a.split('=') for a in parsed_unknown_args)):
                d[k].append(v)

            for k in (k for k in d if len(d[k])==1):
                d[k] = d[k][0]

            kwargs.update(d)

        else:
            parsed_args = self.parser.parse_args(raw_args)

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

    def has_shebang(self):
        body = self.body
        ret = False
        if re.match("^#!.*?python.*$", body, re.I | re.MULTILINE):
            ret = True
        return ret

    def is_cli(self):
        """return True if this is an actual cli script"""
        ret = True
        try:
            self.parse()
        except ValueError, e:
            ret = False

        return ret

    def parse(self):
        """load the script and set the parser and argument info"""
        if self.parser: return
        if not self.has_shebang():
            raise ValueError("no shebang! Please add this as first line: #!/usr/bin/env python")

        ast_tree = ast.parse(self.body, self.path)
        parser = None
        kwarg_info = {
            'order': [],
            'required': [],
            'optional': {},
            'args': None,
            'kwargs': None
        }
        type_map = {
            'int': int,
            'str': str,
            'float': float
        }

        for n in ast.walk(ast_tree):
            if isinstance(n, ast.FunctionDef):
                if n.name == self.function_name:
                    desc = ''
                    if n.body:
                        doc = n.body[0]
                        if isinstance(doc, ast.Expr) and isinstance(doc.value, ast.Str):
                            desc = doc.value.s

                    parser = argparse.ArgumentParser(
                        prog=self.name,
                        description=desc
                    )
                    nas = n.args
                    for i, arg in enumerate(nas.args):
                        arg_args = []
                        arg_kwargs = {}
                        arg_args.append('--{}'.format(arg.id))
                        kwarg_info['order'].append(arg.id)
                        default_i = len(nas.args) - len(nas.defaults) - i

                        if len(nas.defaults) > default_i:
                            try:
                                na = nas.defaults[default_i]
                                if isinstance(na, ast.Num):
                                    repr_n = repr(na.n)
                                    arg_kwargs['default'] = na.n
                                    kwarg_info['optional'][arg.id] = na.n
                                    if '.' in repr_n:
                                        arg_kwargs['type'] = float

                                    else:
                                        arg_kwargs['type'] = int

                                elif isinstance(na, ast.Str):
                                    arg_kwargs['default'] = na.s
                                    arg_kwargs['type'] = str
                                    kwarg_info['optional'][arg.id] = na.s

                                elif isinstance(na, ast.List):
                                    arg_kwargs['action'] = 'append'
                                    kwarg_info['required'].append(arg.id)

                                    if len(na.elts) > 0:
                                        if isinstance(na.elts[0], ast.Name):
                                            arg_kwargs['type'] = type_map[na.elts[0].id]

                                elif isinstance(na, ast.Name):
                                    if na.id == 'True':
                                        arg_kwargs['action'] = 'store_false'
                                        kwarg_info['optional'][arg.id] = True

                                    elif na.id == 'False':
                                        arg_kwargs['action'] = 'store_true'
                                        kwarg_info['optional'][arg.id] = False

                                    else:
                                        arg_kwargs['type'] = type_map[na.id]
                                        kwarg_info['required'].append(arg.id)

                                else:
                                    raise ValueError("{} has an unsupported default".format(arg.id))

                            except KeyError, e:
                                raise ValueError("{} has an unsupported default".format(arg.id))

                        else:
                            kwarg_info['required'].append(arg.id)
                            arg_kwargs['required'] = True


                        #pout.v(arg_args, arg_kwargs)
                        parser.add_argument(*arg_args, **arg_kwargs)

                    if nas.vararg:
                        parser.add_argument(nas.vararg, nargs='*')
                        kwarg_info['args'] = nas.vararg

                    parser.unknown_args = True if nas.kwarg else False
                    break

        if parser:
            self.parser = parser
            self.arg_info = kwarg_info

        else:
            raise ValueError("No main function found")



#def console_out(format_str, *args, **kwargs):
#    sys.stderr.write(format_str.format(*args, **kwargs))
#    sys.stderr.write(os.linesep)
#
#def console_debug(*args, **kwargs):
#    if debug:
#        console_out(*args, **kwargs)
#
def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Command line script running', add_help=False)
    #parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='base directory, defaults to current working directory')
    #parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("-v", "--version", action='version', version="%(prog)s {}".format(__version__))
    #parser.add_argument('args', nargs=argparse.REMAINDER, help='all other arguments')
    parser.add_argument('script', metavar='SCRIPT', nargs='?', help='The script you want to run')

    args, command_args = parser.parse_known_args()

    ret_code = 0

    if args.script:
        s = Script(args.script)
        ret_code = s.run(command_args)

    else:
        basepath = os.getcwd()
        print "Known Commands in {}:".format(basepath)
        for root_dir, dirs, files in os.walk(basepath, topdown=True):
            for f in fnmatch.filter(files, '*.py'):
                filepath = os.path.join(root_dir, f)
                s = Script(filepath)
                if s.is_cli():
                    rel_filepath = os.path.relpath(filepath, basepath)
                    print "\t{}".format(rel_filepath)
                    desc = s.description
                    if desc:
                        for l in desc.split("\n"):
                            print "\t\t{}".format(l)

                    print ""

    return ret_code


if __name__ == u'__main__':
    sys.exit(console())
