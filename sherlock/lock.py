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

from . import backends
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


class Lock(BaseLock):
    '''
    A general lock that inherits global coniguration and provides locks.
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

        .. Note:: this Lock object does not accept a custom lock backend store
                  client object. It instead uses the global custom client
                  object.
        '''

        # Raise exception if client keyword argument is found
        if 'client' in kwargs:
            raise TypeError('Lock object does not accept a custom client '
                            'object')
        super(Lock, self).__init__(lock_name, **kwargs)

        try:
            self.client = _configuration.client
        except ValueError:
            pass

        if self.client is None:
            self._lock_proxy = None
        else:
            try:
                self._lock_proxy = globals()[_configuration.backend['lock_class']](
                    lock_name, **kwargs)
            except KeyError:
                self._lock_proxy = _configuration.backend['lock_class'](
                    lock_name, **kwargs)

    def _acquire(self):
        if self._lock_proxy is None:
            raise LockException('Lock backend has not been configured and '
                                'lock cannot be acquired or released. '
                                'Configure lock backend first.')
        return self._lock_proxy.acquire(False)

    def _release(self):
        if self._lock_proxy is None:
            raise LockException('Lock backend has not been configured and '
                                'lock cannot be acquired or released. '
                                'Configure lock backend first.')
        return self._lock_proxy.release()

    @property
    def _locked(self):
        if self._lock_proxy is None:
            raise LockException('Lock backend has not been configured and '
                                'lock cannot be acquired or released. '
                                'Configure lock backend first.')
        return self._lock_proxy.locked()


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
        owner = uuid.uuid4()
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
            raise LockException('Lock could not be released because it has '
                                'not been acquired by this instance.')

        self._owner = None

    @property
    def _locked(self):
        if self.client.get(self._key_name) is None:
            return False
        return True


class EtcdLock(BaseLock):

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

        super(EtcdLock, self).__init__(lock_name, **kwargs)

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
            _args = [self._key_name, owner]
            if self.expire is not None:
                _args.append(self.expire)
            self.client.set(*tuple(_args))
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

        super(MCLock, self).__init__(lock_name, **kwargs)

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

        _args = [self._key_name, str(owner)]
        if self.expire is not None:
            _args.append(self.expire)
        # Set key only if it does not exist
        if self.client.add(*tuple(_args)) is True:
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
