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

class TestExamples(unittest.TestCase):

    def test_example1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'  
        fn = testdir / 'example1.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4]+'.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            xb = open(xbfn).read()
            self.assertIn('<chapter display_name="Unit 1" start="2013-11-22" url_name="Unit_1">', xb)
            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'chapter/Unit_1.xml'
            self.assertTrue(os.path.exists(cfn))

            self.assertIn('<sequential display_name="Introduction" due="2013-11-22" url_name="Introduction">', open(cfn).read())

            self.assertIn('<problem url_name="p1"/>', open(cfn).read())

    def test_merge(self):
        testdir = path(l2emod.__file__).parent / 'testtex'  
        with make_temp_directory() as tmdir:
            fn = testdir / 'example1.tex'
            print "file %s" % fn
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()

            fn = testdir / 'example2.tex'
            print "file %s" % fn
            nfn = '%s/%s' % (tmdir, fn.basename())
            l2e = latex2edx(nfn, output_dir=tmdir, do_merge=True)
            l2e.convert()

            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(os.path.exists(cfn))

            self.assertIn('<chapter url_name="Unit_1"/>', open(cfn).read())
            self.assertIn('<chapter url_name="Unit_2"/>', open(cfn).read())

            cfn = path(tmdir) / 'chapter/Unit_1.xml'
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'chapter/Unit_2.xml'
            self.assertTrue(os.path.exists(cfn))

if __name__ == '__main__':
    unittest.main()
