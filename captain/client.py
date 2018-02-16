# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import subprocess
import sys
import threading
from collections import deque

from .compat import *


class Captain(object):
    """makes running a captain script from a non CLI environment easy peasy

    We've basically had this in our private repo, and then we created a new project
    and we copy/pasted it into that project so we could test some scripts, then we
    created another project and did the same thing, and that's when it clicked, hey,
    why don't we spend some time to make this generic and put it in the actual
    package? That way there would be one canonical place for running a Captain script.
    And there were high fives all around
    """

    script_prefix = ""
    """this will be prepended to the passed in script on initialization"""

    script_postfix = ""
    """this will be appended to the passed in script on initialization"""

    script_quiet = True
    """this is the default quiet setting for running a script, it can be overriden in run()"""

    cmd_prefix = "python"
    """this is what will be used to invoke captain from the command line when run()
    is called"""

    thread_class = threading.Thread
    """the threading class to use if run_async() is called instead of run()"""

    bufsize = 1000
    """how many lines to buffer of output, set to 0 to suppress all output"""

    @property
    def environ(self):
        environ = getattr(self, "_environ", None)
        if environ: return environ

        # NOTE -- this would have to be updated if this file ever moved
        pwd = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
        pythonpath = pwd + os.pathsep + self.cwd

        environ = dict(os.environ)
        if "PYTHONPATH" in environ:
            environ["PYTHONPATH"] += os.pathsep + pythonpath
        else:
            environ["PYTHONPATH"] = pythonpath

        self._environ = environ
        return environ

    @environ.setter
    def environ(self, v):
        self._environ = v

    @environ.deleter
    def environ(self):
        del self._environ

    @property
    def output(self):
        try:
            ret = "\n".join(self.buf)
        except AttributeError:
            ret = ""

        return ret

    def __init__(self, script, cwd=""):
        self.cwd = os.path.realpath(cwd) if cwd else os.getcwd()
        self.script = script
        if self.script_prefix and not script.startswith(self.script_prefix):
            self.script = os.path.join(self.script_prefix.rstrip("/"), script)

        if self.script_postfix and not self.script.endswith(self.script_postfix):
            self.script += self.script_postfix

    def flush(self, line):
        """flush the line to stdout"""
        # TODO -- maybe use echo?
        sys.stdout.write(line)
        sys.stdout.flush()

    def wait(self):
        self.async_thread.join()

    def run_async(self, *args, **kwargs):
        def target():
            self.run(*args, **kwargs)

        self.async_thread = self.thread_class(target=target)
        self.async_thread.start()

    def run(self, arg_str='', **kwargs):
        quiet = kwargs.pop("quiet", self.script_quiet)
        for line in self.execute(arg_str, **kwargs):
            if not quiet:
                self.flush(line)
        return self.output

    def execute(self, arg_str='', **kwargs):
        """runs the passed in arguments and returns an iterator on the output of
        running command"""
        cmd = "{} {} {}".format(self.cmd_prefix, self.script, arg_str)

        # any kwargs with all capital letters should be considered environment
        # variables
        environ = self.environ
        for k in list(kwargs.keys()):
            if k.isupper():
                environ[k] = kwargs.pop(k)

        # we will allow overriding of these values
        kwargs.setdefault("stderr", subprocess.STDOUT)

        # we will not allow these to be overridden via kwargs
        kwargs["shell"] = True
        kwargs["stdout"] = subprocess.PIPE
        kwargs["cwd"] = self.cwd
        kwargs["env"] = environ

        self.buf = deque(maxlen=self.bufsize)

        try:
            process = subprocess.Popen(
                cmd,
                **kwargs
            )

            # another round of links
            # http://stackoverflow.com/a/17413045/5006 (what I used)
            # http://stackoverflow.com/questions/2715847/
            if is_py2:
                for line in iter(process.stdout.readline, ""):
                    self.buf.append(line.rstrip())
                    yield line
            else:
                for line in iter(process.stdout.readline, b""):
                    line = line.decode("utf-8")
                    self.buf.append(line.rstrip())
                    yield line

            process.wait()
            if process.returncode > 0:
                raise RuntimeError("{} returned {} with output: {}".format(cmd, process.returncode, self.output))

        except subprocess.CalledProcessError as e:
            raise RuntimeError("{} returned {} with output: {}".format(cmd, e.returncode, self.output))


class ModuleClient(Captain):
    """This sets the client up so you can just pass the module name and have everything
    just work"""
    script_quiet = False

    def __init__(self, module_name, cwd=""):
        self.cmd_prefix = "python -m {}".format(module_name)
        super(ModuleClient, self).__init__("", cwd=cwd)


class ScriptClient(Captain):
    """This will add the .py to a script so you don't have to"""
    script_quiet = False

    script_postfix = ".py"

    def __init__(self, script, cwd=""):
        super(ScriptClient, self).__init__(script, cwd=cwd)

