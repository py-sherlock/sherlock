'''
    Tests for all sorts of locks.
'''

import distributedlock
import unittest

from distributedlock import LockException, LockTimeoutException
from mock import Mock


class TestBaseLock(unittest.TestCase):

    def test_init_uses_global_defaults(self):
        distributedlock.configure(namespace='new_namespace')
        lock = distributedlock.lock.BaseLock('lockname')
        self.assertEqual(lock.namespace, 'new_namespace')

    def test_init_does_not_use_global_default_for_client_obj(self):
        client_obj = Mock()
        distributedlock.configure(client=client_obj)
        lock = distributedlock.lock.BaseLock('lockname')
        self.assertNotEqual(lock.client, client_obj)

    def test__locked_raises_not_implemented_error(self):
        def _test(): distributedlock.lock.BaseLock('')._locked
        self.assertRaises(NotImplementedError, _test)

    def test_locked_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          distributedlock.lock.BaseLock('').locked)

    def test__acquire_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          distributedlock.lock.BaseLock('')._acquire)

    def test_acquire_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          distributedlock.lock.BaseLock('').acquire)

    def test__release_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          distributedlock.lock.BaseLock('')._release)

    def test_release_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          distributedlock.lock.BaseLock('').release)

    def test_acquire_acquires_blocking_lock(self):
        lock = distributedlock.lock.BaseLock('')
        lock._acquire = Mock(return_value=True)
        self.assertTrue(lock.acquire())

    def test_acquire_acquires_non_blocking_lock(self):
        lock = distributedlock.lock.BaseLock('123')
        lock._acquire = Mock(return_value=True)
        self.assertTrue(lock.acquire())

    def test_acquire_obeys_timeout(self):
        lock = distributedlock.lock.BaseLock('123', timeout=1)
        lock._acquire = Mock(return_value=False)
        self.assertRaises(LockTimeoutException, lock.acquire)

    def test_acquire_obeys_retry_interval(self):
        lock = distributedlock.lock.BaseLock('123', timeout=0.5,
                                             retry_interval=0.1)
        lock._acquire = Mock(return_value=False)
        try:
            lock.acquire()
        except LockTimeoutException:
            pass
        self.assertEqual(lock._acquire.call_count, 6)


class TestLock(unittest.TestCase):

    def test_lock_does_not_accept_custom_client_object(self):
        self.assertRaises(TypeError, distributedlock.Lock, client=None)

    def test_lock_does_not_create_proxy_when_backend_is_not_set(self):
        distributedlock._configuration._backend = None
        distributedlock._configuration._client = None
        lock = distributedlock.Lock('')
        self.assertEquals(lock._lock_proxy, None)

        self.assertRaises(LockException, lock.acquire)
        self.assertRaises(LockException, lock.release)
        self.assertRaises(LockException, lock.locked)

    def test_lock_creates_proxy_when_backend_is_set(self):
        distributedlock._configuration.backend = distributedlock.backends.REDIS
        lock = distributedlock.Lock('')
        self.assertTrue(isinstance(lock._lock_proxy,
                                   distributedlock.RedisLock))

    def test_lock_uses_proxys_methods(self):
        distributedlock.RedisLock._acquire = Mock(return_value=True)
        distributedlock.RedisLock._release = Mock()
        distributedlock.RedisLock.locked = Mock(return_value=False)

        distributedlock._configuration.backend = distributedlock.backends.REDIS
        lock = distributedlock.Lock('')

        lock.acquire()
        self.assertTrue(distributedlock.RedisLock._acquire.called)

        lock.release()
        self.assertTrue(distributedlock.RedisLock._release.called)

        lock.locked()
        self.assertTrue(distributedlock.RedisLock.locked.called)
