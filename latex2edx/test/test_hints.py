import os
import contextlib
import unittest
import tempfile
import shutil
from path import path	# needs path.py
import latex2edx as l2emod
from latex2edx.main import latex2edx
from StringIO import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2etmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestHints(unittest.TestCase):

    def test_hints1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'  
        fn = testdir / 'example3.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4]+'.xbundle'
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
