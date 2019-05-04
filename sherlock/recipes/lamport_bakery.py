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
import time

from Queue import PriorityQueue
from ..base_lock import BaseLock

_queues = dict()


class LamportQueue(dict):

    def __init__(self, capacity, retry_interval=0.1, timeout=10):
        self.capacity = capacity
        self.retry_interval = retry_interval
        self.timeout = timeout
        self.order = []

    def acquire(self, name):
        if len(self.order) == self.capacity:
            raise Exception('Queue full')

        self.order.append(name)

        timeout = self.timeout
        locked = False
        while timeout >= 0:
            print timeout
            if self.order.index(name) == 0:
                locked = True
                break
            time.sleep(self.retry_interval)
            timeout -= self.retry_interval

        if locked is False:
            self.order.remove(name)

        return locked

    def release(self, name):
        if self.order[0] == name:
            self.order.pop(0)
        else:
            raise Exception('Not your turn yet')


class LamportLock(BaseLock):

    ALLOWED_BACKENDS = (
        sherlock.backends.CASSANDRA,
    )

    CAPACITY = 5

    def __init__(self, lock_name, **kwargs):
        super(LamportLock, self).__init__(lock_name, **kwargs)

        backend = kwargs.get('backend')
        client = kwargs.get('client')

        if backend is None and client is None:
            raise ValueError('Either backend or client must be passed')

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
            if _queues.get(self.lock_name) is None:
                _queues[self.lock_name] = PriorityQueue(self.CAPACITY)
            self.client = _queues[self.lock_name]

    def _acquire(self):
        self.client.put(self.lock_name, block=False)
        return True

    def _release(self):
        return self.client.get(block=False)

    def __del__(self):
        self.client = dict()
