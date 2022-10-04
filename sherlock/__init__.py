"""
Sherlock: Distributed Locks with a choice of backend
====================================================

:mod:`sherlock` is a library that provides easy-to-use distributed inter-process
locks and also allows you to choose a backend of your choice for lock
synchronization.

|Build Status| |Coverage Status|

.. |Build Status| image:: https://travis-ci.org/vaidik/sherlock.png
   :target: https://travis-ci.org/vaidik/sherlock/
.. |Coverage Status| image:: https://coveralls.io/repos/vaidik/incoming/badge.png
   :target: https://coveralls.io/r/vaidik/incoming

Overview
--------

When you are working with resources which are accessed by multiple services or
distributed services, more than often you need some kind of locking mechanism
to make it possible to access some resources at a time.

Distributed Locks or Mutexes can help you with this. :mod:`sherlock` provides
the exact same facility, with some extra goodies. It provides an easy-to-use API
that resembles standard library's `threading.Lock` semantics.

Apart from this, :mod:`sherlock` gives you the flexibilty of using a backend of
your choice for managing locks.

:mod:`sherlock` also makes it simple for you to extend :mod:`sherlock` to use
backends that are not supported.

Features
++++++++

* API similar to standard library's `threading.Lock`.
* Support for With statement, to cleanly acquire and release locks.
* Backend agnostic: supports `Redis`_, `Memcached`_ and `Etcd`_ as choice of
  backends.
* Extendable: can be easily extended to work with any other of backend of
  choice by extending base lock class. Read :ref:`extending`.

.. _Redis: http://redis.io
.. _Memcached: http://memcached.org
.. _Etcd: http://github.com/coreos/etcd

Supported Backends and Client Libraries
+++++++++++++++++++++++++++++++++++++++

Following client libraries are supported for every supported backend:

* Redis: `redis-py`_
* Memcached: `pylibmc`_
* Etcd: `python-etcd`_

.. _redis-py: http://github.com
.. _pylibmc: http://github.com
.. _python-etcd: https://github.com/jplana/python-etcd

As of now, only the above mentioned libraries are supported. Although
:mod:`sherlock` takes custom client objects so that you can easily provide
settings that you want to use for that backend store, but :mod:`sherlock` also
checks if the provided client object is an instance of the supported clients
and accepts client objects which pass this check, even if the APIs are the
same. :mod:`sherlock` might get rid of this issue later, if need be and if
there is a demand for that.

Installation
------------

Installation is simple.

.. code:: bash

    pip install sherlock

.. note:: :mod:`sherlock` will install all the client libraries for all the
          supported backends.

Basic Usage
-----------

:mod:`sherlock` is simple to use as at the API and semantics level, it tries to
conform to standard library's :mod:`threading.Lock` APIs.

.. code-block:: python

    import sherlock
    from sherlock import Lock

    # Configure :mod:`sherlock`'s locks to use Redis as the backend,
    # never expire locks and retry acquiring an acquired lock after an
    # interval of 0.1 second.
    sherlock.configure(backend=sherlock.backends.REDIS,
                       expire=None,
                       retry_interval=0.1)

    # Note: configuring sherlock to use a backend does not limit you
    # another backend at the same time. You can import backend specific locks
    # like RedisLock, MCLock and EtcdLock and use them just the same way you
    # use a generic lock (see below). In fact, the generic Lock provided by
    # sherlock is just a proxy that uses these specific locks under the hood.

    # acquire a lock called my_lock
    lock = Lock('my_lock')

    # acquire a blocking lock
    lock.acquire()

    # check if the lock has been acquired or not
    lock.locked() == True

    # release the lock
    lock.release()

Support for ``with`` statement
++++++++++++++++++++++++++++++

.. code-block:: python

    # using with statement
    with Lock('my_lock'):
        # do something constructive with your locked resource here
        pass

Blocking and Non-blocking API
+++++++++++++++++++++++++++++

.. code-block:: python

    # acquire non-blocking lock
    lock1 = Lock('my_lock')
    lock2 = Lock('my_lock')

    # successfully acquire lock1
    lock1.acquire()

    # try to acquire lock in a non-blocking way
    lock2.acquire(False) == True # returns False

    # try to acquire lock in a blocking way
    lock2.acquire() # blocks until lock is acquired to timeout happens

Using two backends at the same time
+++++++++++++++++++++++++++++++++++

Configuring :mod:`sherlock` to use a backend does not limit you from using
another backend at the same time. You can import backend specific locks like
RedisLock, MCLock and EtcdLock and use them just the same way you use a generic
lock (see below). In fact, the generic Lock provided by :mod:`sherlock` is just
a proxy that uses these specific locks under the hood.

.. code-block:: python

    import sherlock
    from sherlock import Lock

    # Configure :mod:`sherlock`'s locks to use Redis as the backend
    sherlock.configure(backend=sherlock.backends.REDIS)

    # Acquire a lock called my_lock, this lock uses Redis
    lock = Lock('my_lock')

    # Now acquire locks in Memcached
    from sherlock import MCLock
    mclock = MCLock('my_mc_lock')
    mclock.acquire()

Tests
-----

To run all the tests (including integration), you have to make sure that all
the databases are running. Make sure all the services are running:

.. code:: bash

    # memcached
    memcached

    # redis-server
    redis-server

    # etcd (etcd is probably not available as package, here is the simplest way
    # to run it).
    wget https://github.com/coreos/etcd/releases/download/<version>/etcd-<version>-<platform>.tar.gz
    tar -zxvf etcd-<version>-<platform>.gz
    ./etcd-<version>-<platform>/etcd

Run tests like so:

.. code:: bash

    python setup.py test

Documentation
-------------

Available `here`_.

.. _here: http://sher-lock.readthedocs.org

Roadmap
-------

* Support for `Zookeeper`_ as backend.
* Support for `Gevent`_, `Multithreading`_ and `Multiprocessing`_.

.. _Zookeeper: http://zookeeper.apache.org/
.. _Gevent: http://www.gevent.org/
.. _Multithreading: http://docs.python.org/2/library/multithreading.html
.. _Multiprocessing: http://docs.python.org/2/library/multiprocessing.html

License
-------

See `LICENSE`_.

**In short**: This is an open-source project and exists in the public domain
for anyone to modify and use it. Just be nice and attribute the credits
wherever you can. :)

.. _LICENSE: http://github.com/vaidik/sherlock/blob/master/LICENSE.rst

Distributed Locking in Other Languages
--------------------------------------

* NodeJS - https://github.com/thedeveloper/warlock
"""  # noqa: disable=E501

