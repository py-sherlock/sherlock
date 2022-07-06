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
    'MCLock',
    'KubernetesLock'
]

import datetime
import etcd
import kubernetes.client
import kubernetes.client.exceptions
import kubernetes.config
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
    ...             owner = str(uuid.uuid4()) # or anythin you want
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


class Lock(BaseLock):
    '''
    A general lock that inherits global coniguration and provides locks with
    the configured backend.

    .. note:: to use :class:`Lock` class, you must configure the global backend
              to use a particular backend. If the global backend is not set,
              calling any method on instances of :class:`Lock` will throw
              exceptions.

    Basic Usage:

    >>> import sherlock
    >>> from sherlock import Lock
    >>>
    >>> sherlock.configure(sherlock.backends.REDIS)
    >>>
    >>> # Create a lock instance
    >>> lock = Lock('my_lock')
    >>>
    >>> # Acquire a lock in Redis running on localhost
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
    >>> import redis
    >>> redis_client = redis.StrictRedis(host='X.X.X.X', port=6379, db=2)
    >>> sherlock.configure(client=redis_client)
    >>>
    >>> # Acquire a lock in Redis running on X.X.X.X:6379
    >>> lock.acquire()
    >>>
    >>> lock.locked()
    True
    >>>
    >>> # Acquire a lock using the with_statement
    >>> with Lock('my_lock') as lock:
    ...     # do some stuff with your acquired resource
    ...     pass
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
            kwargs.update(client=_configuration.client)
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


class EtcdLock(BaseLock):
    '''
    Implementation of lock with Etcd as the backend for synchronization.

    Basic Usage:

    >>> import etcd
    >>> import sherlock
    >>> from sherlock import EtcdLock
    >>>
    >>> # Global configuration of defaults
    >>> sherlock.configure(expire=120, timeout=20)
    >>>
    >>> # Create a lock instance
    >>> lock = EtcdLock('my_lock')
    >>>
    >>> # Acquire a lock in Etcd, global backend and client configuration need
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
    >>> client = etcd.Client()
    >>>
    >>> # Create a lock instance with custom client object
    >>> lock = EtcdLock('my_lock', client=client)
    >>>
    >>> # To override the defaults, just past the configurations as parameters
    >>> lock = EtcdLock('my_lock', client=client, expire=1, timeout=5)
    >>>
    >>> # Acquire a lock using the with_statement
    >>> with EtcdLock('my_lock') as lock:
    ...     # do some stuff with your acquired resource
    ...     pass
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
        owner = str(uuid.uuid4())

        _args = [self._key_name, owner]
        if self.expire is not None:
            _args.append(self.expire)

        try:
            self.client.write(self._key_name, owner,
                              prevExist=False, ttl=self.expire)
            self._owner = owner
        except etcd.EtcdAlreadyExist:
            return False
        else:
            return True

    def _release(self):
        if self._owner is None:
            raise LockException('Lock was not set by this process.')

        try:
            resp = self.client.delete(self._key_name,
                                      prevValue=str(self._owner))
            self._owner = None
        except ValueError:
            raise LockException('Lock could not be released because it '
                                'was been acquired by this instance.')
        except etcd.EtcdKeyNotFound:
            raise LockException('Lock could not be released as it has not '
                                'been acquired')

    @property
    def _locked(self):
        try:
            self.client.get(self._key_name)
            return True
        except etcd.EtcdKeyNotFound:
            return False


