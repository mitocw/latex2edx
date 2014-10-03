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

class TestVideo(unittest.TestCase):

    def test_video1(self):
        testdir = path(l2emod.__file__).parent / 'testtex'  
        fn = testdir / 'example4.tex'
        print "file %s" % fn
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2e = latex2edx(nfn, output_dir=tmdir)
            l2e.convert()
            xbfn = nfn[:-4]+'.xbundle'
            self.assertTrue(os.path.exists(xbfn))
            xb = open(xbfn).read()

            cfn = path(tmdir) / 'chapter/Unit_2.xml'
            self.assertTrue(os.path.exists(cfn))

            xml = etree.parse(cfn).getroot()
            assert(xml.tag=='chapter')
            assert(xml.get('display_name')=="Unit 2")
            assert(xml.get('start')=="2013-11-22")
            assert(xml[0].tag=='sequential')
            assert(xml[0][0].tag=='vertical')
            assert(xml[0][0][0].tag=='video')
            assert(xml[0][0][0].get('url_name')=='A_sample_video')
            assert(not xml.findall('.//p'))
            assert(xml[0][1][0].tag=='problem')
            assert(xml[0][2][0].tag=='discussion')
            assert(xml[0][2][0].get('url_name')=='Discuss_this_question')
            assert(len(xml[0])==3)

            cfn = path(tmdir) / 'video/A_sample_video.xml'
            self.assertTrue(os.path.exists(cfn))
            self.assertTrue('<video display_name="A sample video" youtube_id_1_0="u23ZUSu7-HY" source="test"/>' in open(cfn).read())

            cfn = path(tmdir) / 'discussion/Discuss_this_question.xml'
            self.assertTrue(os.path.exists(cfn))
            self.assertTrue('<discussion display_name="Discuss this question" forumid="discuss2"/>' in open(cfn).read())

if __name__ == '__main__':
    unittest.main()
