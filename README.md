# Commands

Easy python cli scripts for people that just want get things done.

Commands was lovingly crafted for [First Opinion](http://firstopinionapp.com).

## Usage

A valid `commands` cli script needs two things:

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

can be called on the command line:

    $ pyc path/to/script.py --foo=1 --bar=2


## Examples

```python
import argparse

parser.add_argument("--foo", action='store_true')
parser.add_argument("--bar", default=0, type=int)
parser.add_argument("args", nargs='*')
```

would become:

```python
#!/usr/bin/env python

def main(foo=False, bar=0, *args):
    return 0
```

You can get a list of all available scripts in a directory by running commands with no arguments:

    $ pyc

## Install

Use pip:

    $ pip install commands

## License

MIT

