.. :mod:`sherlock` documentation master file, created by
   sphinx-quickstart on Wed Jan 22 11:28:21 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

API Documentation
=================

Configuration
+++++++++++++

:mod:`sherlock` can be globally configured to set a lot of defaults using the
:func:`sherlock.configure` function. The configuration set using
:func:`sherlock.configure` will be used as the default for all the lock
objects.

.. autofunction:: sherlock.configure

Understanding the configuration parameters
------------------------------------------

:func:`sherlock.configure` accepts certain configuration patterns which are
individually explained in this section. Some of these configurations are global
configurations and cannot be overriden while others can be overriden at
individual lock levels.

``backend``
~~~~~~~~~~~

The `backend` parameter allows you to set which backend you would like to use
with the :class:`sherlock.Lock` class. When set to a particular backend,
instances of :class:`sherlock.Lock` will use this backend for lock
synchronization.

Basic Usage:

>>> import sherlock
>>> sherlock.configure(backend=sherlock.backends.REDIS)

Available Backends
""""""""""""""""""

To set the `backend` global configuration, you would have to choose one from
the defined backends. The defined backends are:

* Etcd: :attr:`sherlock.backends.ETCD`
* Memcache: :attr:`sherlock.backends.MEMCACHE`
* Redis: :attr:`sherlock.backends.REDIS`

``client``
~~~~~~~~~~

The `client` parameter allows you to set a custom clien object which `sherlock`
can use for connecting to the backend store. This gives you the flexibility to
connect to the backend store from the client the way you want. The provided
custom client object must be a valid client object of the supported client
libraries. If the global `backend` has been set, then the provided custom
client object must be an instance of the client library supported by that
backend. If the backend has not been set, then the custom client object must be
an instance of a valid supported client. In this case, `sherlock` will set the
backend by instrospecting the type of the provided client object.

The global default client object set using the `client` parameter will be used
only by :class:`sherlock.Lock` instances. Other :ref:`backend-specific-locks`
will either use the provided client object at the time of instantiating the
lock object of their types or will default to creating a simple client object
by themselves for their backend store, which will assume that their backend
store is running on localhost.

Example:

>>> import redis
>>> import sherlock
>>>
>>> # Configure just the backend
>>> sherlock.configure(backend=sherlock.backends.REDIS)
>>>
>>> # Configure the global client object. This sets the client for all the
>>> # locks.
>>> sherlock.configure(client=redis.StrictRedis())

And when the provided client object does not match the supported library for
the set backend:

>>> import etcd
>>> import sherlock
>>>
>>> sherlock.configure(backend=sherlock.backends.REDIS)
>>> sherlock.configure(client=etcd.Client())
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/vkapoor/Development/sherlock/sherlock/__init__.py", line 148, in configure
    _configuration.update(**kwargs)
  File "/Users/vkapoor/Development/sherlock/sherlock/__init__.py", line 250, in update
    setattr(self, key, val)
  File "/Users/vkapoor/Development/sherlock/sherlock/__init__.py", line 214, in client
    self.backend['name']))
ValueError: Only a client of the redis library can be used when using REDIS as the backend store option.

And when the backend is not configured:

>>> import redis
>>> import sherlock
>>>
>>> # Congiure just the client, this will configure the backend to
>>> # sherlock.backends.REDIS automatically.
>>> sherlock.configure(client=redis.StrictRedis())

And when the client object passed as argument for client parameter is not a
valid client object at all:

>>> import sherlock
>>> sherlock.configure(client=object())
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/vkapoor/Development/sherlock/sherlock/__init__.py", line 148, in configure
    _configuration.update(**kwargs)
  File "/Users/vkapoor/Development/sherlock/sherlock/__init__.py", line 250, in update
    setattr(self, key, val)
  File "/Users/vkapoor/Development/sherlock/sherlock/__init__.py", line 221, in client
    raise ValueError('The provided object is not a valid client'
ValueError: The provided object is not a valid client object. Client objects can only be instances of redis library's client class, python-etcd library's client class or pylibmc library's client class.

``namespace``
~~~~~~~~~~~~~

The ``namespace`` parameter allows you to configure :mod:`sherlock` to set keys
for synchronizing locks with a namespace so that if you are using the same
datastore for something else, the keys set by locks don't conflict with your
other keys set by your application.

In case of Redis and Memcached, the name of your locks are prepended with
``NAMESPACE_`` (where ``NAMESPACE`` is the namespace set by you). In case of
Etcd, a directory with the name same as the ``NAMESPACE`` you provided is
created and the locks are created in that directory.

By default, :mod:`sherlock` does not namespace the keys set for locks.

``expire``
~~~~~~~~~~

This parameter can be used to set the expiry of locks.

This parameter's value defaults to ``60 seconds``.

Example:

>>> import sherlock
>>>
>>> # Configure locks to expire after 2 seconds
>>> sherlock.configure(expire=2)
>>>
>>> lock = sherlock.Lock('my_lock')
>>>
>>> # Acquire the lock
>>> lock.acquire()
True
>>>
>>> # Sleep for 2 seconds to let the lock expire
>>> time.sleep(2)
>>>
>>> # Acquire the lock
>>> lock.acquire()
True

``timeout``
~~~~~~~~~~~

This parameter can be used to set after how much time should :mod:`sherlock`
stop trying to acquire an already acquired lock.

This parameter's value defaults to ``10 seconds``.

Example:

>>> import sherlock
>>>
>>> # Configure locks to timeout after 2 seconds while trying to acquire an
>>> # already acquired lock
>>> sherlock.configure(timeout=2, expire=10)
>>>
>>> lock = sherlock.Lock('my_lock')
>>>
>>> # Acquire the lock
>>> lock.acquire()
True
>>>
>>> # Acquire the lock again and let the timeout elapse
>>> lock.acquire()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "sherlock/lock.py", line 170, in acquire
    'lock.' % self.timeout)
sherlock.lock.LockTimeoutException: Timeout elapsed after 2 seconds while trying to acquiring lock.

``retry_interval``
~~~~~~~~~~~~~~~~~~

This parameter can be used to set after how much time should :mod:`sherlock`
try to acquire lock after failing to acquire it. For example, a log has already
been acquired, then when another lock object tries to acquire the same lock,
it fails. This parameter sets the time interval for which we should sleep
before retrying to acquire the lock.

This parameter can be set to 0 to continuously try acquiring the lock. But that
will also mean that you are bombarding your datastore with requests one after
another.

This parameter's value defaults to ``0.1 seconds (100 milliseconds)``.

Generic Locks
+++++++++++++

:mod:`sherlock` provides generic locks that can be globally configured to use a
specific backend, so that most of your application code does not have to care
about which backend you are using for lock synchronization and makes it easy
to change backend without changing a ton of code.

.. autoclass:: sherlock.Lock
    :members:
    :inherited-members:

.. _backend-specific-locks:

Backend Specific Locks
++++++++++++++++++++++

:mod:`sherlock` provides backend specific Lock classes as well which can be optionally
used to use different backend than a globally configured backend. These locks
have the same interface and semantics as :class:`sherlock.Lock`.

Redis based Locks
-----------------

.. autoclass:: sherlock.RedisLock
    :members:
    :inherited-members:

Etcd based Locks
----------------

.. autoclass:: sherlock.EtcdLock
    :members:
    :inherited-members:

Memcached based Locks
---------------------

.. autoclass:: sherlock.MCLock
    :members:
    :inherited-members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

