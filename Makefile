.PHONY: clean-pyc clean-build docs

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "format - formats files to match code style using black"
	@echo "release - package and upload a release"
	@echo "dist - package"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

format:
	black .

release: clean
	# require that you be on a branch that's linked to origin/main
	# git status -s -b | head -1 | grep "\.\.origin/main"
	# verify that docs build correctly
	git config commit.gpgSign true
	bumpversion $(bump)
	# bumpversion minor
	# bumpversion --new-version 0.0.1-alpha0 part dist
	git push upstream && git push upstream --tags
	python setup.py sdist bdist_wheel
	twine upload dist/*

dist: clean
	python setup.py sdist bdist_wheel
	ls -l dist

package: clean
	python setup.py sdist bdist_wheel
	python web3/scripts/release/test_package.py
