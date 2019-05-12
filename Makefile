# Sherlock Makefile
# ~~~~~~~~~~~~~~~~~
#
# Shortcuts for various tasks.

documentation:
	@(cd docs; make html)

test:
	docker-compose -f docker-compose.dev.yml run sherlock

build:
	docker-compose -f docker-compose.dev.yml build sherlock

up:
	docker-compose -f docker-compose.dev.yml up -d etcd memcached redis
	@echo "Run the following command to start a Python shell with sherlock imported: 'make run_sherlock'"

run_bash: up
	docker-compose -f docker-compose.dev.yml run --entrypoint bash sherlock

run_sherlock: up
	docker-compose -f docker-compose.dev.yml run --entrypoint ipython sherlock

down:
	docker-compose -f docker-compose.dev.yml down

test:
	docker-compose -f docker-compose.dev.yml run sherlock

doctest:
	@(cd docs/source; sphinx-build -b doctest . _build/doctest)

readme:
	python -c 'import sherlock; print sherlock.__doc__' | sed "s/:mod:\`sherlock\`/Sherlock/g" | sed "s/:.*:\`\(.*\)\`/\`\`\1\`\`/g" > README.rst
