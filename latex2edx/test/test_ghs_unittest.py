import os
import unittest
import sys
try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path

# sys.path.append('../python_lib')
# from general_hint_system import *

# -----------------------------------------------------------------------------
# unittest entry


class TestGHS(unittest.TestCase):

    def test_policy1(self):
        assert(True)

    def test_ghs1(self):
        # import here, cause outside the eggs aren't loaded
        mydir = path(os.path.dirname(__file__)).dirname()
        libpath = path(os.path.abspath(mydir + '/python_lib'))
        if str(mydir) == '':
            libpath = '..' + libpath
        print("libpath=%s" % libpath)
        os.chdir(libpath)
        import pytest
        errno = pytest.main(['test_ghs.py'])
        print("errno=%s" % errno)
        assert(errno == 0)

if __name__ == '__main__':
    unittest.main()
