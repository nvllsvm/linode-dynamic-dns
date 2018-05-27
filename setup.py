from setuptools import setup

VERSION = '0.3.1'

setup(
    name='linode-dynamic-dns',
    version=VERSION,
    description='Dynamically set the IP of Linode DNS records ',
    long_description=open('README.rst').read(),
    author='Andrew Rabert',
    author_email='ar@nullsum.net',
    url='https://github.com/nvllsvm/linode-dynamic-dns',
    packages=['linode_dynamic_dns'],
    install_requires=['requests'],
    entry_points={
        'console_scripts': ['linode-dynamic-dns=linode_dynamic_dns:main']},
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6'
    )
)
