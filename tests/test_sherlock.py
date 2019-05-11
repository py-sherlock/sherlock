'''
    Tests for some basic package's root level functionality.
'''

import etcd
import sherlock
import unittest

from sherlock import _Configuration
from mock import Mock

# import reload in Python 3
try:
    reload
except NameError:
    try:
        from importlib import reload
    except ModuleNotFoundError:
        from implib import reload


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        reload(sherlock)
        self.configure = _Configuration()

    def test_update_settings_raises_error_when_updating_invalid_config(self):
        # Raises error when trying to update invalid setting
        self.assertRaises(AttributeError, self.configure.update,
                          invalid_arg='val')

    def test_updates_valid_settings(self):
        # Updates valid setting
        self.configure.update(namespace='something')
        self.assertEqual(self.configure.namespace, 'something')

    def test_backend_gets_backend_when_backend_is_not_set(self):
        # When backend is not set
        self.assertEqual(self.configure._backend, None)
        self.assertEqual(self.configure._backend, self.configure.backend)
        self.assertEqual(self.configure._backend, None)

    def test_backend_gets_backend_when_backend_is_set(self):
        # When backend is set
        self.configure.backend = sherlock.backends.ETCD
        self.assertEqual(self.configure._backend, self.configure.backend)
        self.assertEqual(self.configure._backend,
                         sherlock.backends.ETCD)

    def test_backend_raises_error_on_setting_invalid_backend(self):
        def _test():
            # Set some unexpected value
            self.configure.backend = 0
        self.assertRaises(ValueError, _test)

    def test_backend_sets_backend_value(self):
        self.configure.backend = sherlock.backends.ETCD
        self.assertEqual(self.configure._backend,
                         sherlock.backends.ETCD)

    def test_client_returns_the_set_client_object(self):
        client = Mock()
        self.configure._client = client
        self.assertEqual(self.configure.client, self.configure._client)
        self.assertEqual(self.configure._client, client)

    def test_client_raises_error_when_backend_is_not_set(self):
        # Make sure backend is set to None
        self.assertEqual(self.configure.backend, None)

        def _test():
            self.configure.client
        self.assertRaises(ValueError, _test)

    def test_client_returns_client_when_not_set_but_backend_is_set(self):
        self.configure.backend = sherlock.backends.ETCD
        self.assertTrue(isinstance(self.configure.client, etcd.Client))

    def test_client_sets_valid_client_obj_only_when_backend_set(self):
        # When backend is set and client object is invalid
        self.configure.backend = sherlock.backends.ETCD

        def _test():
            self.configure.client = None
        self.assertRaises(ValueError, _test)

        # When backend is set and client object is valid
        self.configure.client = etcd.Client()

    def test_client_sets_valid_client_obj_only_when_backend_not_set(self):
        # When backend is not set and client library is available and client is
        # valid
        self.configure._backend = None
        self.assertEqual(self.configure.backend, None)
        client_obj = etcd.Client()
        self.configure.client = client_obj
        self.assertEqual(self.configure.client, client_obj)
        self.assertTrue(isinstance(self.configure.client, etcd.Client))

        # When backend is not set and client library is available and client is
        # invalid
        self.configure._backend = None
        self.configure._client = None
        self.assertEqual(self.configure.backend, None)
        client_obj = 'Random'

        def _test():
            self.configure.client = client_obj
        self.assertRaises(ValueError, _test)

        # When backend is not set and client library is available and client is
        # valid
        self.configure._backend = None
        self.configure._client = None
        self.assertEqual(self.configure.backend, None)
        client_obj = etcd.Client()
        self.configure.client = client_obj


def testConfigure():
    '''
    Test the library configure function.
    '''

    sherlock.configure(namespace='namespace')
    assert sherlock._configuration.namespace == 'namespace'


class TestBackends(unittest.TestCase):

    def setUp(self):
        reload(sherlock)

    def test_valid_backends(self):
        self.assertEqual(sherlock.backends.valid_backends,
                         sherlock.backends._valid_backends)

    def test_register_raises_exception_when_lock_class_invalid(self):
        self.assertRaises(ValueError,
                          sherlock.backends.register,
                          'MyLock',
                          object,
                          'some_lib',
                          object)

    def test_register_registers_custom_backend(self):
        class MyLock(sherlock.lock.BaseLock):
            pass
        name = 'MyLock'
        lock_class = MyLock
        library = 'some_lib'
        client_class = object
        args = (1, 2, 3)
        kwargs = dict(somekey='someval')
        sherlock.backends.register(name=name,
                                   lock_class=lock_class,
                                   library=library,
                                   client_class=client_class,
                                   default_args=args,
                                   default_kwargs=kwargs)

        self.assertTrue(isinstance(sherlock.backends.MyLock, dict))
        self.assertEqual(sherlock.backends.MyLock['name'], name)
        self.assertEqual(sherlock.backends.MyLock['lock_class'], lock_class)
        self.assertEqual(sherlock.backends.MyLock['library'], library)
        self.assertEqual(sherlock.backends.MyLock['client_class'],
                         client_class)
        self.assertEqual(sherlock.backends.MyLock['default_args'], args)
        self.assertEqual(sherlock.backends.MyLock['default_kwargs'], kwargs)

        self.assertTrue(
            sherlock.backends.MyLock in sherlock.backends.valid_backends)
