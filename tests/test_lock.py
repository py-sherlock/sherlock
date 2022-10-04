"""
    Tests for all sorts of locks.
"""

import datetime
import pathlib
import tempfile
import unittest
from importlib import reload
from unittest.mock import Mock, patch

import etcd
import kubernetes.client
import kubernetes.client.exceptions

import sherlock


class TestBaseLock(unittest.TestCase):
    def test_init_uses_global_defaults(self):
        sherlock.configure(namespace="new_namespace")
        lock = sherlock.lock.BaseLock("lockname")
        self.assertEqual(lock.namespace, "new_namespace")

    def test_init_does_not_use_global_default_for_client_obj(self):
        client_obj = etcd.Client()
        sherlock.configure(client=client_obj)
        lock = sherlock.lock.BaseLock("lockname")
        self.assertNotEqual(lock.client, client_obj)

    def test__locked_raises_not_implemented_error(self):
        def _test():
            sherlock.lock.BaseLock("")._locked

        self.assertRaises(NotImplementedError, _test)

    def test_locked_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError, sherlock.lock.BaseLock("").locked)

    def test__acquire_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError, sherlock.lock.BaseLock("")._acquire)

    def test_acquire_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError, sherlock.lock.BaseLock("").acquire)

    def test__release_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError, sherlock.lock.BaseLock("")._release)

    def test_release_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError, sherlock.lock.BaseLock("").release)

    def test_acquire_acquires_blocking_lock(self):
        lock = sherlock.lock.BaseLock("")
        lock._acquire = Mock(return_value=True)
        self.assertTrue(lock.acquire())

    def test_acquire_acquires_non_blocking_lock(self):
        lock = sherlock.lock.BaseLock("123")
        lock._acquire = Mock(return_value=True)
        self.assertTrue(lock.acquire())

    def test_acquire_obeys_timeout(self):
        lock = sherlock.lock.BaseLock("123", timeout=1)
        lock._acquire = Mock(return_value=False)
        self.assertRaises(sherlock.LockTimeoutException, lock.acquire)

    def test_acquire_obeys_retry_interval(self):
        lock = sherlock.lock.BaseLock("123", timeout=0.5, retry_interval=0.1)
        lock._acquire = Mock(return_value=False)
        try:
            lock.acquire()
        except sherlock.LockTimeoutException:
            pass
        self.assertEqual(lock._acquire.call_count, 6)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.lock.BaseLock("123")
        release_func = Mock()
        lock.release = release_func
        del lock
        self.assertTrue(release_func.called)


class TestLock(unittest.TestCase):
    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_lock_does_not_accept_custom_client_object(self):
        self.assertRaises(TypeError, sherlock.lock.Lock, client=None)

    def test_lock_does_not_create_proxy_when_backend_is_not_set(self):
        sherlock._configuration._backend = None
        sherlock._configuration._client = None
        lock = sherlock.lock.Lock("")
        self.assertEqual(lock._lock_proxy, None)

        self.assertRaises(sherlock.lock.LockException, lock.acquire)
        self.assertRaises(sherlock.lock.LockException, lock.release)
        self.assertRaises(sherlock.lock.LockException, lock.locked)

    def test_lock_creates_proxy_when_backend_is_set(self):
        sherlock._configuration.backend = sherlock.backends.ETCD
        lock = sherlock.lock.Lock("")
        self.assertTrue(isinstance(lock._lock_proxy, sherlock.lock.EtcdLock))

    def test_lock_uses_proxys_methods(self):
        sherlock.lock.RedisLock._acquire = Mock(return_value=True)
        sherlock.lock.RedisLock._release = Mock()
        sherlock.lock.RedisLock.locked = Mock(return_value=False)

        sherlock._configuration.backend = sherlock.backends.REDIS
        lock = sherlock.lock.Lock("")

        lock.acquire()
        self.assertTrue(sherlock.lock.RedisLock._acquire.called)

        lock.release()
        self.assertTrue(sherlock.lock.RedisLock._release.called)

        lock.locked()
        self.assertTrue(sherlock.lock.RedisLock.locked.called)

    def test_lock_sets_client_object_on_lock_proxy_when_globally_configured(self):
        client = etcd.Client(host="8.8.8.8")
        sherlock.configure(client=client)
        lock = sherlock.lock.Lock("lock")
        self.assertEqual(lock._lock_proxy.client, client)


