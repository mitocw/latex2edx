import os
import contextlib
import unittest
import tempfile
import shutil
import json
from path import path	# needs path.py
import latex2edx as l2emod
from latex2edx.main import latex2edx
from StringIO import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2etmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestPolicy(unittest.TestCase):

    def test_policy1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'  
        fn = testdir / 'example3.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            l2e = latex2edx(nfn, output_dir=tmdir, update_policy=True, suppress_policy=True)
            l2e.convert()

            xbfn = nfn[:-4]+'.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            pfn = path(tmdir) / 'policies/2013_Fall/policy.json'
            self.assertTrue(os.path.exists(pfn))
            dat = open(pfn).read()
            policy = json.loads(dat)
            self.assertTrue('course/2013_Fall' in policy)

            self.assertTrue(policy['course/2013_Fall']['start']=="2014-05-11T12:00")
            self.assertTrue(policy['course/2013_Fall']['end']=="2012-08-12T00:00")
            self.assertTrue(policy['course/2013_Fall']['showanswer']=="always")

            self.assertTrue('chapter/Unit_2' in policy)

            self.assertTrue(policy['sequential/A_second_section']['graded']=="true")
            self.assertTrue(policy['sequential/A_second_section']['due']=="2016-11-22T00:00")

if __name__ == '__main__':
    unittest.main()
