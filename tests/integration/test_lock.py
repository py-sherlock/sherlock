'''
    Integration tests for backend locks.
'''

import etcd
import kubernetes.client
import kubernetes.client.exceptions
import kubernetes.config
import os
import pylibmc
import redis
import sherlock
import time
import unittest


class TestRedisLock(unittest.TestCase):

    def setUp(self):
        try:
            self.client = redis.StrictRedis(
                host=os.getenv('REDIS_HOST', 'redis'),
            )
        except Exception as err:
            print(str(err))
            raise Exception('You must have Redis server running on localhost '
                            'to be able to run integration tests.')
        self.lock_name = 'test_lock'

    def test_acquire(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name).decode('UTF-8'),
                         str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client,
                                  namespace='ns')
        self.assertTrue(lock._acquire())
        self.assertEqual(
            self.client.get('ns_%s' % self.lock_name).decode('UTF-8'),
            str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.RedisLock(self.lock_name, client=self.client)
        lock2 = sherlock.RedisLock(self.lock_name, client=self.client)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client, expire=1)
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_acquire_check_expire_is_not_set(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client,
                                  expire=None)
        lock.acquire()
        time.sleep(2)
        self.assertTrue(self.client.ttl(self.lock_name) < 0)

    def test_release(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client)
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get(self.lock_name), None)

    def test_release_with_namespace(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client,
                                  namespace='ns')
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get('ns_%s' % self.lock_name), None)

    def test_release_own_only(self):
        lock1 = sherlock.RedisLock(self.lock_name, client=self.client)
        lock2 = sherlock.RedisLock(self.lock_name, client=self.client)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.lock.RedisLock(self.lock_name, client=self.client)
        lock.acquire()
        self.assertEqual(self.client.get(self.lock_name).decode('UTF-8'),
                         str(lock._owner))

        del lock
        self.assertEqual(self.client.get(self.lock_name), None)

    def tearDown(self):
        self.client.delete(self.lock_name)
        self.client.delete('ns_%s' % self.lock_name)


class TestEtcdLock(unittest.TestCase):

    def setUp(self):
        self.client = etcd.Client(host=os.getenv('ETCD_HOST', 'etcd'))
        self.lock_name = 'test_lock'

    def test_acquire(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name).value,
                         str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client,
                                 namespace='ns')
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get('/ns/%s' % self.lock_name).value,
                         str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.EtcdLock(self.lock_name, client=self.client)
        lock2 = sherlock.EtcdLock(self.lock_name, client=self.client)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client, expire=1)
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_acquire_check_expire_is_not_set(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client,
                                 expire=None)
        lock.acquire()
        time.sleep(2)
        self.assertEquals(self.client.get(self.lock_name).ttl, None)

    def test_release(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client)
        lock._acquire()
        lock._release()
        self.assertRaises(etcd.EtcdKeyNotFound, self.client.get, self.lock_name)

    def test_release_with_namespace(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client,
                                 namespace='ns')
        lock._acquire()
        lock._release()
        self.assertRaises(etcd.EtcdKeyNotFound, self.client.get, '/ns/%s' % self.lock_name)

    def test_release_own_only(self):
        lock1 = sherlock.EtcdLock(self.lock_name, client=self.client)
        lock2 = sherlock.EtcdLock(self.lock_name, client=self.client)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.lock.EtcdLock(self.lock_name, client=self.client)
        lock.acquire()
        self.assertEqual(self.client.get(self.lock_name).value, str(lock._owner))

        del lock
        self.assertRaises(etcd.EtcdKeyNotFound, self.client.get, self.lock_name)

    def tearDown(self):
        try:
            self.client.delete(self.lock_name)
        except etcd.EtcdKeyNotFound:
            pass
        try:
            self.client.delete('/ns/%s' % self.lock_name)
        except etcd.EtcdKeyNotFound:
            pass