class TestRedisLock(unittest.TestCase):
    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = "lock"
        lock = sherlock.lock.RedisLock(name)
        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = "lock"
        lock = sherlock.lock.RedisLock(name, namespace="local_namespace")
        self.assertEqual(lock._key_name, "local_namespace_%s" % name)

        sherlock.configure(namespace="global_namespace")
        lock = sherlock.lock.RedisLock(name)
        self.assertEqual(lock._key_name, "global_namespace_%s" % name)


class TestEtcdLock(unittest.TestCase):
    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = "lock"
        lock = sherlock.lock.EtcdLock(name)
        self.assertEqual(lock._key_name, "/" + name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = "lock"
        lock = sherlock.lock.EtcdLock(name, namespace="local_namespace")
        self.assertEqual(lock._key_name, "/local_namespace/%s" % name)

        sherlock.configure(namespace="global_namespace")
        lock = sherlock.lock.EtcdLock(name)
        self.assertEqual(lock._key_name, "/global_namespace/%s" % name)


class TestMCLock(unittest.TestCase):
    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = "lock"
        lock = sherlock.lock.MCLock(name)
        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = "lock"
        lock = sherlock.lock.MCLock(name, namespace="local_namespace")
        self.assertEqual(lock._key_name, "local_namespace_%s" % name)

        sherlock.configure(namespace="global_namespace")
        lock = sherlock.lock.MCLock(name)
        self.assertEqual(lock._key_name, "global_namespace_%s" % name)


class TestKubernetesLock(unittest.TestCase):
    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = "lock"
        k8s_namespace = "default"
        lock = sherlock.lock.KubernetesLock(name, k8s_namespace, client=Mock())
        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = "lock"
        k8s_namespace = "default"
        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=Mock(),
            namespace="local-namespace",
        )
        self.assertEqual(lock._key_name, "local-namespace-%s" % name)

        sherlock.configure(namespace="global-namespace")
        lock = sherlock.lock.KubernetesLock(name, k8s_namespace, client=Mock())
        self.assertEqual(lock._key_name, "global-namespace-%s" % name)

    def test_exception_raised_when_invalid_names_set(self):
        test_cases = [
            (
                "lock_name",
                "my-k8s-namespace",
                "my-namespace",
                "lock_name must conform to RFC1123's definition of a DNS label for KubernetesLock",  # noqa: disable=501
            ),
            (
                "lock-name",
                "my_k8s_namespace",
                "my-namespace",
                "k8s_namespace must conform to RFC1123's definition of a DNS label for KubernetesLock",  # noqa: disable=501
            ),
            (
                "lock-name",
                "my-k8s-namespace",
                "my_namespace",
                "namespace must conform to RFC1123's definition of a DNS label for KubernetesLock",  # noqa: disable=501
            ),
        ]
        for lock_name, k8s_namespace, namespace, err_msg in test_cases:
            with self.assertRaises(ValueError) as cm:
                sherlock.lock.KubernetesLock(
                    lock_name,
                    k8s_namespace,
                    client=Mock(),
                    namespace=namespace,
                )
            self.assertEqual(cm.exception.args[0], err_msg)

            sherlock.configure(namespace=namespace)
            with self.assertRaises(ValueError) as cm:
                sherlock.lock.KubernetesLock(
                    lock_name,
                    k8s_namespace,
                    client=Mock(),
                    namespace=namespace,
                )
            self.assertEqual(cm.exception.args[0], err_msg)

    @patch("kubernetes.client.CoordinationV1Api")
    def test_acquire_create_race_condition(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        # Mock the client to reproduce the scenario where the Lease
        # does not exist when read but does when created.
        mock_client.read_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Not Found")
        )
        mock_client.create_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Conflict")
        )
        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )
        self.assertFalse(lock._acquire())

    @patch("kubernetes.client.CoordinationV1Api")
    def test_acquire_create_failed(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        # Mock the client to reproduce the scenario where the Lease
        # does not exist and we fail to create it for some other reason.
        mock_client.read_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Not Found")
        )
        mock_client.create_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Not Conflict")
        )
        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )
        self.assertRaisesRegex(
            sherlock.lock.LockException,
            "Failed to create Lock.",
            lock._acquire,
        )

    @patch("kubernetes.client.CoordinationV1Api")
    def test_acquire_get_failed(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        # Mock the client to reproduce the scenario where we fail to read the Lease
        # for some other reason other than it doesn't exist.
        mock_client.read_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Unexpected")
        )
        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )
        self.assertRaisesRegex(
            sherlock.lock.LockException,
            "Failed to read Lock.",
            lock._acquire,
        )

    @patch("kubernetes.client.CoordinationV1Api")
    def test_acquire_replaced_race_condition(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )

        now = lock._now() - datetime.timedelta(seconds=10)
        lease = kubernetes.client.V1Lease(
            metadata=kubernetes.client.V1ObjectMeta(name=name, namespace=k8s_namespace),
            spec=kubernetes.client.V1LeaseSpec(
                acquire_time=now,
                holder_identity="test-identity",
                lease_duration_seconds=1,
                renew_time=now,
            ),
        )

        # Mock the client to reproduce the scenario where we try to acquire
        # the Lock but someone beats us to it.
        mock_client.read_namespaced_lease.return_value = lease
        mock_client.replace_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Conflict")
        )

        self.assertFalse(lock._acquire())

    @patch("kubernetes.client.CoordinationV1Api")
    def test_acquire_replaced_failed(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )

        now = lock._now() - datetime.timedelta(seconds=10)
        lease = kubernetes.client.V1Lease(
            metadata=kubernetes.client.V1ObjectMeta(name=name, namespace=k8s_namespace),
            spec=kubernetes.client.V1LeaseSpec(
                acquire_time=now,
                holder_identity="test-identity",
                lease_duration_seconds=1,
                renew_time=now,
            ),
        )

        # Mock the client to reproduce the scenario where we try to acquire
        # the Lock but fail to replace the Lease for an unexpected reason.
        mock_client.read_namespaced_lease.return_value = lease
        mock_client.replace_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Unexpected")
        )

        self.assertRaisesRegex(
            sherlock.lock.LockException,
            "Failed to update Lock.",
            lock._acquire,
        )

    @patch("kubernetes.client.CoordinationV1Api")
    def test_release_delete_race_condition(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )
        lock._owner = "test-identity"

        now = lock._now() - datetime.timedelta(seconds=10)
        lease = kubernetes.client.V1Lease(
            metadata=kubernetes.client.V1ObjectMeta(name=name, namespace=k8s_namespace),
            spec=kubernetes.client.V1LeaseSpec(
                acquire_time=now,
                holder_identity=lock._owner,
                lease_duration_seconds=1,
                renew_time=now,
            ),
        )

        # Mock the client to reproduce the scenario where we try to release
        # the Lock but someone acquires it before we get a chance.
        mock_client.read_namespaced_lease.return_value = lease
        mock_client.delete_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Not Found")
        )

        # This should return without issue.
        self.assertIsNone(lock.release())

    @patch("kubernetes.client.CoordinationV1Api")
    def test_release_delete_failed(self, mock_client):
        name = "lock"
        k8s_namespace = "default"

        lock = sherlock.lock.KubernetesLock(
            name,
            k8s_namespace,
            client=mock_client,
        )
        lock._owner = "test-identity"

        now = lock._now() - datetime.timedelta(seconds=10)
        lease = kubernetes.client.V1Lease(
            metadata=kubernetes.client.V1ObjectMeta(name=name, namespace=k8s_namespace),
            spec=kubernetes.client.V1LeaseSpec(
                acquire_time=now,
                holder_identity=lock._owner,
                lease_duration_seconds=1,
                renew_time=now,
            ),
        )

        # Mock the client to reproduce the scenario where we try to release
        # the Lock but fail to delete the Lease for an unexpected reason.
        mock_client.read_namespaced_lease.return_value = lease
        mock_client.delete_namespaced_lease.side_effect = (
            kubernetes.client.exceptions.ApiException(reason="Unexpected")
        )

        self.assertRaisesRegex(
            sherlock.lock.LockException,
            "Failed to release Lock.",
            lock.release,
        )


class TestFileLock(unittest.TestCase):
    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = "lock"

        with tempfile.TemporaryDirectory() as tmpdir:
            lock = sherlock.lock.FileLock(name, client=pathlib.Path(tmpdir))

        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = "lock"

        with tempfile.TemporaryDirectory() as tmpdir:
            lock = sherlock.lock.FileLock(
                name,
                client=pathlib.Path(tmpdir),
                namespace="local_namespace",
            )

        self.assertEqual(lock._key_name, "local_namespace_%s" % name)

        sherlock.configure(namespace="global_namespace")
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = sherlock.lock.FileLock(name, client=pathlib.Path(tmpdir))
        self.assertEqual(lock._key_name, "global_namespace_%s" % name)
