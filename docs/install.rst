Installation
============

Requirements
------------

* python 2.7
* python-lxml
* beautifulsoup

Installation Procedure
----------------------

Install using this command:

    pip install -e git+https://github.com/mitocw/latex2edx.git#egg=latex2edx

Note that xmllint and lxml are required; for ubuntu, this may work:

    apt-get install libxml2-utils python-lxml

PlasTeX (http://plastex.sourceforge.net/) is also required, but should
be installed automatically by the pip install.

Poppler (https://poppler.freedesktop.org/) is required.  On a mac with homebrew this can be installed with

    brew install poppler
