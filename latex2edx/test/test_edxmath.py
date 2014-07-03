import os
import contextlib
import unittest
import tempfile
import shutil
from path import path	# needs path.py
from lxml import etree
import latex2edx as l2emod
from latex2edx.main import latex2edx
from StringIO import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2etmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestedXmath(unittest.TestCase):

    def test_edXmath1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'  
        fn = testdir / 'example6.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.mkdir('%s/dnd' % tmdir)
            os.system('cp %s/quadratic.tex %s/dnd/'  % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4]+'.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            xb = open(xbfn).read()

            cfn = path(tmdir) / 'problem/p1.xml'
            assert(os.path.exists(cfn))
            os.system('ls -sFC %s' % tmdir)
            os.system('ls -sFC %s/problem' % tmdir)
            self.assertTrue(os.path.exists(cfn))
            data = open(cfn).read()
            expect = r"""[mathjax]\begin{eqnarray}
S(\rho) &amp;=&amp;  -\lambda_{1} \log \lambda_{1} -\lambda_{2} \log \lambda_{2} \\
        &amp;=&amp;  H((1+r)/2)
\end{eqnarray}[/mathjax]"""
            assert(expect in data)

if __name__ == '__main__':
    unittest.main()
