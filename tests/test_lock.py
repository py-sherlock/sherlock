'''
    Tests for all sorts of locks.
'''

import etcd
import redis
import sherlock
import unittest
from unittest.mock import Mock

# import reload in Python 3
try:
    reload
except NameError:
    try:
        from importlib import reload
    except ModuleNotFoundError:
        from implib import reload


class TestBaseLock(unittest.TestCase):

    def test_init_uses_global_defaults(self):
        sherlock.configure(namespace='new_namespace')
        lock = sherlock.lock.BaseLock('lockname')
        self.assertEqual(lock.namespace, 'new_namespace')

    def test_init_does_not_use_global_default_for_client_obj(self):
        client_obj = etcd.Client()
        sherlock.configure(client=client_obj)
        lock = sherlock.lock.BaseLock('lockname')
        self.assertNotEqual(lock.client, client_obj)

    def test__locked_raises_not_implemented_error(self):
        def _test(): sherlock.lock.BaseLock('')._locked
        self.assertRaises(NotImplementedError, _test)

    def test_locked_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          sherlock.lock.BaseLock('').locked)

    def test__acquire_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          sherlock.lock.BaseLock('')._acquire)

    def test_acquire_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          sherlock.lock.BaseLock('').acquire)

    def test__release_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          sherlock.lock.BaseLock('')._release)

    def test_release_raises_not_implemented_error(self):
        self.assertRaises(NotImplementedError,
                          sherlock.lock.BaseLock('').release)

    def test_acquire_acquires_blocking_lock(self):
        lock = sherlock.lock.BaseLock('')
        lock._acquire = Mock(return_value=True)
        self.assertTrue(lock.acquire())

    def test_acquire_acquires_non_blocking_lock(self):
        lock = sherlock.lock.BaseLock('123')
        lock._acquire = Mock(return_value=True)
        self.assertTrue(lock.acquire())

    def test_acquire_obeys_timeout(self):
        lock = sherlock.lock.BaseLock('123', timeout=1)
        lock._acquire = Mock(return_value=False)
        self.assertRaises(sherlock.LockTimeoutException, lock.acquire)

    def test_acquire_obeys_retry_interval(self):
        lock = sherlock.lock.BaseLock('123', timeout=0.5,
                                             retry_interval=0.1)
        lock._acquire = Mock(return_value=False)
        try:
            lock.acquire()
        except sherlock.LockTimeoutException:
            pass
        self.assertEqual(lock._acquire.call_count, 6)

    def test_deleting_lock_object_releases_the_lock(self):
        lock = sherlock.lock.BaseLock('123')
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
        lock = sherlock.lock.Lock('')
        self.assertEqual(lock._lock_proxy, None)

        self.assertRaises(sherlock.lock.LockException, lock.acquire)
        self.assertRaises(sherlock.lock.LockException, lock.release)
        self.assertRaises(sherlock.lock.LockException, lock.locked)

    def test_lock_creates_proxy_when_backend_is_set(self):
        sherlock._configuration.backend = sherlock.backends.ETCD
        lock = sherlock.lock.Lock('')
        self.assertTrue(isinstance(lock._lock_proxy,
                                   sherlock.lock.EtcdLock))

    def test_lock_uses_proxys_methods(self):
        sherlock.lock.RedisLock._acquire = Mock(return_value=True)
        sherlock.lock.RedisLock._release = Mock()
        sherlock.lock.RedisLock.locked = Mock(return_value=False)

        sherlock._configuration.backend = sherlock.backends.REDIS
        lock = sherlock.lock.Lock('')

        lock.acquire()
        self.assertTrue(sherlock.lock.RedisLock._acquire.called)

        lock.release()
        self.assertTrue(sherlock.lock.RedisLock._release.called)

        lock.locked()
        self.assertTrue(sherlock.lock.RedisLock.locked.called)

    def test_lock_sets_client_object_on_lock_proxy_when_globally_configured(self):
        client = etcd.Client(host='8.8.8.8')
        sherlock.configure(client=client)
        lock = sherlock.lock.Lock('lock')
        self.assertEqual(lock._lock_proxy.client, client)


class TestRedisLock(unittest.TestCase):

    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = 'lock'
        lock = sherlock.lock.RedisLock(name)
        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = 'lock'
        lock = sherlock.lock.RedisLock(name, namespace='local_namespace')
        self.assertEqual(lock._key_name, 'local_namespace_%s' % name)

        sherlock.configure(namespace='global_namespace')
        lock = sherlock.lock.RedisLock(name)
        self.assertEqual(lock._key_name, 'global_namespace_%s' % name)


class TestEtcdLock(unittest.TestCase):

    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = 'lock'
        lock = sherlock.lock.EtcdLock(name)
        self.assertEqual(lock._key_name, '/' + name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = 'lock'
        lock = sherlock.lock.EtcdLock(name, namespace='local_namespace')
        self.assertEqual(lock._key_name, '/local_namespace/%s' % name)

        sherlock.configure(namespace='global_namespace')
        lock = sherlock.lock.EtcdLock(name)
        self.assertEqual(lock._key_name, '/global_namespace/%s' % name)


class TestMCLock(unittest.TestCase):

    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = 'lock'
        lock = sherlock.lock.MCLock(name)
        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = 'lock'
        lock = sherlock.lock.MCLock(name, namespace='local_namespace')
        self.assertEqual(lock._key_name, 'local_namespace_%s' % name)

        sherlock.configure(namespace='global_namespace')
        lock = sherlock.lock.MCLock(name)
        self.assertEqual(lock._key_name, 'global_namespace_%s' % name)


class TestKubernetesLock(unittest.TestCase):

    def setUp(self):
        reload(sherlock)
        reload(sherlock.lock)

    def test_valid_key_names_are_generated_when_namespace_not_set(self):
        name = 'lock'
        k8s_namespace = 'default'
        lock = sherlock.lock.KubernetesLock(name, k8s_namespace, client=Mock())
        self.assertEqual(lock._key_name, name)

    def test_valid_key_names_are_generated_when_namespace_is_set(self):
        name = 'lock'
        k8s_namespace = 'default'
        lock = sherlock.lock.KubernetesLock(
            name, k8s_namespace, client=Mock(), namespace='local-namespace',
        )
        self.assertEqual(lock._key_name, 'local-namespace-%s' % name)

        sherlock.configure(namespace='global-namespace')
        lock = sherlock.lock.KubernetesLock(name, k8s_namespace, client=Mock())
        self.assertEqual(lock._key_name, 'global-namespace-%s' % name)

    def test_exception_raised_when_invalid_names_set(self):
        test_cases = [
            (
                'lock_name',
                'my-k8s-namespace',
                'my-namespace',
                'lock_name must conform to RFC1123\'s definition of a DNS label for KubernetesLock'
            ),
            (
                'lock-name',
                'my_k8s_namespace',
                'my-namespace',
                'k8s_namespace must conform to RFC1123\'s definition of a DNS label for KubernetesLock'),
            (
                'lock-name',
                'my-k8s-namespace',
                'my_namespace',
                'namespace must conform to RFC1123\'s definition of a DNS label for KubernetesLock'
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
