#!/usr/bin/env python
# http://docs.python.org/distutils/setupscript.html
# http://docs.python.org/2/distutils/examples.html

from setuptools import setup

import captain as module
name = module.__name__
version = module.__version__

setup(
    name=name,
    version=version,
    description='python cli scripts for humans',
    author='Jay Marcyes',
    author_email='jay@firstopinionapp.com',
    url='http://github.com/firstopinion/{}'.format(name),
    packages=[name],
    license="MIT",
    classifiers=[ # https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
    ],
    entry_points = {
        'console_scripts': [
            '{} = {}.__main__:main'.format(name, name),
        ],
    }
)

