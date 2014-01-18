'''
    distributedlock
    ~~~~~~~~~~~~~~~

    Locks that can be acquired in different processes running on same or
    different machines.
'''

__title__ = 'distributedlock'
__version__ = '.'.join(map(str, (0, 0, 0)))
__author__ = 'Vaidik Kapoor'


class _Backends(object):
    '''
    A simple object that provides a list of available backends.
    '''

    REDIS = {
        'name': 'REDIS',
        'library': 'redis',
        'available': False,
    }
    ETCD = {
        'name': 'ETCD',
        'library': 'etcd',
        'available': False,
    }
    MEMCACHED = {
        'name': 'MEMCACHED',
        'library': 'pylibmc',
        'available': False,
    }

    @property
    def valid_backends(self):
        '''
        Return a tuple of valid backends.
        '''

        return (self.REDIS,
                self.ETCD,
                self.MEMCACHED)


try:
    import etcd
    _Backends.ETCD['available'] = True
except ImportError:
    pass

try:
    import pylibmc
    _Backends.MEMCACHED['available'] = True
except ImportError:
    pass


try:
    import redis
    _Backends.REDIS['available'] = True
except ImportError:
    pass


def configure(**kwargs):
    '''
    Set basic configuration for the entire module.

    :param str namespace: provide global namespace
    :param float expire: provide global expiration time
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

        # Lock expiration time
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

        if not val['available']:
            raise ImportError('%s library is not available and hence %s '
                              'can\'t be used as backend.' % (val['library'],
                                                              val['name']))

        self._backend = val

    @property
    def client(self):
        if self._client is not None:
            return self._client
        else:
            if self.backend is None:
                raise ValueError('Cannot create a client object when backend '
                                 'is not configured.')
            if self.backend == backends.REDIS:
                self.client = redis.StrictRedis()
            elif self.backend == backends.ETCD:
                self.client = etcd.Client()
            elif self.backend == backends.MEMCACHED:
                self.client = pylibmc.Client()

        return self._client

    @client.setter
    def client(self, val):
        if self.backend is not None:
            exc_msg = ('Only a client of the %s library can be used '
                       'when using %s as the backend store option.')
            if self.backend == backends.REDIS:
                if isinstance(val, redis.client.StrictRedis):
                    self._client = val
                else:
                    raise ValueError(exc_msg % (self.backend['ibrary'],
                                                self.backend['name']))
            elif self.backend == backends.ETCD:
                if isinstance(val, etcd.Client):
                    self._client = val
                else:
                    raise ValueError(exc_msg % (self.backend['ibrary'],
                                                self.backend['name']))
            elif self.backend == backends.MEMCACHED:
                if isinstance(val, pylibmc.Client):
                    self._client = val
                else:
                    raise ValueError(exc_msg % (self.backend['ibrary'],
                                                self.backend['name']))
        else:
            if backends.REDIS['available']:
                if isinstance(val, redis.client.StrictRedis):
                    self._client = val
                    self.backend = backends.REDIS
            elif backends.ETCD['available']:
                if isinstance(val, etcd.Client):
                    self._client = val
                    self.backend = backends.ETCD
            elif backends.MEMCACHED['available']:
                if isinstance(val, pylibmc.Client):
                    self._client = val
                    self.backend = backends.MEMCACHED
            if self._client is None:
                raise ValueError('Either none of the backend store client '
                                 'libraries are missing or the provided '
                                 'object is unacceptable.')

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
        :param float expire: global lock expiry time.
        :param float timeout: global timeout for acquiring a lock.
        :param float retry_interval: global timeout for retrying to acquire the
                                     lock if previous attempts failed.
        '''

        for key, val in kwargs.iteritems():
            if key not in dir(self):
                raise AttributeError('Invalid configuration. No such '
                                     'configuration as %s.' % key)
            setattr(self, key, val)


backends = _Backends()
_configuration = _Configuration()


# Import important Lock classes
from .lock import *
