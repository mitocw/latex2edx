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


class TestOutput_Fmts(unittest.TestCase):

    def test_output_fmts1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example6.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            try:
                l2e = latex2edx(nfn, output_dir=tmdir, xml_only=True)
                l2e.convert()
                err = ""
            except Exception as err:
                print(err)

            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(not os.path.exists(cfn))

    def test_output_fmts2(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example9_section_only.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            try:
                l2e = latex2edx(nfn, output_dir=tmdir, section_only=True)
                l2e.convert()
                err = ""
            except Exception as err:
                print(err)

            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(not os.path.exists(cfn))

            cfn = path(tmdir) / 'sequential/A_second_section.xml'
            os.system('/bin/ls -R %s' % (path(tmdir)))
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'problem/p1.xml'
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'vertical/A_second_section_vertical.xml'
            self.assertTrue(os.path.exists(cfn))

    def test_output_fmts3(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example9_section_only.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            try:
                l2e = latex2edx(nfn, output_dir=tmdir, section_only=True, suppress_verticals=True)
                l2e.convert()
                err = ""
            except Exception as err:
                print(err)

            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(not os.path.exists(cfn))

            cfn = path(tmdir) / 'sequential/A_second_section.xml'
            os.system('/bin/ls -R %s' % (path(tmdir)))
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'problem/p1.xml'
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'vertical/A_second_section_vertical.xml'
            self.assertTrue(not os.path.exists(cfn))

    def test_output_fmts4(self):
        '''
        units only (problems)
        '''
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example1.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            try:
                l2e = latex2edx(nfn, output_dir=tmdir, units_only=True)
                l2e.convert()
                err = ""
            except Exception as err:
                print(err)

            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))

            cfn = path(tmdir) / 'course/2013_Fall.xml'
            self.assertTrue(not os.path.exists(cfn))

            cfn = path(tmdir) / 'sequential'
            self.assertTrue(not os.path.exists(cfn))

            cfn = path(tmdir) / 'problem/Problem_2.xml'
            self.assertTrue(os.path.exists(cfn))

            cfn = path(tmdir) / 'vertical'
            self.assertTrue(not os.path.exists(cfn))

if __name__ == '__main__':
    unittest.main()
