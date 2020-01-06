import os
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


class TestDND(unittest.TestCase):

    def test_DND1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example5.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.mkdir('%s/dnd' % tmdir)
            os.system('cp %s/quadratic.tex %s/dnd/' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            # xb = open(xbfn).read()

            cfn = path(tmdir) / 'problem/p1.xml'
            assert(os.path.exists(cfn))
            os.system('ls -sFC %s' % tmdir)
            os.system('ls -sFC %s/problem' % tmdir)
            self.assertTrue(os.path.exists(cfn))
            data = open(cfn).read()
            assert('<drag_and_drop_input img="/static/images/quadratic/quadratic_dnd.png" target_outline="false" one_per_target="true"' in data)
            assert('<draggable id="term1" icon="/static/images/quadratic/quadratic_dnd_label1.png"/>' in data)

    def test_DND2(self):
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'example5a.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.mkdir('%s/dnd' % tmdir)
            os.system('cp %s/quadratic.tex %s/dnd/' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            # xb = open(xbfn).read()

            cfn = path(tmdir) / 'problem/p1.xml'
            assert(os.path.exists(cfn))
            os.system('ls -sFC %s' % tmdir)
            os.system('ls -sFC %s/problem' % tmdir)
            self.assertTrue(os.path.exists(cfn))
            data = open(cfn).read()
            assert('<drag_and_drop_input img="/static/images/quadratic/quadratic_dnd.png" target_outline="false" one_per_target="true"' in data)
            assert('<draggable id="term1" icon="/static/images/quadratic/quadratic_dnd_label1.png" can_reuse="true"/>' in data)

if __name__ == '__main__':
    unittest.main()
