.. role:: python(code)
   :language: python

CHANGELOG
#########

Development Version
*******************

0.4.0
*****

Breaking Changes
================

* Drop support for :python:`python<3.7`

New Features
============
* Add :python:`KubernetesLock` backend
* Add :python:`FileLock` backend
* Install backend specific dependencies with extras `#59`_
* Add python`.renew()` method to all backends `#61`_

.. _#59: https://github.com/py-sherlock/sherlock/pull/59
.. _#61: https://github.com/py-sherlock/sherlock/pull/61

Bug Fixes
=========
* Use :python:`ARGV` in Redis Lua scripts to add RedisCluster compatibility `#31`_
* :python:`redis>=2.10.6` client won't work with :python:`sherlock<=0.3.2` `#32`_
* :python:`timeout=0` doesn't work as expected with :python:`RedisLock` `#60`_

.. _#31: https://github.com/vaidik/sherlock/issues/31
.. _#32: https://github.com/vaidik/sherlock/issues/32
.. _#60: https://github.com/py-sherlock/sherlock/pull/60

0.3.2
*****

Bug Fixes
=========
* :python:`redis>=2.10.6` client won't work with :python:`sherlock<=0.3.1` `#32`_

.. _#32: https://github.com/vaidik/sherlock/issues/32

0.3.1
*****

Bug Fixes
=========
* Python 3 support for :python:`sherlock`

0.3.0
*****

Bug Fixes
=========
* :python:`sherlock.Lock` should use globally configured client object.
