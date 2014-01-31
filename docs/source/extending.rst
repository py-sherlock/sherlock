.. :mod:`sherlock` documentation master file, created by
   sphinx-quickstart on Wed Jan 22 11:28:21 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _extending:

Extending
=========

:mod:`sherlock` can be easily extended to work with any backend. You just have
to register your lock's implementation with :mod:`sherlock` and you will be
able to use your lock with the backend of your choice in your project.

Registration
++++++++++++

Custom locks can be registered using the following API:

.. automethod:: sherlock.backends.register

Example
+++++++

Here is an example of implementing a custom lock that uses `Elasticsearch`_ as
backend.

.. _Elasticsearch: http://elasticsearch.org

.. note:: You may distributed your custom lock implementation as package if you
          please. Just make sure that you add :mod:`sherlock` as a dependency.

The following code goes in a module called ``sherlock_es.py``.

.. code:: python

    import elasticsearch
    import sherlock
    import uuid

    from elasticsearch import Elasticsearch
    from sherlock import LockException


    class ESLock(sherlock.lock.BaseLock):
        def __init__(self, lock_name, **kwargs):
            super(ESLock, self).__init__(lock_name, **kwargs)

            if self.client is None:
                self.client = Elasticsearch(hosts=['localhost:9200'])

            self._owner = None

        def _acquire(self):
            owner = uuid.uuid4().hex

            try:
                self.client.get(index='sherlock', doc_type='locks',
                                id=self.lock_name)
            except elasticsearch.NotFoundError, err:
                self.client.index(index='sherlock', doc_type='locks',
                                  id=self.lock_name, body=dict(owner=owner))
                self._owner = owner
                return True
            else:
                return False

        def _release(self):
            if self._owner is None:
                raise LockException('Lock was not set by this process.')

            try:
                resp = self.client.get(index='sherlock', doc_type='locks',
                                       id=self.lock_name)
                if resp['_source']['owner'] == self._owner:
                    self.client.delete(index='sherlock', doc_type='locks',
                                       id=self.lock_name)

                else:
                    raise LockException('Lock could not be released because it '
                                        'was not acquired by this process.')
            except elasticsearch.NotFoundError, err:
                raise LockException('Lock could not be released as it has not '
                                    'been acquired.')

        @property
        def _locked(self):
            try:
                self.client.get(index='sherlock', doc_type='locks',
                                id=self.lock_name)
                return True
            except elasticsearch.NotFoundError, err:
                return False


    # Register the custom lock with sherlock
    sherlock.backends.register(name='ES',
                               lock_class=ESLock,
                               library='elasticsearch',
                               client_class=Elasticsearch,
                               default_args=(),
                               default_kwargs={
                                   'hosts': ['localhost:9200'],
                               })

Our module can be used like so:

.. code:: python

    import sherlock
    import sherlock_es

    # Notice that ES is available as backend now
    sherlock.configure(backend=sherlock.backends.ES)

    lock1 = sherlock.Lock('test1')
    lock1.acquire() # True

    lock2 = sherlock_es.ESLock('test2')
    lock2.acquire() # True

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

