import sys
import os
import argparse
import imp
import codecs
import re
import ast

__version__ = '0.1'
debug = False

class ScriptArg(object):

    def __init__(self, node):
        self.node = node

class Script(object):

    @property
    def body(self):
        if not hasattr(self, '_body'):
            with codecs.open(self.path, 'r+', 'utf-8') as fp:
                self._body = fp.read()
        return self._body

    def __init__(self, script_path):
        self.path = os.path.abspath(os.path.expanduser(str(script_path)))
        if not os.path.isfile(self.path):
            raise IOError("{} does not exist".format(self.path))

    def validate(self):
        body = self.body
        if not re.match("^#!.*?python.*$", body, re.I | re.MULTILINE):
            raise ValueError("no shebang! Please add this as first line: #!/usr/bin/env python")

        args = self.get_args()
        return True

    def get_args(self):
        # make sure the shebang exists
        ast_tree = ast.parse(self.body, self.path)
        #pout.v(ast.dump(ast_tree))
        found_main = False
        parser = None
        kwarg_info = {'required': [], 'optional': {}}
        type_map = {
            'int': int,
            'str': str,
            'float': float
        }

        for n in ast.walk(ast_tree):
            if isinstance(n, ast.FunctionDef):
                if n.name == 'main':
                    found_main = True
                    desc = ''
                    if n.body:
                        doc = n.body[0]
                        if isinstance(doc, ast.Expr) and isinstance(doc.value, ast.Str):
                            desc = doc.value.s

                    parser = argparse.ArgumentParser(description=desc)
                    nas = n.args
#                    pout.v(nas)
#                    pout.x()
                    for i, arg in enumerate(nas.args):
                        arg_args = []
                        arg_kwargs = {}
                        arg_args.append('--{}'.format(arg.id))

                        if len(nas.defaults) > i:
                            try:
                                na = nas.defaults[i]
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


                        #pout.v(arg_args, arg_kwargs)
                        parser.add_argument(*arg_args, **arg_kwargs)

                    if nas.vararg:
                        parser.add_argument(nas.vararg, nargs='*')

                    if nas.kwarg:
                        parser.unknown_args = True

                    self.kwarg_info = kwarg_info

        return parser

        import tokenize
        import token
        g = tokenize.generate_tokens(open(self.path).readline)   # tokenize the string
        for toknum, tokval, o, t, th in g:
            #pout.v(toknum, tokval, o, t, th)
            pout.v(token.tok_name[toknum], tokval)

def import_script(script):
    script = os.path.abspath(os.path.expanduser(script))
    module = imp.load_source('commands_script', script)
    return module

def console_out(format_str, *args, **kwargs):
    sys.stderr.write(format_str.format(*args, **kwargs))
    sys.stderr.write(os.linesep)

def console_debug(*args, **kwargs):
    if debug:
        console_out(*args, **kwargs)

def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Command line script running')
    #parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='base directory, defaults to current working directory')
    parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("-v", "--version", action='version', version="%(prog)s {}".format(__version__))
    #parser.add_argument('args', nargs=argparse.REMAINDER, help='all other arguments')
    parser.add_argument('script', metavar='SCRIPT', help='The script you want to run')

    args, command_args = parser.parse_known_args()

    s = Script(args.script)


    pout.v(args, command_args)


    return 0


    """
    go through each directory of the current directory (then all python directories) looking
    for commands modules, when you find one, see if command_name from the cli is in that module
    (convert any . to /, etc), then you will need to find the command, default_command(...) is the
    default, otherwise name_command(...), you will then introspect to get the params that should be
    passed into it, set those in argparse and then parse the command_args to get a final dict
    that will be passed to the function. Now, to add a new command you just need to a new module
    or a new method in an existing command module and boom, you have a new command, to list all
    the current commands, you just need to run this without any commands, and it will go through
    and parse and compile all the commands and print them out that it can find
    """

    global debug
    debug = args.debug

    return

    # we want to strip current working directory here and add basedir to the pythonpath
    curdir = normalize_dir(os.curdir)
    basedir = normalize_dir(args.basedir)

    # remove current dir paths because basedir will be the dir the code should think it is executing in
    for p in ['', curdir, os.curdir, '{}{}'.format(os.curdir, os.sep)]:
        if p in sys.path:
            sys.path.remove(p)

    sys.path.insert(0, basedir)
    test_args.insert(0, sys.argv[0])
    ret_code = 0

    console_debug('basedir: {}', basedir)

    for module in args.modules:
        found = False
        module = module.decode('utf-8')
        tests_info = find_test_info(module)
        for test_info in tests_info:
            try:
                test = find_test(test_info, basedir)
                if test:
                    found = True
                    ret_code |= run_test(test, argv=test_args)
                    break # only run the first test found for each passed in arg

            except LookupError, e:
                pass
        
        if not found:
            console_out("No test was found for: {}", module)
            ret_code |= 1

    return ret_code

if __name__ == u'__main__':
    sys.exit(console())
