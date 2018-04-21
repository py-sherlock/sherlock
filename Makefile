# Sherlock Makefile
# ~~~~~~~~~~~~~~~~~
#
# Shortcuts for various tasks.

documentation:
	@(cd docs; make html)

test:
	sudo docker-compose -f docker-compose.dev.yml run sherlock

doctest:
	@(cd docs/source; sphinx-build -b doctest . _build/doctest)

readme:
	python -c 'import sherlock; print sherlock.__doc__' | sed "s/:mod:\`sherlock\`/Sherlock/g" | sed "s/:.*:\`\(.*\)\`/\`\`\1\`\`/g" > README.rst
