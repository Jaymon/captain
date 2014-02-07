# Captain

Easy python cli scripts for people that just want get things done.

Captain was lovingly crafted for [First Opinion](http://firstopinionapp.com).

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

can be called on the command line:

    $ pyc path/to/script.py --foo=1 --bar=2


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

