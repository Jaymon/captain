# Captain

Easy python cli scripts for people that just want get things done.

__Important__ - If you have older scripts you might need the [captain~=3.0.0 branch](https://github.com/Jaymon/captain/tree/3.0.0). The mainline branch has an entirely different interface.


## Usage

A valid `captain` cli script needs just two things:

1. A `Default` class that extends `captain.Command` and has a `handle()` method:

    ```python
    from captain import Command
    
    class Default(Command):
        def handle(self, foo, bar):
            return 0
    ```

2. Calling `captain.handle()` at the end of your script:

    ```python
    from captain import Command, handle
    
    class Default(Command):
        def handle(self, foo, bar):
            return 0

    if __name__ == "__main__":
        handle()
    ```

That's it! Whatever arguments you define in your class's `Default.handle()` method will be options on the command line. A captain script is called just like any other python command line script, so to run the above example you could do:

    $ python path/to/script.py --foo=1 --bar=2


## Argument Decorator

The `captain.arg()` decorator provides a nice passthrough api to the full [argparse.ArgumentParser.add_argument() method](https://docs.python.org/3/library/argparse.html#the-add-argument-method) if you want to fine tune how arguments are passed into your script:

```python
from captain import Command, handle, arg

class Default(Command):
    @arg('--foo', '-f', action="store_true")
    @arg('arg', metavar='ARG')
    def handle(self, *args, **kwargs):
        '''this is the help description'''
        self.output.out(args)
        self.output.out(kwargs)

if __name__ == "__main__":
    handle()
```

Would print a help string like this:

    usage: script.py [-h] [--foo FOO] ARG

    this is the help description

    positional arguments:
      ARG

    optional arguments:
      -h, --help         show this help message and exit
      --foo FOO, -f FOO


## Command Output

The `captain.io.Output` class makes it easy to print stuff in your script while still giving you full control by being able to configure the logger if you need to. It also will obey the global `--quiet` flag that Captain adds to every script. 

It's available in the `handle()` method by using `self.output`:

```python
from captain import Command

class Default(Command):
    def handle(self, *args, **kwargs):
        var1 = "print"

        var2 = "stdout"
        self.output.out("this will {} to {}", var1, var2)

        var2 = "stderr"
        self.output.err("this will {} to {}", var1, var2)

        e = ValueError("this will print with stacktrace and everything")
        self.output.exception(e)
```

The `captain.io.Output` class has a lot of nice little helper methods but Captain can also work with modules like [clint](https://github.com/kennethreitz/clint) if you need to do more advanced cli output.


## Examples

A typical standard python cli script

```python
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='fancy script description')
    parser.add_argument("--foo", action='store_true')
    parser.add_argument("--bar", default=0, type=int)
    parser.add_argument("args", nargs='*')
    args = parser.parse_args()
    sys.exit(0)
```

would become:

```python
import captain

class Default(captain.Command):
    def handle(foo=False, bar=0, *args):
        '''fancy script description'''
        return 0

if __name__ == '__main__':
    captain.handle()
```


### Subcommands

Captain supports multiple subcommands defined in the script by naming your `captain.Command` child classes something other than `Default`:

```python
# cli.py

import captain

class Foo(captain.Command):
    def handle(self):
        pass

class Bar(captain.Command):
    def handle(self):
        pass

if __name__ == '__main__':
    captain.handle()
```

So `foo` could be called using:

    $ python cli.py foo

And `bar` could be called using:

    $ python cli.py bar


### Embedding captain in another package

If you want a script from you package to be usable using both `python -m example` and maybe a `console_scripts` entry point defined in `setup.py`, you can set up your package's `__main__.py` module like this:


```python
# example/__main__.py

from captain import Command, handle

class Default(captain.Command):
    def handle(self):
        pass
        
if __name__ == "__main__":
    handle()
```

And then in your `setup.py` script you can add:


```python
entry_points = {
    'console_scripts': [
        'example = example.__main__:handle'
    ],
}
```

That's all there is to it.


## Install

Use pip:

    $ pip install captain

For latest and greatest:

    $ pip install -U "git+https://github.com/Jaymon/captain#egg=captain"

