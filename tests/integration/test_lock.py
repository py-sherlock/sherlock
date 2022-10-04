"""
    Integration tests for backend locks.
"""

import datetime
import json
import os
import pathlib
import time
import unittest
from unittest.mock import patch

import etcd
import kubernetes.client
import kubernetes.client.exceptions
import kubernetes.config
import pylibmc
import redis

import sherlock


class TestRedisLock(unittest.TestCase):
    def setUp(self):
        try:
            self.client = redis.StrictRedis(
                host=os.getenv("REDIS_HOST", "redis"),
            )
        except Exception as err:
            print(str(err))
            raise Exception(
                "You must have Redis server running on localhost "
                "to be able to run integration tests."
            )
        self.lock_name = "test_lock"

    def test_acquire(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())
        self.assertEqual(
            self.client.get(self.lock_name).decode("UTF-8"), str(lock._owner)
        )

    def test_acquire_with_namespace(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client, namespace="ns")
        self.assertTrue(lock._acquire())
        self.assertEqual(
            self.client.get("ns_%s" % self.lock_name).decode("UTF-8"), str(lock._owner)
        )

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
        lock = sherlock.RedisLock(self.lock_name, client=self.client, expire=None)
        lock.acquire()
        time.sleep(2)
        self.assertTrue(self.client.ttl(self.lock_name) < 0)

    def test_release(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client)
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get(self.lock_name), None)

    def test_release_with_namespace(self):
        lock = sherlock.RedisLock(self.lock_name, client=self.client, namespace="ns")
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get("ns_%s" % self.lock_name), None)

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
        self.assertEqual(
            self.client.get(self.lock_name).decode("UTF-8"), str(lock._owner)
        )

        del lock
        self.assertEqual(self.client.get(self.lock_name), None)

    def test_renew(self):
        lock = sherlock.lock.RedisLock(
            self.lock_name,
            client=self.client,
            expire=3600
        )
        self.assertTrue(lock.acquire())
        lock.renew()

    def test_renew_expired(self):
        lock = sherlock.RedisLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        self.assertTrue(lock.acquire())
        time.sleep(2)

        self.assertFalse(lock.renew())

    def test_renew_owner_collision(self):
        lock_1 = sherlock.RedisLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock_2 = sherlock.RedisLock(
            self.lock_name,
            client=self.client,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(1)
        self.assertTrue(lock_2.acquire())

        self.assertFalse(lock_1.renew())

    def test_renew_before_acquire(self):
        lock = sherlock.RedisLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        with self.assertRaisesRegex(sherlock.LockException, "Lock was not set by this process."):
            lock.renew()

    def tearDown(self):
        self.client.delete(self.lock_name)
        self.client.delete("ns_%s" % self.lock_name)


class TestEtcdLock(unittest.TestCase):
    def setUp(self):
        self.client = etcd.Client(host=os.getenv("ETCD_HOST", "etcd"))
        self.lock_name = "test_lock"

    def test_acquire(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name).value, str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client, namespace="ns")
        self.assertTrue(lock._acquire())
        self.assertEqual(
            self.client.get("/ns/%s" % self.lock_name).value, str(lock._owner)
        )

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
        lock = sherlock.EtcdLock(self.lock_name, client=self.client, expire=None)
        lock.acquire()
        time.sleep(2)
        self.assertEquals(self.client.get(self.lock_name).ttl, None)

    def test_release(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client)
        lock._acquire()
        lock._release()
        self.assertRaises(etcd.EtcdKeyNotFound, self.client.get, self.lock_name)

    def test_release_with_namespace(self):
        lock = sherlock.EtcdLock(self.lock_name, client=self.client, namespace="ns")
        lock._acquire()
        lock._release()
        self.assertRaises(
            etcd.EtcdKeyNotFound, self.client.get, "/ns/%s" % self.lock_name
        )

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

    def test_renew(self):
        lock = sherlock.lock.EtcdLock(
            self.lock_name,
            client=self.client,
            expire=3600
        )
        self.assertTrue(lock.acquire())
        lock.renew()

    def test_renew_expired(self):
        lock = sherlock.EtcdLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        self.assertTrue(lock.acquire())
        time.sleep(2)

        self.assertFalse(lock.renew())

    def test_renew_owner_collision(self):
        lock_1 = sherlock.EtcdLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock_2 = sherlock.EtcdLock(
            self.lock_name,
            client=self.client,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(1)
        self.assertTrue(lock_2.acquire())

        self.assertFalse(lock_1.renew())

    def test_renew_before_acquire(self):
        lock = sherlock.EtcdLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        with self.assertRaisesRegex(sherlock.LockException, "Lock was not set by this process."):
            lock.renew()

    def tearDown(self):
        try:
            self.client.delete(self.lock_name)
        except etcd.EtcdKeyNotFound:
            pass
        try:
            self.client.delete("/ns/%s" % self.lock_name)
        except etcd.EtcdKeyNotFound:
            pass


class TestMCLock(unittest.TestCase):
    def setUp(self):
        self.client = pylibmc.Client(
            [os.getenv("MEMCACHED_HOST", "memcached")],
            binary=True,
        )
        self.lock_name = "test_lock"

    def test_acquire(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get(self.lock_name), str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.MCLock(self.lock_name, client=self.client, namespace="ns")
        self.assertTrue(lock._acquire())
        self.assertEqual(self.client.get("ns_%s" % self.lock_name), str(lock._owner))

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
        lock = sherlock.MCLock(self.lock_name, client=self.client, namespace="ns")
        lock._acquire()
        lock._release()
        self.assertEqual(self.client.get("ns_%s" % self.lock_name), None)

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

    def test_renew(self):
        lock = sherlock.lock.MCLock(
            self.lock_name,
            client=self.client,
            expire=3600
        )
        self.assertTrue(lock.acquire())
        lock.renew()

    def test_renew_expired(self):
        lock = sherlock.lock.MCLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        self.assertTrue(lock.acquire())
        time.sleep(1)
        self.assertFalse(lock.renew())

    def test_renew_owner_collision(self):
        lock_1 = sherlock.lock.MCLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock_2 = sherlock.lock.MCLock(
            self.lock_name,
            client=self.client,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(1)
        self.assertTrue(lock_2.acquire())

        self.assertFalse(lock_1.renew())

    def test_renew_before_acquire(self):
        lock = sherlock.lock.MCLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        with self.assertRaisesRegex(sherlock.LockException, "Lock was not set by this process."):
            lock.renew()

    def tearDown(self):
        self.client.delete(self.lock_name)
        self.client.delete("ns_%s" % self.lock_name)


class TestKubernetesLock(unittest.TestCase):
    def setUp(self):
        kubernetes.config.load_kube_config(
            config_file=os.environ["KUBECONFIG"],
        )
        kubernetes.config.load_config
        self.client = kubernetes.client.CoordinationV1Api()
        self.lock_name = "test-lock"
        self.k8s_namespace = "default"

    def test_acquire(self):
        lock = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
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
            namespace="ns",
        )
        self.assertTrue(lock._acquire())
        lease = self.client.read_namespaced_lease(
            name=f"ns-{self.lock_name}",
            namespace=self.k8s_namespace,
        )
        self.assertEqual(lease.spec.holder_identity, str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
        lock2 = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
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

    def test_acquire_expired_lock(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=1,
        )
        lock.acquire()
        lease_1 = self.client.read_namespaced_lease(
            name=self.lock_name,
            namespace=self.k8s_namespace,
        )
        time.sleep(2)

        # We can acquire the Lock again after it
        # expires.
        self.assertTrue(lock.acquire())

        lease_2 = self.client.read_namespaced_lease(
            name=self.lock_name,
            namespace=self.k8s_namespace,
        )

        # New Lease has new owner and new owner is not the same
        # as old owner.
        self.assertEqual(lease_2.spec.holder_identity, str(lock._owner))
        self.assertNotEqual(
            lease_1.spec.holder_identity,
            lease_2.spec.holder_identity,
        )

    @patch("sherlock.lock.uuid.uuid4")
    def test_acquire_owner_collison(self, mock_uuid4):
        mock_uuid4.return_value = b"fake-uuid"

        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=None,
        )
        self.assertTrue(lock.acquire())
        self.assertFalse(lock.acquire(blocking=False))

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
        lock = sherlock.KubernetesLock(self.lock_name, self.k8s_namespace)
        lock._acquire()
        lock._release()
        with self.assertRaises(kubernetes.client.exceptions.ApiException) as cm:
            self.client.read_namespaced_lease(
                name=self.lock_name,
                namespace=self.k8s_namespace,
            )
        self.assertEqual(cm.exception.reason, "Not Found")

    def test_release_with_namespace(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            namespace="ns",
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
            self.lock_name,
            self.k8s_namespace,
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
        self.assertEqual(cm.exception.reason, "Not Found")

    def test_release_lock_that_no_longer_exists(self):
        lock_1 = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=1,
        )
        lock_2 = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(2)
        self.assertTrue(lock_2.acquire())
        lock_2.release()

        # Releasing a Lock has been removed should be fine.
        self.assertIsNone(lock_1.release())

    def test_renew(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=3600
        )
        self.assertTrue(lock.acquire())
        first_expiry_time = lock._expiry_time(lock._get_lease())
        lock.renew()
        second_expiry_time = lock._expiry_time(lock._get_lease())
        self.assertGreater(second_expiry_time, first_expiry_time)

    def test_renew_expired(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=1
        )
        self.assertTrue(lock.acquire())
        first_expiry_time = lock._expiry_time(lock._get_lease())

        time.sleep(1)
        self.assertFalse(lock.renew())

        second_expiry_time = lock._expiry_time(lock._get_lease())
        self.assertEqual(second_expiry_time, first_expiry_time)

    def test_renew_owner_collision(self):
        lock_1 = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=1,
        )
        lock_2 = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(1)
        self.assertTrue(lock_2.acquire())

        self.assertFalse(lock_1.renew())

    def test_renew_before_acquire(self):
        lock = sherlock.KubernetesLock(
            self.lock_name,
            self.k8s_namespace,
            expire=1
        )
        with self.assertRaisesRegex(sherlock.LockException, "Lock was not set by this process."):
            lock.renew()

    def tearDown(self):
        try:
            self.client.delete_namespaced_lease(
                name=self.lock_name,
                namespace=self.k8s_namespace,
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason != "Not Found":
                raise exc
        try:
            self.client.delete_namespaced_lease(
                name=f"ns-{self.lock_name}",
                namespace=self.k8s_namespace,
            )
        except kubernetes.client.exceptions.ApiException as exc:
            if exc.reason != "Not Found":
                raise exc


class TestFileLock(unittest.TestCase):
    def setUp(self):
        self.client = pathlib.Path("/tmp/sherlock")
        self.lock_name = "test-lock"
        self.k8s_namespace = "default"

    def _load_file(self, key_name):
        with (self.client / key_name).with_suffix(".json").open("r") as f:
            return json.load(f)

    def test_acquire(self):
        lock = sherlock.FileLock(self.lock_name, client=self.client)
        self.assertTrue(lock._acquire())

        key = self.lock_name
        file = self._load_file(key)
        self.assertEqual(file["owner"], str(lock._owner))

    def test_acquire_with_namespace(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            namespace="ns",
        )
        self.assertTrue(lock._acquire())
        key = f"ns_{self.lock_name}"
        file = self._load_file(key)
        self.assertEqual(file["owner"], str(lock._owner))

    def test_acquire_once_only(self):
        lock1 = sherlock.FileLock(
            self.lock_name,
            client=self.client,
        )
        lock2 = sherlock.FileLock(
            self.lock_name,
            client=self.client,
        )
        self.assertTrue(lock1._acquire())
        self.assertFalse(lock2._acquire())

    def test_acquire_check_expiry(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock.acquire()
        time.sleep(2)
        self.assertFalse(lock.locked())

    def test_acquire_locked(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=None,
        )
        self.assertTrue(lock.acquire())
        self.assertFalse(lock._acquire())

    def test_acquire_expired_lock(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock.acquire()
        file_1 = self._load_file(self.lock_name)
        time.sleep(2)

        # We can acquire the Lock again after it
        # expires.
        self.assertTrue(lock.acquire())

        file_2 = self._load_file(self.lock_name)

        # New file has new owner and new owner is not the same
        # as old owner.
        self.assertEqual(file_2["owner"], str(lock._owner))
        self.assertNotEqual(file_1["owner"], file_2["owner"])

    @patch("sherlock.lock.uuid.uuid4")
    def test_acquire_owner_collison(self, mock_uuid4):
        mock_uuid4.return_value = b"fake-uuid"

        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=None,
        )
        self.assertTrue(lock.acquire())
        self.assertFalse(lock.acquire(blocking=False))

    def test_acquire_check_expire_is_not_set(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=None,
        )
        lock.acquire()
        time.sleep(2)
        file = self._load_file(self.lock_name)
        self.assertEqual(
            file["expiry_time"],
            datetime.datetime.max.astimezone(datetime.timezone.utc).isoformat(),
        )
        self.assertTrue(lock.locked())

    def test_release(self):
        lock = sherlock.FileLock(self.lock_name, client=self.client)
        lock._acquire()
        lock._release()
        self.assertFalse(lock._data_file.exists())

    def test_release_with_namespace(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            namespace="ns",
        )
        lock._acquire()
        lock._release()
        self.assertFalse(lock._data_file.exists())

    def test_release_own_only(self):
        lock1 = sherlock.FileLock(self.lock_name, client=self.client)
        lock2 = sherlock.FileLock(self.lock_name, client=self.client)
        lock1._acquire()
        self.assertRaises(sherlock.LockException, lock2._release)
        lock1._release()

    def test_locked(self):
        lock = sherlock.FileLock(self.lock_name, client=self.client)
        lock._acquire()
        self.assertTrue(lock._locked)
        lock._release()
        self.assertFalse(lock._locked)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.FileLock(self.lock_name, client=self.client)

        lock.acquire()
        file = self._load_file(self.lock_name)
        self.assertEqual(file["owner"], str(lock._owner))

        data_file = lock._data_file
        del lock
        self.assertFalse(data_file.exists())

    def test_release_lock_that_no_longer_exists(self):
        lock_1 = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock_2 = sherlock.FileLock(
            self.lock_name,
            client=self.client,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(2)
        self.assertTrue(lock_2.acquire())
        lock_2.release()

        # Releasing a Lock has been removed should be fine.
        self.assertIsNone(lock_1.release())

    def test_renew(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=3600
        )
        self.assertTrue(lock.acquire())
        first_expiry_time = datetime.datetime.fromisoformat(
            self._load_file(self.lock_name)["expiry_time"]
        )
        lock.renew()
        second_expiry_time = datetime.datetime.fromisoformat(
            self._load_file(self.lock_name)["expiry_time"]
        )
        self.assertGreater(second_expiry_time, first_expiry_time)

    def test_renew_expired(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        self.assertTrue(lock.acquire())
        first_expiry_time = datetime.datetime.fromisoformat(
            self._load_file(self.lock_name)["expiry_time"]
        )

        time.sleep(1)
        self.assertFalse(lock.renew())

        second_expiry_time = datetime.datetime.fromisoformat(
            self._load_file(self.lock_name)["expiry_time"]
        )
        self.assertEqual(second_expiry_time, first_expiry_time)

    def test_renew_owner_collision(self):
        lock_1 = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=1,
        )
        lock_2 = sherlock.FileLock(
            self.lock_name,
            client=self.client,
        )
        self.assertTrue(lock_1.acquire())
        # Wait for Lock to expire
        time.sleep(1)
        self.assertTrue(lock_2.acquire())

        self.assertFalse(lock_1.renew())

    def test_renew_before_acquire(self):
        lock = sherlock.FileLock(
            self.lock_name,
            client=self.client,
            expire=1
        )
        with self.assertRaisesRegex(sherlock.LockException, "Lock was not set by this process."):
            lock.renew()


    def tearDown(self):
        for file in self.client.iterdir():
            file.unlink()
