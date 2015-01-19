# Captain

Easy python cli scripts for people that just want get things done.

Captain was lovingly crafted for [First Opinion](http://firstopinionapp.com) and powers all our command line scripts.

## Usage

A valid `captain` cli script needs two things:

1. a shebang on the first line

    ```python
    #!/usr/bin/env python
    ```

2. a `main` function

    ```python
    def main(foo, bar):
        return 0
    ```

That's it! Whatever arguments you define in the `main` function will be options on the command line.

```python
def main(foo, bar):
    return 0
```

So `foo` and `bar` can be called on the command line:

    $ pyc path/to/script.py --foo=1 --bar=2


## Argument Decorator

The `captain.decorators.arg()` decorator provides a nice passthrough api to the full [argparse](https://docs.python.org/2/library/argparse.html) module if you need to really customize how arguments are passed into your script:

```python
#!/usr/bin/env python

from captain import echo
from captain.decorators import arg 


@arg('--foo', '-f')
@arg('arg', metavar='ARG')
def main(**kwargs):
    '''this is the help description'''
    print kwargs['foo'], kwargs['a']
    return 0
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

This small module makes it easy to print output in your script while still giving you full control by being able to configure the logger if you need to. It also will obey the global `--quiet` flag.

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

Captain also can work with [clint](https://github.com/kennethreitz/clint) if you need to do more advanced cli output.


## Examples

A typical standard python cli script:

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
#!/usr/bin/env python

def main(foo=False, bar=0, *args):
    '''fancy script description'''
    return 0
```

You can get a list of all available scripts in a directory by running captain with no arguments:

    $ captain


## Install

Use pip:

    $ pip install captain


## License

MIT


## TODO

allow you to set *_arg values, so you could do `arg=[int]` to make sure the *args values where all ints, likewise, you could do `foo_arg, bar_arg` and that would be positional arg 0 and 1, I think this would work ok and be ok, we could also make everything that ends in `_kwarg` be a named argument and everything that ends in `_arg` be a positional argument. Then `*args` and `**kwargs` would just be for everything else (the catchall).

