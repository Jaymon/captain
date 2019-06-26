# Captain

Easy python cli scripts for people that just want get things done.


## Usage

A valid `captain` cli script needs just two things:

1. A `main` function

    ```python
    def main(foo, bar):
        return 0
    ```

2. Calling exit using `captain.exit(__name__)`

    ```python
    import captain

    def main(foo, bar):
        return 0

    captain.exit(__name__)
    ```

That's it! Whatever arguments you define in the `main` function will be options on the command line. A captain script is called just like any other python command line script, so to run the above example you could do:

    $ python path/to/script.py --foo=1 --bar=2


## Argument Decorator

The `captain.decorators.arg()` decorator provides a nice passthrough api to the full [argparse](https://docs.python.org/2/library/argparse.html) module if you need to really customize how arguments are passed into your script:

```python
from captain import exit
from captain import echo
from captain.decorators import arg 


@arg('--foo', '-f')
@arg('arg', metavar='ARG')
def main(*args, **kwargs):
    '''this is the help description'''
    echo.out(args)
    echo.out(kwargs)

exit(__name__)
```

Would print a help string like this:

    usage: script.py [-h] [--foo FOO] ARG

    this is the help description

    positional arguments:
      ARG

    optional arguments:
      -h, --help         show this help message and exit
      --foo FOO, -f FOO

If you want another nifty way to define arguments, take a look at [docopt](https://github.com/docopt/docopt).


## Echo

This small module makes it easy to print stuff in your script while still giving you full control by being able to configure the logger if you need to. It also will obey the global `--quiet` flag.

```python
from captain import echo

var1 = "print"

var2 = "stdout"
echo.out("this will {} to {}", var1, var2)

var2 = "stderr"
echo.err("this will {} to {}", var1, var2)

e = ValueError("this will print with stacktrace and everything")
echo.exception(e)
```

The `echo` module has a lot of nice little helper features but Captain also can work with modules like [clint](https://github.com/kennethreitz/clint) if you need to do more advanced cli output.


## Examples

### A typical standard python cli script

```python
import argparse

if __name__ == u'__main__':
    parser = argparse.ArgumentParser(description='fancy script description')
    parser.add_argument("--foo", action='store_true')
    parser.add_argument("--bar", default=0, type=int)
    parser.add_argument("args", nargs='*')
    args = parser.parse_args()
```

would become:

```python
import captain

def main(foo=False, bar=0, *args):
    '''fancy script description'''
    return 0

captain.exit(__name__)
```


### Subcommands

Captain supports multiple subcommands defined in the script using the format `main_subcommand`.

```python
# cli.py

import captain

def main_foo():
    pass

def main_bar():
    pass

captain.exit(__name__)
```

So `foo` could be called using:

    $ python cli.py foo

And `bar` could be called using:

    $ python cli.py bar


### Embedding captain in another package

If you want a script from you package to be usable using both `python -m example` and maybe a `console_scripts` entry point, you can set up your package's `__main__.py` module like this:


```python
# example/__main__.py

from captain import exit

def main():
    pass

# hook for setup.py entry_points
def console():
    exit(__name__)
    
# hook for python -m MODULE call
if __name__ == "__main__":
    console()
```

And then in your `setup.py` script you can add:


```python
entry_points = {
    'console_scripts': [
        'example = example.__main__:console'
    ],
}
```

That's all there is to it.


### Easy listing of all captain scripts in a directory

You can get a list of all available scripts in a directory by running captain with no arguments:

    $ captain


## Install

Use pip:

    $ pip install captain

For latest and greatest:

    $ pip install --upgrade "git+https://github.com/Jaymon/captain#egg=captain"

