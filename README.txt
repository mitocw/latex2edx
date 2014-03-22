=========
latex2edx
=========

Converts latex to edX XML format.

Uses plasTeX

Installation
============

    pip install -e git+https://github.com/mitocw/latex2edx.git#egg=latex2edx

Note that xmllint and lxml are required; for ubuntu, this may work:

    apt-get install libxml2-utils python-lxml

Usage
=====

Usage: latex2edx [options] filename.tex

Options:

  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -v, --verbose         verbose error messages
  -o OUTPUT_FN, --output-xbundle=OUTPUT_FN
                        Filename for output xbundle file
  -d OUTPUT_DIR, --output-directory=OUTPUT_DIR
                        Directory name for output course XML files
  -c CONFIG_FILE, --config-file=CONFIG_FILE
                        configuration file to load
  -m, --merge-chapters  merge chapters into existing course directory

History
=======

* v1.0: python package; unit tests; xbundle and modular code
* v1.1: Support for jsinput, custom mathjax filtering, formularesponse
* v1.1.1: Fix optargs bug with plastex

