'''
Run unittest on xbundle.py
'''
from latex2edx.xbundle import XBundle
import unittest
from lxml import etree
import os
# ----------------------------------------------------------------------------
# tests


class TestXBundle(unittest.TestCase):
    def testRoundTrip(self):

        print "Testing XBundle round trip import -> export"
        xb = XBundle()
        cxmls = '''
<course semester="2013_Spring" course="mitx.01">
  <chapter display_name="Intro">
    <sequential display_name="Overview">
      <html display_name="Overview text">
        hello world
      </html>
    </sequential>
    <!-- a comment -->
  </chapter>
</course>
'''

        pxmls = """
<policies semester='2013_Spring'>
  <gradingpolicy>y:2</gradingpolicy>
  <policy>x:1</policy>
</policies>
"""

        xb.set_course(etree.XML(cxmls))
        xb.add_policies(etree.XML(pxmls))
        xb.add_about_file("overview.html", "hello overview")

        xbin = str(xb)

        tdir = 'testdata'
        if not os.path.exists(tdir):
            os.mkdir(tdir)
        xb.export_to_directory(tdir)

        # test round trip

        xb2 = XBundle()
        xb2.import_from_directory(tdir + '/mitx.01')

        xbreloaded = str(xb2)

        if not xbin == xbreloaded:
            print "xbin"
            print xbin
            print "xbreloaded"
            print xbreloaded

        self.assertEqual(xbin, xbreloaded)

if __name__ == '__main__':
    unittest.main()