import pathlib

# Import important Lock classes
from . import lock
from .lock import (
    EtcdLock,
    FileLock,
    KubernetesLock,
    Lock,
    LockException,
    LockTimeoutException,
    MCLock,
    RedisLock,
)

__all__ = [
    "backends",
    "configure",
    "Lock",
    "LockException",
    "LockTimeoutException",
    "EtcdLock",
    "FileLock",
    "KubernetesLock",
    "MCLock",
    "RedisLock",
]


class _Backends(object):
    """
    A simple object that provides a list of available backends.
    """

    _valid_backends = []

    try:
        import redis

        REDIS = {
            "name": "REDIS",
            "library": "redis",
            "client_class": redis.StrictRedis,
            "lock_class": "RedisLock",
            "default_args": (),
            "default_kwargs": {},
        }
        _valid_backends.append(REDIS)
    except ImportError:
        pass

    try:
        import etcd

        ETCD = {
            "name": "ETCD",
            "library": "etcd",
            "client_class": etcd.Client,
            "lock_class": "EtcdLock",
            "default_args": (),
            "default_kwargs": {},
        }
        _valid_backends.append(ETCD)
    except ImportError:
        pass

    try:
        import pylibmc

        MEMCACHED = {
            "name": "MEMCACHED",
            "library": "pylibmc",
            "client_class": pylibmc.Client,
            "lock_class": "MCLock",
            "default_args": (["localhost"],),
            "default_kwargs": {
                "binary": True,
            },
        }
        _valid_backends.append(MEMCACHED)
    except ImportError:
        pass

    try:
        import kubernetes.client

        KUBERNETES = {
            "name": "KUBERNETES",
            "library": "kubernetes",
            "client_class": kubernetes.client.CoordinationV1Api,
            "lock_class": "KubernetesLock",
            "default_args": (),
            "default_kwargs": {},
        }
        _valid_backends.append(KUBERNETES)
    except ImportError:
        pass

    try:
        FILE = {
            "name": "FILE",
            "library": "pathlib",
            "client_class": pathlib.Path,
            "lock_class": "FileLock",
            "default_args": ("/tmp/sherlock",),
            "default_kwargs": {},
        }
        _valid_backends.append(FILE)
    except ImportError:
        pass

    def register(
        self,
        name,
        lock_class,
        library,
        client_class,
        default_args=(),
        default_kwargs={},
    ):
        """
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
        """

        if not issubclass(lock_class, lock.BaseLock):
            raise ValueError(
                "lock_class parameter must be a sub-class of " "sherlock.lock.BaseLock"
            )
        setattr(
            self,
            name,
            {
                "name": name,
                "lock_class": lock_class,
                "library": library,
                "client_class": client_class,
                "default_args": default_args,
                "default_kwargs": default_kwargs,
            },
        )

        valid_backends = list(self._valid_backends)
        valid_backends.append(getattr(self, name))
        self._valid_backends = tuple(valid_backends)

    @property
    def valid_backends(self):
        """
        Return a tuple of valid backends.

        :returns: a list of valid supported backends
        :rtype: tuple
        """

        return self._valid_backends


