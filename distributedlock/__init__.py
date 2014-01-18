'''
    distributedlock
    ~~~~~~~~~~~~~~~

    Locks that can be acquired in different processes running on same or
    different machines.
'''

__title__ = 'distributedlock'
__version__ = '.'.join(map(str, (0, 0, 0)))
__author__ = 'Vaidik Kapoor'


def configure(backend=None):
    '''
    Set basic configuration for the entire module.
    '''
