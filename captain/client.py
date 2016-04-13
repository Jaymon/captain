import os
import subprocess
import sys
import threading


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

    cmd_prefix = "python"
    """this is what will be used to invoke captain from the command line when run()
    is called"""

    thread_class = threading.Thread
    """the threading class to use if run_async() is called instead of run()"""

    def __init__(self, script, cwd=""):
        self.cwd = cwd if cwd else os.curdir
        self.script = script
        if self.script_prefix and not script.startswith(self.script_prefix):
            self.script = os.path.join(self.script_prefix, script)

        if self.script_postfix and not self.script.endswith(self.script_postfix):
            self.script += self.script_postfix

        #if not self.script.endswith('.py'):
        #    self.script += '.py'

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

    def check_run(self, *args, **kwargs):
        """runs the command and returns all the output"""
        ret = ""
        for line in self.run(*args, **kwargs):
            ret += line
        return ret

    def run(self, arg_str='', **process_kwargs):
        cmd = "{} {} {}".format(self.cmd_prefix, self.script, arg_str)

        # we will allow overriding of these values
        process_kwargs.setdefault("stderr", subprocess.STDOUT)

        # we will not allow these to be overridden via kwargs
        process_kwargs["shell"] = True
        process_kwargs["stdout"] = subprocess.PIPE
        process_kwargs["cwd"] = self.cwd

        try:
            process = subprocess.Popen(
                cmd,
                **process_kwargs
            )

            # another round of links
            # http://stackoverflow.com/a/17413045/5006 (what I used)
            # http://stackoverflow.com/questions/2715847/
            for line in iter(process.stdout.readline, ""):
                yield line

            # flush any remaining output
            #line = process.stdout.read()
            #yield line

            process.wait()
            if process.returncode > 0:
                raise RuntimeError("{} returned {}".format(cmd, process.returncode))

        except subprocess.CalledProcessError as e:
            raise RuntimeError("{} returned {}".format(cmd, e.returncode))

