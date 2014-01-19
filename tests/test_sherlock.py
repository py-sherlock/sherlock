'''
    Tests for some basic package's root level functionality.
'''

import sherlock
import unittest

from sherlock import _Configuration
from mock import Mock


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
        self.configure.backend = sherlock.backends.REDIS
        self.assertEqual(self.configure._backend, self.configure.backend)
        self.assertEqual(self.configure._backend,
                         sherlock.backends.REDIS)

    def test_backend_raises_error_on_setting_invalid_backend(self):
        def _test():
            # Set some unexpected value
            self.configure.backend = 0
        self.assertRaises(ValueError, _test)

    def test_backend_sets_backend_value(self):
        self.configure.backend = sherlock.backends.REDIS
        self.assertEqual(self.configure._backend,
                         sherlock.backends.REDIS)

    def test_client_returns_the_set_client_object(self):
        client = Mock()
        self.configure._client = client
        self.assertEqual(self.configure.client, self.configure._client)
        self.assertEqual(self.configure._client, client)

    def test_client_raises_error_when_backend_is_not_set(self):
        # Make sure backend is set to None
        self.assertEqual(self.configure.backend, None)
        def _test():
            client = self.configure.client
        self.assertRaises(ValueError, _test)

    def test_client_returns_client_when_not_set_but_backend_is_set(self):
        mock_obj = Mock()
        sherlock.redis.StrictRedis = Mock
        sherlock.redis.client.StrictRedis = Mock
        self.configure.backend = sherlock.backends.REDIS
        self.assertTrue(isinstance(self.configure.client, Mock))

    def test_client_sets_valid_client_obj_only_when_backend_set(self):
        # When backend is set and client object is invalid
        self.configure.backend = sherlock.backends.REDIS
        def _test():
            self.configure.client = None
        self.assertRaises(ValueError, _test)

        # When backend is set and client object is valid
        sherlock.redis.client.StrictRedis = Mock
        self.configure.client = Mock()

    def test_client_sets_valid_client_obj_only_when_backend_not_set(self):
        # When backend is not set and client library is available and client is
        # valid
        self.configure._backend = None
        self.assertEquals(self.configure.backend, None)
        client_obj = Mock()
        self.configure.client = client_obj
        self.assertEquals(self.configure.client, client_obj)
        self.assertTrue(isinstance(self.configure.client, Mock))

        # When backend is not set and client library is available and client is
        # invalid
        self.configure._backend = None
        self.configure._client = None
        self.assertEquals(self.configure.backend, None)
        client_obj = 'Random'
        def _test():
            self.configure.client = client_obj
        self.assertRaises(ValueError, _test)

        # When backend is not set and client library is available and client is
        # valid
        self.configure._backend = None
        self.configure._client = None
        self.assertEquals(self.configure.backend, None)
        client_obj = Mock()
        self.configure.client = client_obj


def testConfigure():
    '''
    Test the library configure function.
    '''

    sherlock.configure(namespace='namespace')
    assert sherlock._configuration.namespace == 'namespace'
