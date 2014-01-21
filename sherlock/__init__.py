'''
    sherlock
    ~~~~~~~~~~~~~~~

    Locks that can be acquired in different processes running on same or
    different machines.
'''

import etcd
import pylibmc
import redis


class _Backends(object):
    '''
    A simple object that provides a list of available backends.
    '''

    REDIS = {
        'name': 'REDIS',
        'library': 'redis',
        'client_class': redis.StrictRedis,
        'lock_class': 'RedisLock',
    }
    ETCD = {
        'name': 'ETCD',
        'library': 'etcd',
        'client_class': etcd.Client,
        'lock_class': 'EtcdLock',
    }
    MEMCACHED = {
        'name': 'MEMCACHED',
        'library': 'pylibmc',
        'client_class': pylibmc.Client,
        'lock_class': 'MCLock',
    }

    @property
    def valid_backends(self):
        '''
        Return a tuple of valid backends.
        '''

        return (self.REDIS,
                self.ETCD,
                self.MEMCACHED)


def configure(**kwargs):
    '''
    Set basic configuration for the entire module.

    :param str namespace: provide global namespace
    :param float expire: provide global expiration time. If expicitly set to
                         `None`, lock will not expire.
    :param float timeout: provide global timeout period
    :param float retry_interval: provide global retry interval
    '''

    _configuration.update(**kwargs)


class _Configuration(object):

    def __init__(self):
        # Choice of backend
        self._backend = None

        # Client object to connect with the backend store
        self._client = None

        # Namespace to use for setting lock keys in the backend store
        self.namespace = None

        # Lock expiration time. If explicitly set to `None`, lock will not
        # expire.
        self.expire = 60

        # Timeout to acquire lock
        self.timeout = 10

        # Retry interval to retry acquiring a lock if previous attempts failed
        self.retry_interval = 0.1

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, val):
        if val not in backends.valid_backends:
            raise ValueError('Invalid backend. Valid backends are: '
                             'backends.REDIS, backends.ETCD and '
                             'backends.MEMCACHED.')

        self._backend = val

    @property
    def client(self):
        if self._client is not None:
            return self._client
        else:
            if self.backend is None:
                raise ValueError('Cannot create a default client object when '
                                 'backend is not configured.')
            if self.backend == backends.REDIS:
                self.client = redis.StrictRedis()
            elif self.backend == backends.ETCD:
                self.client = etcd.Client()
            elif self.backend == backends.MEMCACHED:
                self.client = pylibmc.Client(['localhost'],
                                             binary=True)

        return self._client

    @client.setter
    def client(self, val):
        # When backend is set, check client type
        if self.backend is not None:
            exc_msg = ('Only a client of the %s library can be used '
                       'when using %s as the backend store option.')
            if isinstance(val, self.backend['client_class']):
                self._client = val
            else:
                raise ValueError(exc_msg % (self.backend['library'],
                                            self.backend['name']))
        else:
            for backend in backends.valid_backends:
                if isinstance(val, backend['client_class']):
                    self._client = val
                    self.backend = backend
            if self._client is None:
                raise ValueError('The provided object is not a valid client'
                                 'object. Client objects can only be '
                                 'instances of redis library\'s client class,'
                                 'python-etcd library\'s client class or '
                                 'pylibmc library\'s client class.')

    def update(self, **kwargs):
        '''
        Update configuration. Provide keyword arguments where the keyword
        parameter is the configuration and its value (the argument) is the
        value you intend to set.

        :param backend: global choice of backend. This backend will be used
                        for managing locks.
        :param client: global client object to use to connect with backend
                       store.
        :param str namespace: optional global namespace to namespace lock keys
                              for your application in order to avoid conflicts.
        :param float expire: set lock expiry time. If explicitly set to `None`,
                             lock will not expire.
        :param float timeout: global timeout for acquiring a lock.
        :param float retry_interval: global timeout for retrying to acquire the
                                     lock if previous attempts failed.
        '''

        for key, val in kwargs.iteritems():
            if key not in dir(self):
                raise AttributeError('Invalid configuration. No such '
                                     'configuration as %s.' % key)
            setattr(self, key, val)


# Create a backends singleton
backends = _Backends()

# Create a configuration singleton
_configuration = _Configuration()

# Import important Lock classes
from .lock import *
