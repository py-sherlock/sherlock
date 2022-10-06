CHANGELOG
---------

Development Version
+++++++++++++++++++

0.4.0
*****

* [BREAKING] Drop support for `python<3.7`

* [FEAT] Add `KubernetesLock` backend
* [FEAT] Add `FileLock` backend
* [FEAT] Install backend specific dependencies with extras #59_
* [FEAT] Add `.renew()` method to all backends #61_

* [BUGFIX] Use `ARGV` in Redis Lua scripts to add RedisCluster compatibility #31_
* [BUGFIX] `redis>=2.10.6` client won't work with `sherlock 0.3.1` #32_
* [BUGFIX] `timeout=0` doesn't work as expected with `RedisLock` #60_

.. _#31: https://github.com/vaidik/sherlock/issues/31
.. _#32: https://github.com/vaidik/sherlock/issues/32
.. _#59: https://github.com/py-sherlock/sherlock/pull/59
.. _#60: https://github.com/py-sherlock/sherlock/pull/60
.. _#61: https://github.com/py-sherlock/sherlock/pull/61

0.3.2
*****

* [BUGFIX] `redis>=2.10.6` client won't work with `sherlock 0.3.1` #32_

.. _#32: https://github.com/vaidik/sherlock/issues/32

0.3.1
*****

* [BUGFIX] Python 3 support for `sherlock`

0.3.0
*****

* [BUGFIX] `sherlock.Lock` should use globally configured client object.
