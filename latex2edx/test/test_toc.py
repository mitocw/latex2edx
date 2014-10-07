import os
import re
import unittest
from lxml import etree
from path import path  # needs path.py

import latex2edx as l2e
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestToC(unittest.TestCase):

    def test_toc1(self):
        testdir = path(l2e.__file__).parent / 'testtex'
        fn = testdir / 'example11_toc_test.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            try:
                l2eout = latex2edx(nfn, output_dir=tmdir)
                l2eout.convert()
            except Exception as err:
                print "Error = %s" % str(err)

            xhfn = nfn[:-4] + '.xhtml'
            xml = etree.fromstring(open(xhfn).read())
            toclabels = xml.findall('.//toclabel')
            self.assertTrue(toclabels[0].text == 'chap:intro')
            self.assertTrue(toclabels[1].text == 'mo:explore')
            tocref = xml.find('.//tocref')
            self.assertTrue(tocref.text == 'mo:explore')
            labels = xml.findall('.//label')
            for label in labels:
                self.assertTrue(label.text in ['fig:single', 'fig:multi'])
            captions = xml.findall('.//div[@class="caption"]')
            for caption in captions:
                self.assertTrue(caption[0].text in ['Figure 1', 'Figure 2'])
            chaps = xml.findall('.//chapter')
            self.assertTrue(chaps[0].get('refnum') is None)
            self.assertTrue(chaps[1].get('refnum') == '1')
            equation = xml.find('.//td[@class="equation"]')
            self.assertTrue(re.findall(r'\\label\{(.*?)\}', equation.text,
                            re.S)[0] == 'eq:pythagorean')

    def test_toc2(self):
        testdir = path(l2e.__file__).parent / 'testtex'
        fn = testdir / 'example11_toc_test.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            try:
                l2eout = latex2edx(nfn, output_dir=tmdir, popup_flag=True)
                l2eout.convert()
            except Exception as err:
                print "Error = %s" % str(err)

            cfn = path(tmdir) / 'html/text-L1.xml'
            data = open(cfn).read()
            xml = etree.fromstring(data)
            href = xml.findall('.//a[@href]')
            # Check the reference link text
            self.assertTrue(href[0].text == '0')  # Non-numbered chapter
            self.assertTrue(href[1].text == '(1.2)')  # Numbered equation 2
            self.assertTrue(href[2].text == '(1.3)')  # Numbered equation 3
            # Check for popup format
            self.assertTrue(href[1].get('href') == 'javascript: void(0)')
            self.assertTrue(href[2].get('href') == 'javascript: void(0)')
            # Check for taglist in problem
            cfn = path(tmdir) / 'problem/p0.xml'
            data = open(cfn).read()
            xml = etree.fromstring(data)
            taglist = xml.find('.//p[@id="taglist"]')
            self.assertTrue(taglist.get('tags') == 'mo:explore,mo:problem')

if __name__ == '__main__':
    unittest.main()
