'''
    Integration tests for backend locks.
'''

import etcd
import pylibmc
import redis
import sherlock
import time
import unittest


class TestRedisLock(unittest.TestCase):

    def setUp(self):
        try:
            self.client = redis.StrictRedis()
        except Exception, err:
            print str(err)
            raise Exception('You must have Redis server running on localhost '
                            'to be able to run integration tests.')
        self.lock_name = 'test_lock'

    def test_acquire(self):
        lock = sherlock.RedisLock(self.lock_name)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name), str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.RedisLock(self.lock_name, namespace='ns')
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get('ns_%s' % self.lock_name),
                         str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.RedisLock(self.lock_name)
        lock2 = sherlock.RedisLock(self.lock_name)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.RedisLock(self.lock_name, expire=1)
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_release(self):
        lock = sherlock.RedisLock(self.lock_name)
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get(self.lock_name), None)

    def test_release_with_namespace(self):
        lock = sherlock.RedisLock(self.lock_name, namespace='ns')
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get('ns_%s' % self.lock_name), None)

    def test_release_own_only(self):
        lock1 = sherlock.RedisLock(self.lock_name)
        lock2 = sherlock.RedisLock(self.lock_name)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.RedisLock(self.lock_name)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def tearDown(self):
        self.client.delete(self.lock_name)
        self.client.delete('ns_%s' % self.lock_name)


class TestEtcdLock(unittest.TestCase):

    def setUp(self):
        self.client = etcd.Client()
        self.lock_name = 'test_lock'

    def test_acquire(self):
        lock = sherlock.EtcdLock(self.lock_name)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name).value,
                         str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.EtcdLock(self.lock_name, namespace='ns')
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get('/ns/%s' % self.lock_name).value,
                         str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.EtcdLock(self.lock_name)
        lock2 = sherlock.EtcdLock(self.lock_name)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.EtcdLock(self.lock_name, expire=1)
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_release(self):
        lock = sherlock.EtcdLock(self.lock_name)
        lock._acquire()
        lock._release()
        self.assertRaises(KeyError, self.client.get, self.lock_name)

    def test_release_with_namespace(self):
        lock = sherlock.EtcdLock(self.lock_name, namespace='ns')
        lock._acquire()
        lock._release()
        self.assertRaises(KeyError, self.client.get, '/ns/%s' % self.lock_name)

    def test_release_own_only(self):
        lock1 = sherlock.EtcdLock(self.lock_name)
        lock2 = sherlock.EtcdLock(self.lock_name)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.EtcdLock(self.lock_name)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def tearDown(self):
        try:
            self.client.delete(self.lock_name)
        except KeyError:
            pass
        try:
            self.client.delete('/ns/%s' % self.lock_name)
        except KeyError:
            pass

class TestMCLock(unittest.TestCase):

    def setUp(self):
        self.client = pylibmc.Client(['localhost'], binary=True)
        self.lock_name = 'test_lock'

    def test_acquire(self):
        lock = sherlock.MCLock(self.lock_name)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name), str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.MCLock(self.lock_name, namespace='ns')
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get('ns_%s' % self.lock_name),
                         str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.MCLock(self.lock_name)
        lock2 = sherlock.MCLock(self.lock_name)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.MCLock(self.lock_name, expire=1)
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_release(self):
        lock = sherlock.MCLock(self.lock_name)
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get(self.lock_name), None)

    def test_release_with_namespace(self):
        lock = sherlock.MCLock(self.lock_name, namespace='ns')
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get('ns_%s' % self.lock_name), None)

    def test_release_own_only(self):
        lock1 = sherlock.MCLock(self.lock_name)
        lock2 = sherlock.MCLock(self.lock_name)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.MCLock(self.lock_name)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def tearDown(self):
        self.client.delete(self.lock_name)
        self.client.delete('ns_%s' % self.lock_name)