def configure(**kwargs):
    """
    Set basic global configuration for :mod:`sherlock`.

    :param backend: global choice of backend. This backend will be used
                    for managing locks by :class:`sherlock.Lock` class
                    objects.
    :param client: global client object to use to connect with backend
                   store. This client object will be used to connect to the
                   backend store by :class:`sherlock.Lock` class instances.
                   The client object must be a valid object of the client
                   library. If the backend has been configured using the
                   `backend` parameter, the custom client object must belong
                   to the same library that is supported for that backend.
                   If the backend has not been set, then the custom client
                   object must be an instance of a valid supported client.
                   In that case, :mod:`sherlock` will set the backend by
                   introspecting the type of provided client object.
    :param str namespace: provide global namespace
    :param float expire: provide global expiration time. If expicitly set to
                         `None`, lock will not expire.
    :param float timeout: provide global timeout period
    :param float retry_interval: provide global retry interval

    Basic Usage:

    >>> import sherlock
    >>> from sherlock import Lock
    >>>
    >>> # Configure sherlock to use Redis as the backend and the timeout for
    >>> # acquiring locks equal to 20 seconds.
    >>> sherlock.configure(timeout=20, backend=sherlock.backends.REDIS)
    >>>
    >>> import redis
    >>> redis_client = redis.StrictRedis(host='X.X.X.X', port=6379, db=1)
    >>> sherlock.configure(client=redis_client)
    """

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
            backend_names = list(
                map(
                    lambda x: "sherlock.backends.%s" % x["name"],
                    backends.valid_backends,
                )
            )
            error_str = ", ".join(backend_names[:-1])
            backend_names = "%s and %s" % (error_str, backend_names[-1])
            raise ValueError(
                "Invalid backend. Valid backends are: " "%s." % backend_names
            )

        self._backend = val

    @property
    def client(self):
        if self._client is not None:
            return self._client
        else:
            if self.backend is None:
                raise ValueError(
                    "Cannot create a default client object when "
                    "backend is not configured."
                )

            for backend in backends.valid_backends:
                if self.backend == backend:
                    self.client = self.backend["client_class"](
                        *self.backend["default_args"], **self.backend["default_kwargs"]
                    )
        return self._client

    @client.setter
    def client(self, val):
        # When backend is set, check client type
        if self.backend is not None:
            exc_msg = (
                "Only a client of the %s library can be used "
                "when using %s as the backend store option."
            )
            if isinstance(val, self.backend["client_class"]):
                self._client = val
            else:
                raise ValueError(
                    exc_msg % (self.backend["library"], self.backend["name"])
                )
        else:
            for backend in backends.valid_backends:
                if isinstance(val, backend["client_class"]):
                    self._client = val
                    self.backend = backend
            if self._client is None:
                raise ValueError(
                    "The provided object is not a valid client"
                    "object. Client objects can only be "
                    "instances of redis library's client class, "
                    "python-etcd library's client class or "
                    "pylibmc library's client class."
                )

    def update(self, **kwargs):
        """
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
        """

        for key, val in kwargs.items():
            if key not in dir(self):
                raise AttributeError(
                    "Invalid configuration. No such " "configuration as %s." % key
                )
            setattr(self, key, val)


# Create a backends singleton
backends = _Backends()

# Create a configuration singleton
_configuration = _Configuration()
