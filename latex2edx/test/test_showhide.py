'''
Test calls to the edXshowhide environment a proper creation of the
supporting latex2edx.js and latex2edx.css in the static directory.
'''
import os
import unittest
from lxml import etree
from path import path  # needs path.py

import latex2edx as l2e
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestShowHide(unittest.TestCase):
    '''
    This class inherits the `unittest.TestCase` class and contains the method
    `test_sh1` that tests the generation of proper html and supporting files
    '''

    def test_sh1(self):
        '''
        Test the output of `latex2edx example14_showhide.tex` for proper
        formation of the showhide element.
        '''
        testdir = path(l2e.__file__).parent / 'testtex'
        tfn = testdir / 'example14_showhide.tex'
        print "file %s" % tfn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, tfn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2eout = latex2edx(nfn, output_dir=tmdir)
            l2eout.convert()

            jsfn = '%s/static/latex2edx.js' % tmdir
            cssfn = '%s/static/latex2edx.css' % tmdir
            self.assertTrue(os.path.exists(jsfn))
            self.assertTrue(os.path.exists(cssfn))

            tfn = '%s/html/Text.xml' % tmdir
            xml = etree.parse(tfn).getroot()
            sh = xml.find('.//div[@class="hideshowbox"]')
            self.assertEqual(sh[0].tag, 'h4')
            self.assertEqual(sh[0].get('onclick'), 'hideshow(this);')
            self.assertEqual(sh[0].text, 'Secret text')
            self.assertEqual(sh[1].get('class'), 'hideshowcontent')
            self.assertEqual(sh[1].text.strip(), 'Hidden text')
            self.assertEqual(sh[2].get('class'), 'hideshowbottom')
            lk = xml.find('.//LINK')
            self.assertTrue('latex2edx.css' in lk.get('href'))
            sc = xml.find('.//SCRIPT')
            self.assertTrue('latex2edx.js' in sc.get('src'))

if __name__ == '__main__':
    unittest.main()
