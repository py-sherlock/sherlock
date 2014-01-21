try:
    from setuptools import setup, find_packages
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

__title__ = 'sherlock'
__version__ = '.'.join(map(str, (0, 0, 0)))
__author__ = 'Vaidik Kapoor'

import os

# get path of repo files
path = lambda fname: os.path.join(os.path.dirname(__file__), fname)

description = ''
for file_ in ('README.rst', 'LICENSE.rst', 'CHANGELOG.rst'):
    with open(path('%s' % file_)) as f:
        description += f.read() + '\n\n'

setup(
    name='sherlock',
    version=__version__,
    author='Vaidik Kapoor',
    author_email='kapoor.vaidik@gmail.com',
    description=('Distributed inter-process locks with a choice of backend.'),
    long_description=description,
    platforms=('Any',),
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'redis',
        'python-etcd',
        'pylibmc',
    ],
    zip_safe = False,
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'mock',
    ]
)
