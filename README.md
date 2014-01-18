# distributedlock

This project aims at providing easy to use API for acquiring distributed
inter-process locks and at the same time being backend agnostic.

## Features

* API similar to standard library's Lock.
* Support for With statement.
* Backend agnostic: supports Etcd, Zookeeper, Redis, Memcached. Can be extended
  work with other DBs as well.
* Works well with Gevent, Tornado, Twisted, Multithreading, Multiprocessing.
