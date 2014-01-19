try:
    from setuptools import setup, find_packages
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

__title__ = 'sherlock'
__version__ = '.'.join(map(str, (0, 0, 0)))
__author__ = 'Vaidik Kapoor'

# read contents of a file
read_file = lambda x: open(x, 'r').read()

setup(
    name='sherlock',
    version=__version__,
    author='Vaidik Kapoor',
    author_email='kapoor.vaidik@gmail.com',
    description=('Locks that can be acquired in different processes running '
                 'on same or different machines.'),
    long_description=read_file('README.md'),
    platforms=('Any',),
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'redis',
        'etcd',
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
        'datadiff',
    ]
)
