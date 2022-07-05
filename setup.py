from setuptools import setup, find_packages

__title__ = 'sherlock'
__version__ = '.'.join(map(str, (0, 3, 2)))
__author__ = 'Vaidik Kapoor'

import os

# get path of repo files
path = lambda fname: os.path.join(os.path.dirname(__file__), fname)

description = ''
for file_ in ('README.rst', 'CHANGELOG.rst'):
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
        'kubernetes',
        'redis',
        'python-etcd',
        'pylibmc',
    ],
    zip_safe = False,
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'mock',
    ]
)
