#!/usr/bin/env python

from setuptools import setup

from linode_dynamic_dns import __version__

setup(
    name='linode-dynamic-dns',
    version=__version__,
    description='Python Distribution Utilities',
    author='Andrew Rabert',
    author_email='arabert@nullsum.net',
    url='https://github.com/nvllsvm/linode-dynamic-dns',
    packages=['linode_dynamic_dns'],
    install_requires=['requests'],
    entry_points={
        'console_scripts': ['linode-dynamic-dns=linode_dynamic_dns.app:main']}
)
