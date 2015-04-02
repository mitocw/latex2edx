'''
Test XML insertion using the `edXxml` command with example13_edxxml.tex
'''
import os
import unittest
from path import path  # needs path.py

import latex2edx as l2e
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestEdxxml(unittest.TestCase):
    '''
    This class inherits the `unittest.TestCase` class and contains the methods
    `test_edxxml1` that test the proper functionality of the latex2edx
    `edXxml` command, properly parsing all text, children, and tail text
    contained therein.
    '''

    def test_edxxml1(self):
        '''
        Test the output of `latex2edx example13_edxxml.tex` for proper
        rendering of the complete XML with multiple calls in `edXxml` in a
        given line.
        '''
        testdir = path(l2e.__file__).parent / 'testtex'
        tfn = testdir / 'example13_edxxml.tex'
        print "file %s" % tfn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, tfn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2eout = latex2edx(nfn, output_dir=tmdir)
            l2eout.convert()

            cfn = path(tmdir) / 'html/Code_Text.xml'
            data = open(cfn).read().split('\n')
            expected = ('A matrix <code>A</code> and column vector named '
                        '<code>b</code> can be multiplied in the form '
                        '<code>A b</code> only if the number of columns '
                        'of <code>b</code> match the number of rows in '
                        '<code>A</code>. </p>')
            self.assertEqual(data[2], expected)

if __name__ == '__main__':
    unittest.main()
