#! /usr/bin/env python

from setuptools import setup

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name="promise_keeper",
    py_modules=["promise_keeper"],
    version="0.4",
    description="A simple async processing helper",
    long_description=long_description,
    author="Steve Brettschneider",
    author_email="steve@bluehousefamily.com",
    url="https://github.com/brettschneider/python_promise_keeper",
    download_url="https://github.com/brettschneider/python_promise_keeper/archive/0.4.tar.gz",
    keywords=["promise", "async", "threading", "aynchronous", "simple"],
    classifiers=[]
)
