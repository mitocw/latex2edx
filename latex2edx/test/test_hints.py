import os
import unittest
try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path
from io import StringIO

import latex2edx as l2emod
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestHints(unittest.TestCase):

    def test_hints1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example3.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            p1fn = path(tmdir) / 'problem/p1.xml'
            self.assertTrue(os.path.exists(p1fn))
            dat = open(p1fn).read()
            self.assertIn('# General hint system for edX', dat)

            p2fn = path(tmdir) / 'problem/p2.xml'
            self.assertTrue(os.path.exists(p2fn))
            dat = open(p2fn).read()
            self.assertIn('# General hint system for edX', dat)

            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(os.path.exists(cfn))

if __name__ == '__main__':
    unittest.main()
