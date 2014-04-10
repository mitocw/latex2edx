import os
import contextlib
import unittest
import tempfile
import shutil
from latex2edx.main import latex2edx
from StringIO import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2etmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

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
               '\\begin{edXchapter}{Unit 1}[start="2013-11-22"]\n'
               '\\begin{edXsection}{Introduction}\n'
               '\\begin{edXproblem}{test problem}\n'
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
            #print "xbundle = "
            #print str(l2e.xb)
            #print
            self.assertIn(r'<a style="display:none" href="/course/jump_to_id" id="aturl_1"/>', str(l2e.xb))

if __name__ == '__main__':
    unittest.main()
