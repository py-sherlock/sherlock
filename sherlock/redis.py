'''
    redis
    ~~~~~

    Implementation using Redis as backend.
'''

__all__ = [
    'RedisLock',
]

import redis
import uuid

from .base import BaseLock
from .exceptions import LockException

_client_class = redis.StrictRedis


class RedisLock(BaseLock):
    '''
    Implementation of lock with Redis as the backend for synchronization.

    Basic Usage:

    >>> import redis
    >>> import sherlock
    >>> from sherlock import RedisLock
    >>>
    >>> # Global configuration of defaults
    >>> sherlock.configure(expire=120, timeout=20)
    >>>
    >>> # Create a lock instance
    >>> lock = RedisLock('my_lock')
    >>>
    >>> # Acquire a lock in Redis, global backend and client configuration need
    >>> # not be configured since we are using a backend specific lock.
    >>> lock.acquire()
    True
    >>>
    >>> # Check if the lock has been acquired
    >>> lock.locked()
    True
    >>>
    >>> # Release the acquired lock
    >>> lock.release()
    >>>
    >>> # Check if the lock has been acquired
    >>> lock.locked()
    False
    >>>
    >>> # Use this client object
    >>> client = redis.StrictRedis()
    >>>
    >>> # Create a lock instance with custom client object
    >>> lock = RedisLock('my_lock', client=client)
    >>>
    >>> # To override the defaults, just past the configurations as parameters
    >>> lock = RedisLock('my_lock', client=client, expire=1, timeout=5)
    >>>
    >>> # Acquire a lock using the with_statement
    >>> with RedisLock('my_lock') as lock:
    ...     # do some stuff with your acquired resource
    ...     pass
    '''

    _acquire_script = '''
    local result = redis.call('SETNX', KEYS[1], KEYS[2])
    if result == 1 then
        redis.call('EXPIRE', KEYS[1], KEYS[3])
    end
    return result
    '''

    _release_script = '''
    local result = 0
    if redis.call('GET', KEYS[1]) == KEYS[2] then
        redis.call('DEL', KEYS[1])
        result = 1
    end
    return result
    '''

    def __init__(self, lock_name, **kwargs):
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

        super(RedisLock, self).__init__(lock_name, **kwargs)

        if self.client is None:
            self.client = redis.StrictRedis(host='localhost', port=6379, db=0)

        self._owner = None

        # Register Lua script
        self._acquire_func = self.client.register_script(self._acquire_script)
        self._release_func = self.client.register_script(self._release_script)

    @property
    def _key_name(self):
        if self.namespace is not None:
            key = '%s_%s' % (self.namespace, self.lock_name)
        else:
            key = self.lock_name
        return key

    def _acquire(self):
        owner = str(uuid.uuid4())
        if self.expire is None:
            expire = -1
        else:
            expire = self.expire
        if self._acquire_func(keys=[self._key_name,
                                    owner,
                                    expire]) != 1:
            return False
        self._owner = owner
        return True

    def _release(self):
        if self._owner is None:
            raise LockException('Lock was not set by this process.')

        if self._release_func(keys=[self._key_name, self._owner]) != 1:
            raise LockException('Lock could not be released because it was '
                                'not acquired by this instance.')

        self._owner = None

    @property
    def _locked(self):
        if self.client.get(self._key_name) is None:
            return False
        return True
