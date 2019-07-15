#!/usr/bin/env python

#    Copyright 2019 Dirk Niggemann
#
#    This file is part of PyGCMS.
#

from setuptools import setup
from glob import glob
import matplotlib
import sys
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# read in the version number
with open('pygcms/__init__.py') as f:
    exec(f.read())

options = {
    'name': 'PyGCMS',
    'version': __version__,
    'description': 'HP 5890/5971 GC/MS Control Program',
    'author': 'Dirk Niggemann',
    'author_email': 'dirk.niggemann@gmail.com',
    'url': 'https://github.com/dirkenstein/pygcms',
    'license': 'MIT',
    'platforms': ['Any'],
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Chemistry'
    ],
    'long_description': read('README.rst'),
    'packages': ['pygcms', 'pygcms.gui',
                 'pygcms.device', 'pygcms.msfile', 'pygcms.calc'],
    'scripts': ['gcms.py','spec.py'],
    'include_package_data': False,
    'install_requires': ['numpy', 'scipy', 'matplotlib', 'peakutils','mollusk', 'pandas', 'PyQt5', 'pyqt_led'],
}

#all the magic happens right here
setup(**options)

