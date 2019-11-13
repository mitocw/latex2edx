'''
Test calls to \index{} and the creation of a key_map.json file for use as
a searchable index, currently only seems to work as a static page.
'''
import json
import os
import unittest
try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path

import latex2edx as l2e
from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class TestKey(unittest.TestCase):
    '''
    This class inherits the `unittest.TestCase` class and contains the method
    `test_key1` that test the proper functionality of the latex2edx `index`
    command.
    '''

    def test_key1(self):
        '''
        Test the output of `latex2edx example12_index.tex` for proper
        formation of the key_map.json file.
        '''
        testdir = path(l2e.__file__).parent / 'testtex'
        tfn = testdir / 'example12_index.tex'
        print("file %s" % tfn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, tfn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2eout = latex2edx(nfn, output_dir=tmdir)
            l2eout.convert()

            jsfn = '%s/static/key_map.json' % tmdir
            keymap = json.load(open(jsfn))
            self.assertEqual(set(keymap.keys()), set(['topic', 'numerical']))
            self.assertEqual(keymap['topic'][0],
                             ['Module_1/A_lecture_section/1',
                              'Module_1/Another_lecture_section/1'])
            self.assertEqual(keymap['numerical'],
                             [['Module_0/A_problem_section/2'],
                              ['Example problem']])

if __name__ == '__main__':
    unittest.main()
