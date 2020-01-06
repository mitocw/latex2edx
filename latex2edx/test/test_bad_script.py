import os
import re
import contextlib
import unittest
import tempfile
import shutil
import json
try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path
from io import StringIO

import latex2edx as l2emod
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestBad_Script(unittest.TestCase):

    def test_bad_script1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example1_bad_script.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            try:
                l2e = latex2edx(nfn, output_dir=tmdir)
                l2e.convert()
            except Exception as err:
                print("Error = %s" % str(err))
                self.assertTrue(re.search('Error processing element script in file .*\.tex line 82', str(err)))

    def test_bad_script2(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example7_bad_script.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            try:
                l2e = latex2edx(nfn, output_dir=tmdir)
                l2e.convert()
            except Exception as err:
                print("Error = %s" % str(err))
                self.assertTrue(re.search('Error processing element edxincludepy in file .*\.tex line 25', str(err)))

if __name__ == '__main__':
    unittest.main()
