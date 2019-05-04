'''
    Tests for all sorts of locks.
'''

import sherlock
import unittest

from sherlock.recipes.lamport_bakery import LamportLock

# import reload in Python 3
try:
    reload
except NameError:
    try:
        from importlib import reload
    except ModuleNotFoundError:
        from implib import reload


#class TestBaseLock(unittest.TestCase):
#
#    def test_init_uses_global_defaults(self):
#        sherlock.configure(namespace='new_namespace')
#        lock = sherlock.lock.BaseLock('lockname')
#        self.assertEqual(lock.namespace, 'new_namespace')
#
#    def test_init_does_not_use_global_default_for_client_obj(self):
#        client_obj = etcd.Client()
#        sherlock.configure(client=client_obj)
#        lock = sherlock.lock.BaseLock('lockname')
#        self.assertNotEqual(lock.client, client_obj)
#
#    def test__locked_raises_not_implemented_error(self):
#        def _test(): sherlock.lock.BaseLock('')._locked
#        self.assertRaises(NotImplementedError, _test)
#
#    def test_locked_raises_not_implemented_error(self):
#        self.assertRaises(NotImplementedError,
#                          sherlock.lock.BaseLock('').locked)
#
#    def test__acquire_raises_not_implemented_error(self):
#        self.assertRaises(NotImplementedError,
#                          sherlock.lock.BaseLock('')._acquire)
#
#    def test_acquire_raises_not_implemented_error(self):
#        self.assertRaises(NotImplementedError,
#                          sherlock.lock.BaseLock('').acquire)
#
#    def test__release_raises_not_implemented_error(self):
#        self.assertRaises(NotImplementedError,
#                          sherlock.lock.BaseLock('')._release)
#
#    def test_release_raises_not_implemented_error(self):
#        self.assertRaises(NotImplementedError,
#                          sherlock.lock.BaseLock('').release)
#
#    def test_acquire_acquires_blocking_lock(self):
#        lock = sherlock.lock.BaseLock('')
#        lock._acquire = Mock(return_value=True)
#        self.assertTrue(lock.acquire())
#
#    def test_acquire_acquires_non_blocking_lock(self):
#        lock = sherlock.lock.BaseLock('123')
#        lock._acquire = Mock(return_value=True)
#        self.assertTrue(lock.acquire())
#
#    def test_acquire_obeys_timeout(self):
#        lock = sherlock.lock.BaseLock('123', timeout=1)
#        lock._acquire = Mock(return_value=False)
#        self.assertRaises(sherlock.LockTimeoutException, lock.acquire)
#
#    def test_acquire_obeys_retry_interval(self):
#        lock = sherlock.lock.BaseLock('123', timeout=0.5,
#                                             retry_interval=0.1)
#        lock._acquire = Mock(return_value=False)
#        try:
#            lock.acquire()
#        except sherlock.LockTimeoutException:
#            pass
#        self.assertEqual(lock._acquire.call_count, 6)
#
#    def test_deleting_lock_object_releases_the_lock(self):
#        lock = sherlock.lock.BaseLock('123')
#        release_func = Mock()
#        lock.release = release_func
#        del lock
#        self.assertTrue(release_func.called)


class TestLamportLock(unittest.TestCase):

    def setUp(self):
        reload(sherlock)

    def test_not_passing_client_and_backend_should_raise_error(self):
        def _test():
            LamportLock('lock')

        self.assertRaises(ValueError, _test)

    def test_default_client_for_cassandra(self):
        lock = LamportLock('lock', backend=sherlock.backends.CASSANDRA)
        self.assertTrue(isinstance(
            lock.client,
            sherlock.backends.CASSANDRA['client_class']))

    def test_backend_must_be_allowed(self):
        def _test():
            LamportLock(
                'lock',
                backend=sherlock.backends.ETCD)
        self.assertRaises(ValueError, _test)

        # Should not raise any exception
        lock = LamportLock(
            'lock',
            backend=sherlock.backends.CASSANDRA)
        self.assertTrue(
            isinstance(lock.client,
                       sherlock.backends.CASSANDRA['client_class']))

    def test_client_must_match_specified_backend_type(self):
        def _test():
            LamportLock(
                'lock',
                backend=sherlock.backends.CASSANDRA,
                client=object())
        self.assertRaises(ValueError, _test)

        # Should not raise any exception
        LamportLock(
            'lock',
            backend=sherlock.backends.CASSANDRA,
            client=dict())

    def test_client_must_match_one_of_allowed_backend_types(self):
        def _test():
            LamportLock(
                'lock',
                client=object())
        self.assertRaises(ValueError, _test)

        # Should not raise any exception
        LamportLock(
            'lock',
            client=dict())
