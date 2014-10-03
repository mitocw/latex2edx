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

class TestMath(unittest.TestCase):

    def test_math1(self):
        # make sure latex math expressions are turned into mathjax
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            fp = MakeTeX(r'$\frac{\alpha}{\sqrt{1+\beta}}$').fp
            l2e = latex2edx(tmdir + '/test.tex', fp=fp, do_images=False, output_dir=tmdir)
            self.assertIn(r'<div>[mathjaxinline]\frac{\alpha }{\sqrt {1+\beta }}[/mathjaxinline]</div>', l2e.xhtml)

    def test_math2(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            tex = r'\begin{eqnarray}\dot{Q} = \frac{A}{R_{\rm thermal}} \Delta T\end{eqnarray}'
            expect = '[mathjaxinline]\\displaystyle \\dot{Q} = \\frac{A}{R_{\\rm thermal}} \\Delta T[/mathjaxinline]'
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir)
            # print l2e.p2x.renderer.__dict__
            self.assertIn(expect, l2e.xhtml)

if __name__ == '__main__':
    unittest.main()
