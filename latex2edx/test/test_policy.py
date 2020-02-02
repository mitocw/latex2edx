import os
import re
import unittest
import json
try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path
from io import StringIO

import latex2edx as l2emod
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestPolicy(unittest.TestCase):

    def test_policy1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example3.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            l2e = latex2edx(nfn, output_dir=tmdir, update_policy=True, suppress_policy=True)
            l2e.convert()

            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            pfn = path(tmdir) / 'policies/2013_Fall/policy.json'
            self.assertTrue(os.path.exists(pfn))
            dat = open(pfn).read()
            policy = json.loads(dat)
            self.assertTrue('course/2013_Fall' in policy)

            self.assertTrue(policy['course/2013_Fall']['start'] == "2014-05-11T12:00")
            self.assertTrue(policy['course/2013_Fall']['end'] == "2012-08-12T00:00")
            self.assertTrue(policy['course/2013_Fall']['showanswer'] == "always")

            self.assertTrue('chapter/Unit_2' in policy)

            self.assertTrue(policy['sequential/A_second_section']['graded'] == "true")
            self.assertTrue(policy['sequential/A_second_section']['due'] == "2016-11-22T00:00")

    def test_policy2(self):
        '''
        Check for good error message, with filename and lineno
        '''
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example10_badpolicy.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            try:
                l2e = latex2edx(nfn, output_dir=tmdir, update_policy=True, suppress_policy=True)
                l2e.convert()
            except Exception as err:
                print("Error = %s" % str(err))
                self.assertTrue(re.search('Error processing element sequential in file .*example10_badpolicy.tex line 18', str(err)))

if __name__ == '__main__':
    unittest.main()
