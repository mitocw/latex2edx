import os
import re
import unittest
try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path
from lxml import etree
from io import StringIO

import latex2edx as l2emod
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestedXinclude(unittest.TestCase):

    def test_edXinclude1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example7.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            # xb = open(xbfn).read()

            cfn = path(tmdir) / 'chapter/Unit_2.xml'
            assert(os.path.exists(cfn))
            self.assertTrue(os.path.exists(cfn))
            data = open(cfn).read()
            expect = r"""<vertical url_name="A_second_section_vertical1">
      <staffgrading url_name="project_paper"/>
    </vertical>"""
            assert(expect in data)

            cfn = path(tmdir) / 'staffgrading/project_paper.xml'
            assert(os.path.exists(cfn))

    def test_edXinclude2(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example7_bad.tex'
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
                self.assertTrue(re.search('Error processing element edxincludepy in file .*example.*\.tex line 25', str(err)))

if __name__ == '__main__':
    unittest.main()