class TestMCLock(unittest.TestCase):

    def setUp(self):
        self.client = pylibmc.Client(
            [os.getenv('MEMCACHED_HOST', 'memcached')],
            binary=True,
        )
        self.lock_name = 'test_lock'

    def test_acquire(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name), str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client,
                               namespace='ns')
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get('ns_%s' % self.lock_name),
                         str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.MCLock(self.lock_name, client=self.client)
        lock2 = sherlock.MCLock(self.lock_name, client=self.client)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client, expire=1)
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_release(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client)
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get(self.lock_name), None)

    def test_release_with_namespace(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client,
                               namespace='ns')
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get('ns_%s' % self.lock_name), None)

    def test_release_own_only(self):
        lock1 = sherlock.MCLock(self.lock_name, client=self.client)
        lock2 = sherlock.MCLock(self.lock_name, client=self.client)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.lock.MCLock(self.lock_name, client=self.client)
        lock.acquire()
        self.assertEqual(self.client.get(self.lock_name), str(lock._owner))

        del lock
        self.assertEqual(self.client.get(self.lock_name), None)

    def tearDown(self):
        self.client.delete(self.lock_name)
        self.client.delete('ns_%s' % self.lock_name)


class TestKubernetesLock(unittest.TestCase):

    def setUp(self):
        kubernetes.config.load_config()
        self.client = kubernetes.client.CoordinationV1Api()
        self.lock_name = 'test-lock'
        self.k8s_namespace = 'default'

    def test_acquire(self):
        lock = sherlock.KubernetesLock(
            self.lock_name, self.k8s_namespace)
        self.assertTrue(lock._acquire())
        lease = self.client.read_namespaced_lease(
            name=self.lock_name,
            namespace=self.k8s_namespace,
        )
        self.assertEqual(lease.spec.holder_identity, str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            namespace='ns',
        )
        self.assertTrue(lock._acquire())
        lease = self.client.read_namespaced_lease(
            name=f'ns-{self.lock_name}',
            namespace=self.k8s_namespace,
        )
        self.assertEqual(lease.spec.holder_identity, str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.KubernetesLock(
            self.lock_name, self.k8s_namespace)
        lock2 = sherlock.KubernetesLock(
            self.lock_name, self.k8s_namespace)
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=1,
        )
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_acquire_check_expire_is_not_set(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=None,
        )
        lock.acquire()
        time.sleep(2)
        lease = self.client.read_namespaced_lease(
            name=self.lock_name,
            namespace=self.k8s_namespace,
        )
        self.assertIsNone(lease.spec.lease_duration_seconds)
        self.assertTrue(lock.locked())

    def test_release(self):
        lock = sherlock.KubernetesLock(
            self.lock_name, self.k8s_namespace)
        lock._acquire()
        lock._release()
        with self.assertRaises(kubernetes.client.exceptions.ApiException) as cm:
            self.client.read_namespaced_lease(
                name=self.lock_name,
                namespace=self.k8s_namespace,
            )
        self.assertEqual(cm.exception.reason, 'Not Found')

    def test_release_with_namespace(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            namespace='ns',
        )
        lock._acquire()
        lock._release()
        # self.assertEqual(self.client.get('ns_%s' % self.lock_name), None)

    def test_release_own_only(self):
        lock1 = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
        lock2 = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.KubernetesLock(
            self.lock_name, self.k8s_namespace, client=self.client,
        )
        lock.acquire()
        lease = self.client.read_namespaced_lease(
            name=self.lock_name,
            namespace=self.k8s_namespace,
        )
        self.assertEqual(lease.spec.holder_identity, str(lock._owner))

        del lock
        with self.assertRaises(kubernetes.client.exceptions.ApiException) as cm:
            self.client.read_namespaced_lease(
                name=self.lock_name,
                namespace=self.k8s_namespace,
            )
        self.assertEqual(cm.exception.reason, 'Not Found')

    def tearDown(self):
        try:
            self.client.delete_namespaced_lease(
                name=self.lock_name,
                namespace=self.k8s_namespace,
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason != 'Not Found':
                raise exc
        try:
            self.client.delete_namespaced_lease(
                name=f'ns-{self.lock_name}',
                namespace=self.k8s_namespace,
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason != 'Not Found':
                raise exc
