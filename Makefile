# Sherlock Makefile
# ~~~~~~~~~~~~~~~~~
#
# Shortcuts for various tasks.

CODE_MOUNTED := $(shell ps aux| grep "minikube mount" | grep -v grep > /dev/null ; echo $$?)
DELETE_JOB = kubectl delete job sherlock-tests

documentation:
	@(cd docs; make html)

setup:
	kubectl apply -f kubernetes/etcd
	./kubernetes/wait-for pod pod=etcd
	kubectl apply -f kubernetes/redis
	./kubernetes/wait-for pod pod=redis
	kubectl apply -f kubernetes/memcached
	./kubernetes/wait-for pod pod=memcached

mount-code:
ifeq ($(CODE_MOUNTED), 1)
	minikube mount $(shell pwd):/code/sherlock &
endif

unmount-code:
ifeq ($(CODE_MOUNTED), 0)
	@ps aux | grep "minikube mount" | grep -v grep | awk '{ print $$2 }' | xargs kill
endif

setup-dev: mount-code
	kubectl apply -f kubernetes/sherlock/deployment.yaml
	./kubernetes/wait-for pod pod=sherlock

clean-dev: unmount-code
	kubectl delete deployment sherlock

attach:
	@echo "\n\nAttaching to container"
	kubectl exec -it $(shell kubernetes/get-pod-name pod=sherlock) /bin/bash

dev: setup-dev attach

test: setup mount-code
	kubectl apply -f kubernetes/sherlock/job.yaml
	./kubernetes/wait-for pod pod=sherlock-tests
	sleep 1
	kubectl logs -f `./kubernetes/get-pod-name pod=sherlock-tests`
	# TODO: fix this next ugly statement
	./kubernetes/is-job-complete sherlock-tests && ($(DELETE_JOB) && exit 0) || ($(DELETE_JOB) && exit 1);


doctest:
	@(cd docs/source; sphinx-build -b doctest . _build/doctest)

readme:
	python -c 'import sherlock; print sherlock.__doc__' | sed "s/:mod:\`sherlock\`/Sherlock/g" | sed "s/:.*:\`\(.*\)\`/\`\`\1\`\`/g" > README.rst
