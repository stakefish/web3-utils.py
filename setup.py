#!/usr/bin/env python
from setuptools import (
    find_packages,
    setup,
)

extras_require = {
    "linter": [
        "black==22.10.0",
        "isort==5.10.1",
    ],
    "dev": [
        "bumpversion==0.6.0",
        "eth-brownie==1.19.2",
        "pytest-asyncio==0.20.2",
        "pytest-mock==3.10.0",
        "setuptools==65.6.3",
    ],
}

extras_require["dev"] = (
    extras_require["linter"]
    + extras_require["dev"]
)

with open("./README.md") as readme:
    long_description = readme.read()

setup(
    name="web3-utils",
    # *IMPORTANT*: Don't manually change the version here. Use the 'bumpversion' utility.
    version="0.0.1",
    description="""Stakefish web3 utils for Python""",
    long_description_content_type="text/markdown",
    long_description=long_description,
    author="Michal Baranowski, Mateusz Sokola",
    author_email="mbaranovski@stake.fish, mateusz@stake.fish",
    url="https://github.com/stakefish/web3-utils",
    include_package_data=True,
    install_requires=[
        "web3==5.31.1",
    ],
    python_requires="==3.10.5",
    extras_require=extras_require,
    # py_modules=["web3_utils"],
    # entry_points={"pytest11": ["pytest_ethereum = web3.tools.pytest_ethereum.plugins"]},
    license="INTERNAL",
    # zip_safe=False,
    keywords="ethereum, stakefish",
    packages=find_packages(exclude=["tests", "tests.*"]),
    # package_data={"web3": ["py.typed"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: Proprietary :: Internal",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.10",
    ],
)
