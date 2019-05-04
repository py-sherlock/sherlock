'''
    lock
    ~~~~

    A generic lock.
'''

__all__ = [
    'LockException',
    'LockTimeoutException',
    'BaseLock',
]

import time

from . import _configuration


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


class BaseLock(object):
    '''
    Interface for implementing custom Lock implementations. This class must be
    sub-classed in order to implement a custom Lock with custom logic or
    different backend or both.

    Basic Usage (an example of our imaginary datastore)

    >>> class MyLock(BaseLock):
    ...     def __init__(self, lock_name, **kwargs):
    ...         super(MyLock, self).__init__(lock_name, **kwargs)
    ...         if self.client is None:
    ...             self.client = mybackend.Client(host='localhost', port=1234)
    ...         self._owner = None
    ...
    ...     def _acquire(self):
    ...         if self.client.get(self.lock_name) is not None:
    ...             owner = uuid.uuid4() # or anythin you want
    ...             self.client.set(self.lock_name, owner)
    ...             self._owner = owner
    ...             if self.expire is not None:
    ...                 self.client.expire(self.lock_name, self.expire)
    ...             return True
    ...         return False
    ...
    ...     def _release(self):
    ...         if self._owner is not None:
    ...             lock_val = self.client.get(self.lock_name)
    ...             if lock_val == self._owner:
    ...                 self.client.delete(self.lock_name)
    ...
    ...     def _locked(self):
    ...         if self.client.get(self.lock_name) is not None:
    ...             return True
    ...         return False
    '''

    def __init__(self,
                 lock_name,
                 **kwargs):
        '''
        :param str lock_name: name of the lock to uniquely identify the lock
                              between processes.
        :param str namespace: Optional namespace to namespace lock keys for
                              your application in order to avoid conflicts.
        :param float expire: set lock expiry time. If explicitly set to `None`,
                             lock will not expire.
        :param float timeout: set timeout to acquire lock
        :param float retry_interval: set interval for trying acquiring lock
                                     after the timeout interval has elapsed.
        :param client: supported client object for the backend of your choice.
        '''

        self.lock_name = lock_name

        if kwargs.get('namespace'):
            self.namespace = kwargs['namespace']
        else:
            self.namespace = _configuration.namespace

        if 'expire' not in kwargs:
            self.expire = _configuration.expire
        else:
            self.expire = kwargs['expire']

        if kwargs.get('timeout'):
            self.timeout = kwargs['timeout']
        else:
            self.timeout = _configuration.timeout

        if kwargs.get('retry_interval'):
            self.retry_interval = kwargs['retry_interval']
        else:
            self.retry_interval = _configuration.retry_interval

        if kwargs.get('client'):
            self.client = kwargs['client']
        else:
            self.client = None

    @property
    def _locked(self):
        '''
        Implementation of method to check if lock has been acquired. Must be
        implemented in the sub-class.

        :returns: if the lock is acquired or not
        :rtype: bool
        '''

        raise NotImplementedError('Must be implemented in the sub-class.')

    def locked(self):
        '''
        Return if the lock has been acquired or not.

        :returns: True indicating that a lock has been acquired ot a
                  shared resource is locked.
        :rtype: bool
        '''

        return self._locked

    def _acquire(self):
        '''
        Implementation of acquiring a lock in a non-blocking fashion. Must be
        implemented in the sub-class. :meth:`acquire` makes use of this
        implementation to provide blocking and non-blocking implementations.

        :returns: if the lock was successfully acquired or not
        :rtype: bool
        '''

        raise NotImplementedError('Must be implemented in the sub-class.')

    def acquire(self, blocking=True):
        '''
        Acquire a lock, blocking or non-blocking.

        :param bool blocking: acquire a lock in a blocking or non-blocking
                              fashion. Defaults to True.
        :returns: if the lock was successfully acquired or not
        :rtype: bool
        '''

        if blocking is True:
            timeout = self.timeout
            while timeout >= 0:
                if self._acquire() is not True:
                    timeout -= self.retry_interval
                    if timeout > 0:
                        time.sleep(self.retry_interval)
                else:
                    return True
            raise LockTimeoutException('Timeout elapsed after %s seconds '
                                       'while trying to acquiring '
                                       'lock.' % self.timeout)
        else:
            return self._acquire()

    def _release(self):
        '''
        Implementation of releasing an acquired lock. Must be implemented in
        the sub-class.
        '''

        raise NotImplementedError('Must be implemented in the sub-class.')

    def release(self):
        '''
        Release a lock.
        '''

        return self._release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        try:
            self.release()
        except LockException:
            pass
