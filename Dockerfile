FROM python:3.7

WORKDIR /sherlock

# Memcached
RUN apt-get update -y && apt-get install -y libmemcached-dev
RUN pip install pytz coverage ipython ipdb
