=========
latex2edx
=========

Converts latex to edX XML format.

Uses plasTeX

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
