FROM python:3.7

WORKDIR /sherlock

# Memcached
RUN apt-get update -y && apt-get install -y libmemcached-dev gcc
RUN pip install pytz ipython ipdb

COPY requirements-ci.txt /sherlock/requirements-ci.txt
RUN pip install -r /sherlock/requirements-ci.txt && \
    rm /sherlock/requirements-ci.txt
