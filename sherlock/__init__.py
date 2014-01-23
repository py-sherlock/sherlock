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
        'default_args': (),
        'default_kwargs': {},
    }
    ETCD = {
        'name': 'ETCD',
        'library': 'etcd',
        'client_class': etcd.Client,
        'lock_class': 'EtcdLock',
        'default_args': (),
        'default_kwargs': {},
    }
    MEMCACHED = {
        'name': 'MEMCACHED',
        'library': 'pylibmc',
        'client_class': pylibmc.Client,
        'lock_class': 'MCLock',
        'default_args': (
            ['localhost'],
        ),
        'default_kwargs': {
            'binary': True,
        },
    }

    _valid_backends = (
        REDIS,
        ETCD,
        MEMCACHED,
    )

    def register(self, name, lock_class, library, client_class,
                 default_args=(), default_kwargs={}):
        '''
        Register a custom backend.

        :param str name: Name of the backend by which you would want to refer
                         this backend in your code.
        :param class lock_class: the sub-class of
                                 :class:`sherlock.lock.BaseLock` that you have
                                 implemented. The reference to your implemented
                                 lock class will be used by
                                 :class:`sherlock.Lock` proxy to use your
                                 implemented class when you globally set that
                                 the choice of backend is the one that has been
                                 implemented by you.
        :param str library: dependent client library that this implementation
                            makes use of.
        :param client_class: the client class or valid type which you use to
                             connect the datastore. This is used by the
                             :func:`configure` function to validate that
                             the object provided for the `client`
                             parameter is actually an instance of this class.
        :param tuple default_args: default arguments that need to passed to
                                   create an instance of the callable passed to
                                   `client_class` parameter.
        :param dict default_kwargs: default keyword arguments that need to
                                    passed to create an instance of the
                                    callable passed to `client_class`
                                    parameter.

        Usage:

        >>> import some_db_client
        >>> class MyLock(sherlock.lock.BaseLock):
        ...     # your implementation comes here
        ...     pass
        >>>
        >>> sherlock.configure(name='Mylock',
        ...                    lock_class=MyLock,
        ...                    library='some_db_client',
        ...                    client_class=some_db_client.Client,
        ...                    default_args=('localhost:1234'),
        ...                    default_kwargs=dict(connection_pool=6))
        '''

        if not issubclass(lock_class, lock.BaseLock):
            raise ValueError('lock_class parameter must be a sub-class of '
                             'sherlock.lock.BaseLock')
        setattr(self, name, {
            'name': name,
            'lock_class': lock_class,
            'library': library,
            'client_class': client_class,
            'default_args': default_args,
            'default_kwargs': default_kwargs,
        })

        valid_backends = list(self._valid_backends)
        valid_backends.append(getattr(self, name))
        self._valid_backends = tuple(valid_backends)

    @property
    def valid_backends(self):
        '''
        Return a tuple of valid backends.
        '''

        return self._valid_backends


def configure(**kwargs):
    '''
    Set basic global configuration for :mod:`sherlock`.

    :param backend: global choice of backend. This backend will be used
                    for managing locks by :class:`sherlock.Lock` class
                    objects.
    :param client: global client object to use to connect with backend
                   store. This client object will be used to connect to the
                   backend store by :class:`sherlock.Lock` class instances.
    :param str namespace: provide global namespace
    :param float expire: provide global expiration time. If expicitly set to
                         `None`, lock will not expire.
    :param float timeout: provide global timeout period
    :param float retry_interval: provide global retry interval

    .. note:: the global default client object set using the client parameter
              will be used only by :class:`sherlock.Lock` instances. Other
              :ref:`backend-specific-locks` will either use the provided client
              object at the time of instantiating the lock object or will
              default to creating a simple client object by themselves for
              their backend store, which will assume that their backend store
              is running on localhost.
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
            backend_names = map(lambda x: 'sherlock.backends.%s' % x['name'],
                                backends.valid_backends)
            error_str = ', '.join(backend_names[:-1])
            backend_names = '%s and %s' % (error_str,
                                           backend_names[-1])
            raise ValueError('Invalid backend. Valid backends are: '
                             '%s.' % backend_names)

        self._backend = val

    @property
    def client(self):
        if self._client is not None:
            return self._client
        else:
            if self.backend is None:
                raise ValueError('Cannot create a default client object when '
                                 'backend is not configured.')

            for backend in backends.valid_backends:
                if self.backend == backend:
                    self.client = self.backend['client_class'](
                        *self.backend['default_args'],
                        **self.backend['default_kwargs'])
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
from . import lock
from .lock import *
