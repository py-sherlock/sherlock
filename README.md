# sherlock

This project aims at providing easy to use API for acquiring distributed
inter-process locks and at the same time being backend agnostic.

## Features

* API similar to standard library's Lock.
* Support for With statement.
* Backend agnostic: supports Etcd, Redis, Memcached. Can be extended to
  work with other data stores as well.

## Coming Soon

* Support for Zookeeper
* Works with Gevent, Multithreading, Multiprocessing.
