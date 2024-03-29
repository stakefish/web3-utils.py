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

lint:
	black --check .

format:
	black .

install: clean
	pip install --editable .
	pip install -r requirements-dev.txt
	npm ci

test:
	brownie test --network hardhat -s

release: clean
	# require that you be on a branch that's linked to origin/main
	git status -s -b | head -1 | grep "\.\.origin/main"
	git config commit.gpgSign true
	bumpversion $(bump)
	git push origin && git push origin --tags
	python -m build
	twine upload dist/*

dist: clean
	python -m build
	ls -l dist

package: clean
	python -m build
	python scripts/test_package.py
