'''
    exceptions
    ~~~~~~~~~~

    Sherlock specific exceptions.
'''

__all__ = [
    'LockException',
    'LockTimeoutException',
]


class LockException(Exception):
    '''
    Generic exception for Locks.
    '''

    pass


class LockTimeoutException(Exception):
    '''
    Raised whenever timeout occurs while trying to acquire lock.
    '''

    pass