class MCLock(BaseLock):
    '''
    Implementation of lock with Memcached as the backend for synchronization.

    Basic Usage:

    >>> import pylibmc
    >>> import sherlock
    >>> from sherlock import MCLock
    >>>
    >>> # Global configuration of defaults
    >>> sherlock.configure(expire=120, timeout=20)
    >>>
    >>> # Create a lock instance
    >>> lock = MCLock('my_lock')
    >>>
    >>> # Acquire a lock in Memcached, global backend and client configuration
    >>> # need not be configured since we are using a backend specific lock.
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
    >>> client = pylibmc.Client(['X.X.X.X'], binary=True)
    >>>
    >>> # Create a lock instance with custom client object
    >>> lock = MCLock('my_lock', client=client)
    >>>
    >>> # To override the defaults, just past the configurations as parameters
    >>> lock = MCLock('my_lock', client=client, expire=1, timeout=5)
    >>>
    >>> # Acquire a lock using the with_statement
    >>> with MCLock('my_lock') as lock:
    ...     # do some stuff with your acquired resource
    ...     pass
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
        owner = str(uuid.uuid4())

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
                                    'was been acquired by this instance.')
        else:
            raise LockException('Lock could not be released as it has not '
                                'been acquired')

    @property
    def _locked(self):
        return True if self.client.get(self._key_name) is not None else False


class KubernetesLock(BaseLock):
    '''
    Implementation of lock with Kubernetes resource as the backend for synchronization.

    Basic Usage:

    >>> import sherlock
    >>> from sherlock import KubernetesLock
    >>>
    >>> # Global configuration of defaults
    >>> sherlock.configure(expire=120, timeout=20)
    >>>
    >>> # Create a lock instance
    >>> lock = KubernetesLock(
    ...     'my_lock', 'my_namespace', group='', version='v1', resource='configmaps',
    ... )
    >>>
    >>> # Acquire a lock in Kubernetes, global backend and client configuration need
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
    >>> # To override the defaults, just past the configurations as parameters
    >>> lock = KubernetesLock(
    ...     'my_lock', 'my_namespace', expire=1, timeout=5,
    ... )
    >>>
    >>> # Acquire a lock using the with_statement
    >>> with KubernetesLock('my_lock', 'my_namespace') as lock:
    ...     # do some stuff with your acquired resource
    ...     pass
    '''

    def __init__(
        self,
        lock_name: str,
        k8s_namespace: str,
        **kwargs,
    ) -> None:
        '''
        :param str lock_name: name of the lock to uniquely identify the lock
                              between processes.
        :param str k8s_namespace: Kubernetes namespace to store the lock in.
        :param str namespace: Namespace to namespace lock keys for
                              your application in order to avoid conflicts.
        :param float expire: set lock expiry time. If explicitly set to `None`,
                             lock will not expire.
        :param float timeout: set timeout to acquire lock
        :param float retry_interval: set interval for trying acquiring lock
                                     after the timeout interval has elapsed.
        :param client: supported client object for the backend of your choice.
        '''
        super().__init__(lock_name, **kwargs)

        self.k8s_namespace = k8s_namespace

        # Verify that all names are compatible with Kubernetes.
        rfc_1123_dns_label = re.compile('^(?![0-9]+$)(?!-)[a-zA-Z0-9-]{,63}(?<!-)$')
        err_msg = '{} must conform to RFC1123\'s definition of a DNS label for KubernetesLock'
        for attr in ('lock_name', 'k8s_namespace', 'namespace'):
            value = getattr(self, attr)
            if value is not None:
                if rfc_1123_dns_label.match(getattr(self, attr)) is None:
                    raise ValueError(err_msg.format(attr))

        if self.client is None:
            kubernetes.config.load_config()
            self.client = kubernetes.client.CoordinationV1Api()

        self._owner = None

    @property
    def _key_name(self):
        if self.namespace is not None:
            key = '%s-%s' % (self.namespace, self.lock_name)
        else:
            key = self.lock_name
        return key

    def _get_lease_expiry_time(self, lease: kubernetes.client.V1Lease) -> datetime:
        # Determine whether the Lease has exired.
        if lease.spec.renew_time is not None and lease.spec.lease_duration_seconds is not None:
            return lease.spec.renew_time + datetime.timedelta(seconds=lease.spec.lease_duration_seconds)
        elif lease.spec.lease_duration_seconds is None:
            return datetime.datetime.max
        return datetime.datetime.min

    def _acquire(self):
        name = self._key_name
        owner = self._owner or str(uuid.uuid4())

        try:
            lease = self.client.read_namespaced_lease(
                name=name, namespace=self.k8s_namespace
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason == 'Not Found':
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                lease = self.client.create_namespaced_lease(
                    namespace=self.k8s_namespace,
                    body=kubernetes.client.V1Lease(
                        metadata=kubernetes.client.V1ObjectMeta(
                            name=name,
                        ),
                        spec=kubernetes.client.V1LeaseSpec(
                            holder_identity=owner,
                            acquire_time=now,
                            renew_time=now,
                            lease_duration_seconds=self.expire,
                        ),
                    ),
                )
                self._owner = owner
                return True
            raise LockException('Could not read or create Lock.') from exc

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if owner == lease.spec.holder_identity:
            # Same owner renew lease.
            lease.spec.renew_time = now
            lease.spec.lease_duration_seconds = self.expire
        elif now < self._get_lease_expiry_time(lease):
            # Lease has not expired.
            return False

        # Different owner and lease has expired so acquire lease.
        lease.spec.holder_identity = owner
        lease.spec.acquire_time = now
        lease.spec.renew_time = now
        lease.spec.lease_duration_seconds = self.expire

        try:
            lease = self.client.replace_namespaced_lease(
                name=name,
                namespace=self.k8s_namespace,
                body=lease,
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason == 'Conflict':
                return False
            raise Lock('Failed to update Lock.') from exc
        self._owner = owner
        return True

    def _release(self):
        if self._owner is None:
            raise LockException('Lock was not set by this process.')

        name = self._key_name
        try:
            lease = self.client.read_namespaced_lease(
                name=name,
                namespace=self.k8s_namespace,
            )
            if self._owner == lease.spec.holder_identity:
                self.client.delete_namespaced_lease(
                    name=name,
                    namespace=self.k8s_namespace,
                    body=kubernetes.client.V1DeleteOptions(
                        preconditions=kubernetes.client.V1Preconditions(
                            resource_version=lease.metadata.resource_version
                        )
                    )
                )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason in ('Not Found', 'Conflict'):
                # The Lease was acquired by another instance and may have
                # already been removed by that instance.
                raise LockException(
                    'Lock could not be released because it was '
                    'no longer held by this instance.'
                ) from exc
            raise exc

    @property
    def _locked(self):
        try:
            lease = self.client.read_namespaced_lease(
                name=self._key_name,
                namespace=self.k8s_namespace,
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason == 'Not Found':
                return False
            raise exc

        if datetime.datetime.now(tz=datetime.timezone.utc) > self._get_lease_expiry_time(lease):
            return False
        return True
