import os
import unittest
from io import StringIO

from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory


class MakeTeX(object):
    def __init__(self, tex):
        buf = """\\documentclass[12pt]{article}\n\\usepackage{edXpsl}\n\n\\begin{document}"""
        buf += tex
        buf += "\\end{document}"
        self.buf = buf

    @property
    def fp(self):
        return StringIO(self.buf)


class TestAskTA(unittest.TestCase):

    def test_askta1(self):

        tex = ('\\begin{edXcourse}{1.00x}{1.00x Fall 2013}[url_name=2013_Fall]\n'
               '\n'
               '\\begin{edXchapter}{Unit 1}[start="2013-11-22"]\n'
               '\n'
               '\\begin{edXsection}{Introduction}\n'
               '\n'
               '\\begin{edXproblem}{test problem}\n'
               '\n'
               '\\edXaskta{settings=1 to="test@gmail.com"}\n\n'
               '\\edXaskta{cc="tocc@gmail.com"}\n\n'
               '\\end{edXproblem}\n'
               '\\end{edXsection}\n'
               '\\end{edXchapter}\n'
               '\\end{edXcourse}\n'
               )

        # make sure edXaskta buttons work properly
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            fp = MakeTeX(tex).fp
            l2e = latex2edx(tmdir + '/test.tex', fp=fp, do_images=False, output_dir=tmdir)
            l2e.xhtml2xbundle()
            # print "xbundle = "
            # print str(l2e.xb)
            # print
            self.assertIn(r'<a style="display:none" href="/course/jump_to_id" id="aturl_1"/>', str(l2e.xb))

if __name__ == '__main__':
    unittest.main()
