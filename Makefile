# Sherlock Makefile
# ~~~~~~~~~~~~~~~~~
#
# Shortcuts for various tasks.

documentation:
	@(cd docs; make html)

test:
	tox

doctest:
	@(cd docs/source; sphinx-build -b doctest . _build/doctest)

readme:
	python -c 'import sherlock; print sherlock.__doc__' | sed "s/:mod:\`sherlock\`/Sherlock/g" | sed "s/:.*:\`\(.*\)\`/\`\`\1\`\`/g" > README.rst
