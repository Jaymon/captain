#!/usr/bin/env python
# http://docs.python.org/distutils/setupscript.html
# http://docs.python.org/2/distutils/examples.html

from setuptools import setup, find_packages
import re
import os
from codecs import open


name = "captain"
with open(os.path.join(name, "__init__.py"), encoding='utf-8') as f:
    version = re.search("^__version__\s*=\s*[\'\"]([^\'\"]+)", f.read(), flags=re.I | re.M).group(1)

long_description = ""
if os.path.isfile('README.rst'):
    with open('README.rst', encoding='utf-8') as f:
        long_description = f.read()

setup(
    name=name,
    version=version,
    description='python cli scripts for humans',
    long_description=long_description,
    author='Jay Marcyes',
    author_email='jay@firstopinionapp.com',
    url='http://github.com/firstopinion/{}'.format(name),
    packages=find_packages(),
    license="MIT",
    classifiers=[ # https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    entry_points = {
        'console_scripts': [
            '{} = {}.__main__:console'.format(name, name),
        ],
    },
#     scripts=[
#         '{}/bin/captain'.format(name)
#     ]
)

