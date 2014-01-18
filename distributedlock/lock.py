'''
    lock
    ~~~~

    A generic lock.
'''

__all__ = [
    'LockException',
    'LockTimeoutException',
    'Lock',
    'RedisLock',
    'EtcdLock',
    'MCLock'
]

import etcd
import pylibmc
import redis
import time
import uuid

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

    def __init__(self,
                 lock_name,
                 namespace=None,
                 expire=60,
                 timeout=10,
                 retry_interval=0.1,
                 client=None):
        '''
        :param str lock_name: name of the lock to uniquely identify the lock
                              between processes.
        :param str namespace: Optional namespace to namespace lock keys for
                              your application in order to avoid conflicts.
        :param int expire: set lock expiry time.
        :param int timeout: set timeout to acquire lock
        :param int retry_interval: set interval for trying acquiring lock
                                     after the timeout interval has elapsed.
        :param client: supported client object for the backend of your choice.
        '''

        self.lock_name = lock_name

        if kwargs.get('namespace'):
            self.namespace = kwargs['namespace']
        else:
            self.namespace = _configuration.namespace

        if kwargs.get('expire'):
            self.expire = kwargs['expire']
        else:
            self.expire = _configuration.expire

        if kwargs.get('timeout'):
            self.timeout = kwargs['timeout']
        else:
            self.timeout = _configuration.timeout

        if kwargs.get('retry_interval'):
            self.retry_interval = kwargs['retry_interval']
        else:
            self.client = _configuration.retry_interval

        if kwargs.get('client'):
            self.client = kwargs['client']
        else:
            self.client = _configuration.client

    @property
    def _locked(self):
        '''
        Implementation of method to check if lock has been acquired. Must be
        implemented in the sub-class.
        '''

        raise NotImplementedError('Must be implemented in the sub-class.')

    def locked(self):
        '''
        Return if the lock has been acquired or not.

        :returns bool: True indicating that a lock has been acquired ot a
                       shared resource is locked.
        '''

        return self._locked

    def _acquire(self):
        '''
        Implementation of acquiring a lock in a non-blocking fashion. Must be
        implemented in the sub-class. :meth:`acquire` makes use of this
        implementation to provide blocking and non-blocking implementations.
        '''

        raise NotImplementedError('Must be implemented in the sub-class.')

    def acquire(self, blocking=True):
        '''
        Acquire a lock, blocking or non-blocking.

        :param bool blocking: acquire a lock in a blocking or non-blocking
                              fashion. Defaults to True.
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
            raise LockTimeoutException('Timeout elapsed while trying to '
                                       'acquire Lock.')
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


class RedisLock(BaseLock):

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

    def __init__(self, *args, **kwargs):
        '''
        :param str lock_name: name of the lock to uniquely identify the lock
                              between processes.
        :param str namespace: Optional namespace to namespace lock keys for
                              your application in order to avoid conflicts.
        :param int expire: set lock expiry time.
        :param int timeout: set timeout to acquire lock
        :param int retry_interval: set interval for trying acquiring lock
                                   after the timeout interval has elapsed.
        :param client: supported client object for the backend of your choice.
        '''

        super(RedisLock, self).__init__(*args, **kwargs)

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
        owner = uuid.uuid4()
        if self._acquire_func(keys=[self._key_name,
                                    owner,
                                    self.expire]) != 1:
            return False
        self._owner = owner
        return True

    def _release(self):
        if self._owner is None:
            raise LockException('Lock was not set by this process.')

        if self._release_func(keys=[self._key_name, self._owner]) != 1:
            raise LockException('Lock could not be released because it has '
                                'not been acquired by this instance.')

        self._owner = None

    @property
    def _locked(self):
        if self.client.get(self._key_name) is None:
            return False
        return True


class EtcdLock(BaseLock):

    def __init__(self, *args, **kwargs):
        '''
        :param str lock_name: name of the lock to uniquely identify the lock
                              between processes.
        :param str namespace: Optional namespace to namespace lock keys for
                              your application in order to avoid conflicts.
        :param int expire: set lock expiry time.
        :param int timeout: set timeout to acquire lock
        :param int retry_interval: set interval for trying acquiring lock
                                   after the timeout interval has elapsed.
        :param client: supported client object for the backend of your choice.
        '''

        super(EtcdLock, self).__init__(*args, **kwargs)

        if self.client is None:
            self.client = etcd.Client()

        self._owner = None

    @property
    def _key_name(self):
        if self.namespace is not None:
            return '/%s/%s' % (self.namespace, self.lock_name)
        else:
            return '/%s' % self.lock_name

    def _acquire(self):
        owner = uuid.uuid4()

        try:
            self.client.get(self._key_name)
        except KeyError:
            self.client.set(self._key_name, owner, ttl=self.expire)
            self._owner = owner
            return True
        else:
            return False

    def _release(self):
        if self._owner is None:
            raise LockException('Lock was not set by this process.')

        try:
            resp = self.client.get(self._key_name)
            if resp.value == str(self._owner):
                self.client.delete(self._key_name)
                self._owner = None
            else:
                raise LockException('Lock could not be released because it '
                                    'has not been acquired by this instance.')
        except KeyError:
            raise LockException('Lock could not be released as it has not '
                                'been acquired')

    @property
    def _locked(self):
        try:
            self.client.get(self._key_name)
            return True
        except KeyError:
            return False


class MCLock(BaseLock):

    def __init__(self, *args, **kwargs):
        '''
        :param str lock_name: name of the lock to uniquely identify the lock
                              between processes.
        :param str namespace: Optional namespace to namespace lock keys for
                              your application in order to avoid conflicts.
        :param int expire: set lock expiry time.
        :param int timeout: set timeout to acquire lock
        :param int retry_interval: set interval for trying acquiring lock
                                   after the timeout interval has elapsed.
        :param client: supported client object for the backend of your choice.
        '''

        super(MCLock, self).__init__(*args, **kwargs)

        if self.client is None:
            self.client = pylibmc.Client(['localhost'],
                                         binary=True)

        self._owner = None

    @property
    def _key_name(self):
        if self.namespace is not None:
            key = '%s_%s' % (self.namespace, self.lock_name)
        else:
            key = self.lock_name
        return key

    def _acquire(self):
        owner = uuid.uuid4()

        # Set key only if it does not exist
        if self.client.add(self._key_name, str(owner),
                           time=self.expire) is True:
            self._owner = owner
            return True
        else:
            return False

    def _release(self):
        if self._owner is None:
            raise LockException('Lock was not set by this process.')

        resp = self.client.get(self._key_name)
        if resp is not None:
            if resp == str(self._owner):
                self.client.delete(self._key_name)
                self._owner = None
            else:
                raise LockException('Lock could not be released because it '
                                    'has not been acquired by this instance.')
        else:
            raise LockException('Lock could not be released as it has not '
                                'been acquired')

    @property
    def _locked(self):
        return True if self.client.get(self._key_name) is not None else False
