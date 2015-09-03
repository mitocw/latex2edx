'''
Test latex2edx export to directory tree with optionally specified nested
file structure in the url_name field of problem elements.
'''
import os
import unittest
from lxml import etree
from path import path  # needs path.py

import latex2edx as l2e
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestAllow_Dirs(unittest.TestCase):
    '''
    This class contains two test methods:
    `test_allow_dirs1` checks the behavior of the output when the
    allow-directories flag is not set
    `test_allow_dirs2` checks to make sure nested directories are created
    when desired
    '''

    def test_allow_dirs1(self):
        '''
        Test that the output problem is properly renamed when allow-directories
        is set to false
        '''
        testdir = path(l2e.__file__).parent / 'testtex'
        tfn = testdir / 'example15_directories.tex'
        print "file %s" % tfn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, tfn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2eout = latex2edx(nfn, output_dir=tmdir, allow_dirs=False)
            l2eout.convert()

            opfn = path(tmdir) / 'problem/test_subdirprob.xml'
            self.assertTrue(os.path.exists(opfn))

            cfn = path(tmdir) / 'chapter/One.xml'
            xml = etree.fromstring(open(cfn).read())
            prob = xml.find('.//problem')
            self.assertEqual(prob.get('url_name'), 'test_subdirprob')

    def test_allow_dirs2(self):
        '''
        Test that the output problem is properly nested when allow-directories
        is specified
        '''
        testdir = path(l2e.__file__).parent / 'testtex'
        tfn = testdir / 'example15_directories.tex'
        print "file %s" % tfn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, tfn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2eout = latex2edx(nfn, output_dir=tmdir, allow_dirs=True)
            l2eout.convert()

            opfn = path(tmdir) / 'problem/test/subdirprob.xml'
            self.assertTrue(os.path.exists(opfn))

            cfn = path(tmdir) / 'chapter/One.xml'
            xml = etree.fromstring(open(cfn).read())
            prob = xml.find('.//problem')
            self.assertEqual(prob.get('url_name'), 'test:subdirprob')

if __name__ == '__main__':
    unittest.main()
