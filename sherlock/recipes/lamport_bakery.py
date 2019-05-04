'''
    lamport_bakery
    ~~~~~~~~~~~~~~

    Generic implementation of Lamport Bakery locking algorithm.

    >>> import sherlock
    >>> from sherlock.recipes import LamportLock
    >>>
    >>> sherlock.configure(sherlock.backends.CASANDRA)
    >>>
    >>> lock1 = LamportLock(name='my_lock')
    >>> lock1.acquire()
    True
    >>> lock1.locked()
    True
    >>>
    >>> lock2 = LamportLock(name='my_lock_2')
    >>> lock2.acquire(blocking=False)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    LamportLockException: Waiting in queue at rank 1
    >>>
    >>> lock1.release()
    >>>
    >>> lock1.locked()
    >>> False
'''

import sherlock

from ..base_lock import BaseLock


class KVStore(dict):

    CAPACITY = 3


kv = KVStore()


class LamportLock(BaseLock):

    ALLOWED_BACKENDS = (
        sherlock.backends.CASSANDRA,
    )

    CAPACITY = 5

    def __init__(self, lock_name, **kwargs):
        super(LamportLock, self).__init__(lock_name, **kwargs)

        backend = kwargs.get('backend')
        client = kwargs.get('client')

        if backend is not None and backend not in self.ALLOWED_BACKENDS:
            raise ValueError('%s backend is not supported.' % backend)
        self.backend = backend

        if client is not None:
            if backend is not None:
                if not isinstance(client, backend['client_class']):
                    raise ValueError(
                        'Client\'s instance type (%s) does not '
                        'match the type of specified backend (%s)' % (
                            type(client), backend))
            else:
                for allowed_backend in self.ALLOWED_BACKENDS:
                    if not isinstance(client,
                                      allowed_backend['client_class']):
                        raise ValueError('Client type %s is not supported.' % (
                            type(client)))

            self.client = kwargs['client']
        else:
            # self.client = self.backend['client_class'](
            self.client = kv

    def _acquire(self):
        if self.client.get(self.lock_name) is None:
            self.client[self.lock_name] = True
            return True

        return False

    def __del__(self):
        self.client = dict()
