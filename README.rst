Sherlock: Distributed Locks with a choice of backend
====================================================

**Sherlock** is a library that provides easy-to-use distributed inter-process
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

Distributed Locks or Mutexes can help you with this. Sherlock provides the
exact same facility, with some extra goodies. It provides an easy-to-use API
that resembles standard library's `threading.Lock` semantics.

Apart from this, Sherlock gives you the flexibilty of using a backend of your
choice for managing locks.

Sherlock also makes it simple for you to extend Sherlock to use backends that
are not supported.

Features
++++++++

* API similar to standard library's `threading.Lock`. 
* Support for With statement, to cleanly acquire and release locks.
* Backend agnostic: supports `Redis`_, `Memcached`_ and `Etcd`_ as choice of
  backends.
* Extendable: can be easily extended to work with anyother of backend of choice
  by extending classes.

.. _Redis:: http://redis.io
.. _Memcached:: http://memcached.org
.. _Etcd:: http://github.com/coreos/etcd

Supported Backends and Client Libraries
+++++++++++++++++++++++++++++++++++++++

Following client libraries are supported for every supported backend:

* Redis: `redis-py`_
* Memcached: `pylibmc`_
* Etcd: `python-etcd`_

.. _redis-py:: http://github.com
.. _pylibmc:: http://github.com
.. _python-etcd:: https://github.com/jplana/python-etcd

As of now, only the above mentioned libraries are supported. Although Sherlock
takes custom client objects so that you can easily provide settings that you
want to use for that backend store, but Sherlock also checks if the provided
client object is an instance of the supported clients and accepts client
objects which pass this check, even if the APIs are the same. Sherlock might
get rid of this issue later, if need be and if there is a demand for that.

Installation
------------

Installation is simple.

.. code:: bash

    pip install sherlock

.. note:: Sherlock will install all the client libraries for all the
          supported backends.

Basic Usage
-----------

.. code-block:: python

    import sherlock
    from sherlock import Lock

    # Configure Sherlock's locks to use Redis as the backend,
    # never expire locks and retry acquiring an acquired lock after an
    # interval of 0.1 second.
    sherlock.configure(backend=sherlock.backends.REDIS,
                       expire=None,
                       retry_interval=0.1)

    # Note: configuring Sherlock to use a backend does not limit you from using
    # another backend at the same time. You can import backend specific locks
    # like RedisLock, MCLock and EtcdLock and use them just the same way you
    # use a generic lock (see below). In fact, the generic Lock provided by
    # Sherlock is just a proxy that uses these specific locks under the hood.

    # acquire a lock called my_lock
    lock = Lock('my_lock')

    # acquire a blocking lock
    lock.acquire()

    # check if the lock has been acquired or not
    lock.locked() == True

    # release the lock
    lock.release()

    # using with statement
    with Lock('my_lock'):
        '''
        do something constructive with your locked resource here
        '''
        pass

    # acquire non-blocking lock
    lock1 = Lock('my_lock')
    lock2 = Lock('my_lock')
    
    # successfully acquire lock1
    lock1.acquire()

    # try to acquire lock in a non-blocking way
    lock2.acquire(False) == True # returns False

    # try to acquire lock in a blocking way
    lock2.acquire() # blocks until lock is acquired to timeout happens

Documentation
-------------

Read the documentation availalbe on `Read The Docs`_ for more detailed usage.

.. _Read The Docs: http://sherlock.readthedocs.org/en/latest/

Tests
-----

Make sure all the services are running:

.. code:: bash

    # memcached
    memcached

    # redis-server
    redis-server

    # etcd
    wget https://github.com/coreos/etcd/releases/download/<version>/etcd-<version>-<platform>.tar.gz
    tar -zxvf etcd-<version>-<platform>.gz
    ./etcd-<version>-<platform>/etcd

Run tests like so:

.. code:: bash

    python setup.py test

Roadmap
-------

* Support for `Zookeeper`_ as backend.
* Support for `Gevent`_, `Multithreading`_ and `Multiprocessing`_.

.. _Zookeeper:: http://zookeeper.apache.org/
.. _Gevent:: http://www.gevent.org/
.. _Multithreading:: http://docs.python.org/2/library/multithreading.html
.. _Multiprocessing:: http://docs.python.org/2/library/multiprocessing.html

License
-------

See `LICENSE`_.

.. _LICENSE: http://github.com/vaidik/sherlock/blob/master/LICENSE.rst
