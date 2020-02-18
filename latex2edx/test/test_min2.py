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


class TestMin2(unittest.TestCase):

    def test_min2(self):
        '''
        Jeremy Orloff's test to ensure math "Find $P(Z < 1.5)$." is converted correctly, with "<" becoming "&lt;"
        '''
        testdir = path(l2emod.__file__).parent / 'testtex'
        fn = testdir / 'min2.tex'
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir, section_only=True, verbose=True)
            l2e.convert()
            xbfn = nfn[:-4] + '.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            with open(xbfn) as fp:
                xb = fp.read()
            print(xb)
            self.assertIn('[mathjaxinline]P(Z &lt; 1.5)[/mathjaxinline]', xb)

if __name__ == '__main__':
    unittest.main()
