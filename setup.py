from setuptools import setup


setup(
    name='linode-dynamic-dns',
    description='Dynamically set the IP of Linode DNS records ',
    long_description=open('README.rst').read(),
    author='Andrew Rabert',
    author_email='ar@nullsum.net',
    url='https://github.com/nvllsvm/linode-dynamic-dns',
    packages=['linode_dynamic_dns'],
    install_requires=['requests'],
    entry_points={
        'console_scripts': ['linode-dynamic-dns=linode_dynamic_dns:main']},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    setup_requires=['setuptools_scm'],
    use_scm_version=True
)
