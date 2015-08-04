#!/usr/bin/env python
#
# XBundle class
#
# an xbundle file is an XML format file with element <xbundle>, which
# includes the following sub-elements:
#
# <metadata>
#   <policies semester=...>: <policy> and <gradingpolicy>
#                            each contain the JSON for the corresponding file
#   <about>: <file filename=...> </about>
# </metadata>
# <course semester="...">: course XML </course>
#
# The XBundle class represents an xbundle file; it can read and write
# the file, and it can import and export to standard edX (unbundled) format.

import os
import sys
import re
import string
import glob
import subprocess

from lxml import etree
from lxml.html.soupparser import fromstring as fsbs
from path import path	# needs path.py

#-----------------------------------------------------------------------------

DEF_POLICY_JSON = """
{
    "course/2013_Spring": {
        "graceperiod": "1 day 5 hours 59 minutes 59 seconds",
        "start": "2013-02-19T14:15",
        "display_name": "The Challenges of Existence",
        "showanswer": "attempted",
        "rerandomize": "never",
        "show_calculator": "Yes",
        "tabs": [ {"type": "courseware"},
                  {"name": "Course Info", "type": "course_info"},
                  {"name": "Discussion", "type": "discussion"},
                  {"name": "Progress", "type": "progress"},
                  {"name": "Staff Grading", "type": "staff_grading"}
                ],
	"remote_gradebook": {
	    "name" : "STELLAR:/project/mitxdemosite",
	    "section" : "r01"
	    },
        "discussion_topics": {
            "General": {
                "sort_key": "A",
                "id": "4201x_Spring2013_General"
            },
            "Feedback": {
                "sort_key": "AA",
                "id": "4201x_Spring2013_Feedback"
            },
            "Troubleshooting": {
                "sort_key": "AB",
                "id": "4201x_Spring2013_Troubleshooting"
            }
        }
    }
}
"""

DEF_GRADING_POLICY_JSON = """
{
  "GRADER" : [
    {
      "type" : "Homework",
      "min_count" : 12,
      "drop_count" : 2,
      "short_label" : "HW",
      "weight" : 0.15
    },
    {
      "type" : "Lab",
      "min_count" : 12,
      "drop_count" : 2,
      "category" : "Labs",
      "weight" : 0.15
    },
    {
      "type" : "Midterm",
      "name" : "Midterm Exam",
      "short_label" : "Midterm",
      "weight" : 0.3
    },
    {
      "type" : "Final",
      "name" : "Final Exam",
      "short_label" : "Final",
      "weight" : 0.4
    }
  ],
  "GRADE_CUTOFFS" : {
    "A" : 0.87,
    "B" : 0.7,
    "C" : 0.6
  }
}
"""

#-----------------------------------------------------------------------------

class XBundle(object):
    '''
    An XBundle is defined by two elements: course and metadata.
    metadata includes policies and about.
    '''

    DescriptorTags = ['course','chapter','sequential','vertical','html','problem','video',
                      'conditional', 'combinedopenended', 'videosequence', 'problemset',
                      'wrapper', 'poll_question', 'randomize', 'proctor', 'discussion',
                      'staffgrading', ]
    KeepTogetherTags = []	# for latex2edx - simplier course structure
    MapTags = dict(section='sequential')
    DefaultSemester = '2013_Fall'
    DefaultOrg = 'MITx'
    PolicyTagMap = {'policy' : 'policy', 'gradingpolicy': 'grading_policy'}
    html_parser = etree.HTMLParser(compact=False,recover=True,remove_blank_text=True)

    def __init__(self, keep_urls=False, force_studio_format=False,
                 skip_hidden=False, keep_studio_urls=False,
                 no_overwrite=None,
                 ):
        '''
        if keep_urls=True then the original url_name attributes are kept upon import and export,
        if nonrandom (ie non-Studio).

        if keep_studio_urls=True and keep_urls=True, then keep random urls.

        no_overwrite: optional list of xml tags for which files should not be overwritten (eg course)
        '''
        self.course = etree.Element('course')
        self.metadata = etree.Element('metadata')
        self.urlnames = []
        self.xml = None				# only used if XML xbundle file was read in
        self.keep_urls = keep_urls
        self.force_studio_format = force_studio_format	# sequential must be followed by vertical in export
        self.skip_hidden = skip_hidden
        self.keep_studio_urls = keep_studio_urls
        self.no_overwrite = no_overwrite or []
        self.overwrite_files = []
        return


    #----------------------------------------
    # creation by parts

    def set_course(self,xml):
        if not xml.tag=='course':
            self.errlog('set_course should be called with a <course> element')
            return
        if not 'org' in xml.attrib:
            xml.set('org',self.DefaultOrg)
        semester = xml.get('url_name', xml.get('semester', self.DefaultSemester))
        if not 'semester' in xml.attrib:
            xml.set('semester', semester)
        self.semester = semester
        self.course = xml
        # fill up self.urlnames with existing ones if keep_urls
        if self.keep_urls:
            def walk(xml):
                un = xml.get('url_name','')
                if un:
                    self.urlnames.append(un)
                if xml.tag in self.DescriptorTags:
                    for child in xml:
                        walk(child)
            walk(xml)


    def add_policies(self, policies):
        '''add a policies XML subtree to the metadata'''
        self.metadata.append(policies)


    def add_about_file(self, filename, filedata):
        '''add a file to the about element'''
        about = self.metadata.find('about')
        if about is None:
            about = etree.SubElement(self.metadata,'about')
        abfile = etree.SubElement(about, 'file')
        abfile.set('filename',filename)
        # Unicode characters in the "about" HTML file were causing
        # the lxml package to break.
        abfile.text = filedata.decode('utf-8')

    #----------------------------------------
    # load/save

    def load(self, fn):
        """
        Load from xbundle.xml file
        """
        self.xml = etree.parse(fn).getroot()
        self.course = self.xml.find('course')
        self.metadata = self.xml.find('metadata')
        self.errlog("course id = %s" % self.course_id())


    def save(self, fn='xbundle.xml', fp=None):
        """
        Save to xbundle.xml file
        """
        if fp is None:
            fp = open(fn,'w')
        fp.write(str(self))


    def __str__(self):
        xml = etree.Element('xbundle')
        self.xml = xml
        xml.append(self.metadata)
        xml.append(self.course)
        return self.pp_xml(xml)

    #----------------------------------------
    # import/export


    def import_from_directory(self, dir='./'):
        '''
        Create xbundle from edX xml directory.
        Using this is a great way to sanitize directory structure
        and also normalize url_name filenames (and make them
        meaningfully human readable).
        '''
        dir = path(dir)
        self.metadata = etree.Element('metadata')
        self.import_metadata_from_directory(dir)
        self.import_course_from_directory(dir)


    def import_metadata_from_directory(self, dir):
        # load policies
        # print "ppath = ", (path(dir) / 'policies/*')
        for pdir in glob.glob(path(dir) / 'policies/*'):
            # print "pdir=",pdir
            policies = etree.Element('policies')
            policies.set('semester',os.path.basename(pdir))
            for fn in glob.glob(path(pdir) / '*.json'):
                x = etree.SubElement(policies,os.path.basename(fn).replace('_','').replace('.json',''))
                x.text = open(fn).read()
            self.add_policies(policies)

        # load about files
        for afn in glob.glob(dir / 'about/*'):
            try:
                self.add_about_file(os.path.basename(afn), open(afn).read())
            except Exception as err:
                print "Oops, failed to add file %s, error=%s" % (afn, err)


    def import_course_from_directory(self, dir):
        '''load course tree, removing intermediate descriptors with url_name'''
        dir = path(dir)
        x = etree.parse(dir / 'course.xml').getroot()
        semester = x.get('url_name','')		# the url_name of <course> is special - the semester
        cxml = self.import_xml_removing_descriptor(dir, x)
        cxml.set('semester',semester)
        self.course = cxml
        self.fix_old_course_section()
        self.fix_old_descriptor_name(self.course)
        # print self.pp_xml(self.course)


    def fix_old_descriptor_name(self, xml):
        '''
        Turn name -> display_name on descriptor tags
        '''
        if xml.tag in self.DescriptorTags:
            if 'name' in xml.attrib and not xml.get('display_name',''):
                xml.set('display_name',xml.get('name'))
                xml.attrib.pop('name')
            for child in xml:
                self.fix_old_descriptor_name(child)


    def fix_old_course_section(self):
        '''
        Remove <section>
        '''
        for sect in self.course.findall('.//section'):
            for seq in sect.findall('.//sequential'):
                for k in seq:
                    seq.addprevious(k)
                sect.remove(seq)		# remove sequential from inside section
            sect.tag = 'sequential'


    def is_not_random_urlname(self, un):
        if self.keep_studio_urls:		# keep url even if random looking
            return True
        # random urlname eg: 55bc076ad06e4ede9d0561948c03be2f
        nrand = len('55bc076ad06e4ede9d0561948c03be2f')
        if not len(un)==nrand:
            return True
        ndigits = len([z for z in un if z in string.digits])
        if ndigits<6:
            return True
        return False	# ie seems to be random


    def update_metadata_from_policy(self, xml):
        # update metadaa for this element from policy, if exists
        policy = getattr(self,'policy')
        pkey = '%s/%s' % (xml.tag, xml.get('url_name',xml.get('url_name_orig','<no_url_name>')))
        if policy and pkey in policy:
            #print "policy match for %s" % pkey
            for (k,v) in policy[pkey].iteritems():
                #if 'hide' in k:
                #    print "metadata: %s" % [k,v]
                if xml.get(k,None) is None:	# don't overwrite xml's metadata setting, if exists already
                    xml.set(k,str(v))


    def import_xml_removing_descriptor(self, dir, xml):
        '''
        load XML file, recursively following and removing intermediate
        descriptors with url_name.

        if element is a DescriptorTag element, and display_name is missing, then
        use its url_name, if that is available.

        dir should be a path.
        '''
        un = xml.get('url_name','')
        if xml.tag in self.DescriptorTags and 'url_name' in xml.attrib and un:
            unfn = un.replace(':','/')		# colon -> subdir slash in url_name
            fn = dir / xml.tag / (unfn+'.xml')
            if not os.path.exists(fn):
                # print "[xbundle] Skipping %s, does not exist" % fn
                return xml
            try:
                dxml = etree.parse(fn).getroot()
            except Exception as err:
                print "[xbundle] Error parsing xml for %s" % fn
                raise
            try:
                dxml.attrib.update(xml.attrib)
            except Exception as err:
                print "[xbundle] error updating attribute, dxml=%s\nxml=%s"  % (etree.tostring(dxml), etree.tostring(xml))
                print "dxml.attrib=%s" % dxml.attrib
                print "xml.attrib=%s" % xml.attrib
                print "likely your version of lxml is too old (need version >= 3)"
                raise
            dxml.attrib.pop('url_name')

            if self.keep_urls and self.is_not_random_urlname(un):
                dxml.set('url_name_orig', un)	# keep url_name as url_name_orig

            if dxml.tag in self.DescriptorTags and dxml.get('display_name') is None:
                if not dxml.tag=='course':	# special case: don't add display_name to course
                    dxml.set('display_name',un)

            if self.skip_hidden:
                self.update_metadata_from_policy(dxml)
                if xml.get('hide_from_toc','')=='true':
                    print "[xbundle] Skipping %s (%s), it has hide_from_toc=true" % (xml.tag, xml.get('display_name','<noname>'))
                else:
                    xml = dxml
            else:
                xml = dxml

        fn = xml.get('filename','')
        if xml.tag in ['html','problem'] and fn: # special for <html filename="..." display_name="..."/>
                                                 # and <problem filename="...">
            if xml.tag=='html':
                if not fn.endswith('.html'):
                    fn += '.html'
                #if not fn.startswith('html/'):
                #    fn = 'html/' + fn
                options = dict(parser=self.html_parser)
            elif xml.tag=='problem':
                if not fn.endswith('.xml'):
                    fn += '.xml'
                #if not fn.startswith('problems/'):
                #    fn = 'problems/' + fn
                options = {}

            if not os.path.exists(dir/xml.tag/fn):
                if '-' in fn:
                    fn = '%s/%s' % (fn.split('-',1)[0], fn)
            try:
                dxml = etree.parse(dir / xml.tag / fn, **options).getroot()
            except Exception as err:
                print "Error!  Can't load and parse HTML file %s, error:" % (dir/xml.tag/fn)
                print err
                dxml = None
            if dxml is not None:
                if 'xmlns' in dxml.attrib:
                    dxml.attrib.pop('xmlns')
                dxml.attrib.update(xml.attrib)
                dxml.attrib.pop('filename')
                if dxml.tag in self.DescriptorTags and dxml.get('display_name') is None:
                    dxml.set('display_name',un)
                xml = dxml

        if self.skip_hidden:
            self.update_metadata_from_policy(xml)
            if xml.get('hide_from_toc','')=='true':
                print "[xbundle] Skipping %s (%s), it has hide_from_toc=true" % (xml.tag, xml.get('display_name','<noname>'))
                return xml

        for child in xml:
            dchild = self.import_xml_removing_descriptor(dir, child)	# recurse
            if not dchild==child:
                child.addprevious(dchild)	# replace descriptor with contents
                xml.remove(child)
        return xml


    def export_to_directory(self, exdir='./', xml_only=False, newfmt=True):
        '''
        Export xbundle to edX xml directory
        First insert all the intermediate descriptors needed.
        Do about and XML separately.
        '''
        coursex = etree.Element('course')
        semester = self.course.get('semester', '')
        semester = semester.replace(' ', '_')		# no spaces in url_name (should do more checks here)
        self.course.set('semester', semester)		# replace attribute just in case
        coursex.set('url_name', semester)
        coursex.set('org', self.course.get('org', ''))
        if newfmt:
            coursex.set('course', self.course.get('course',
                        self.course.get('number', '')))
        else:
            coursex.set('number', self.course.get('number', ''))  # backwards compatibility

        self.export = self.make_descriptor(self.course, semester)
        self.export.append(self.course)
        self.add_descriptors(self.course)

        # print self.pp_xml(self.export)

        self.dir = self.mkdir(path(exdir) / self.course_id())
        if not xml_only:
            self.export_meta_to_directory()
        self.export_xml_to_directory(self.export[0], dowrite=True)

        # write out top-level course.xml

        self.write_xml_file(self.dir / 'course.xml', coursex)


    def export_meta_to_directory(self):
        '''
        Write out metadata (about and policy) to directory.
        '''
        pdir = self.mkdir(self.dir / 'policies')
        for pxml in self.metadata.findall('policies'):
            semester = pxml.get('semester')
            dir = self.mkdir(pdir / semester)
            for k in pxml:
                fn = self.PolicyTagMap.get(k.tag, k.tag) + '.json'
                open(dir / fn, 'w').write(k.text)  # write out content to policy directory file

        adir = self.mkdir(self.dir / 'about')
        for fxml in self.metadata.findall('about/file'):
            fn = fxml.get('filename')
            try:
                fp = open(adir / fn, 'w')
                if fxml.text is not None and len(fxml.text):
                    fp.write(fxml.text)
                fp.close()
            except Exception as err:
                self.errlog('failed to write about file %s, error %s' % (adir / fn, err))


    def write_xml_file(self, fn, xml, force_overwrite=False):
        if (not force_overwrite) and (xml.tag in self.no_overwrite) and os.path.exists(fn):
            print "[xbundle] Not overwriting %s for %s" % (fn, xml)
            fn = fn + '.new'
            self.overwrite_files.append(fn)
        open(fn, 'w').write(self.pp_xml(xml))

    def export_xml_to_directory(self, elem, dowrite=False):
        '''
        Do this recursively.  If an element is a descriptor, then put that in its own
        subdirectory.
        '''
        def write_xml(x):
            un = x.get('url_name')
            if un is None:
                self.errlog("Oops!  error in export_xml_to_directory, missing url_name:")
                self.errlog(x)
            elem.attrib.pop('url_name')
            if 'url_name_orig' in elem.attrib and self.keep_urls:
                elem.attrib.pop('url_name_orig')
            edir = self.mkdir(self.dir / x.tag)
            # Check for any ':' symbols in the url_name and create appropriate subdirectories
            subdirs = un.split(':')
            for newdir in subdirs[:-1] :
                edir = self.mkdir(edir / newdir)
            un = subdirs[-1]
            self.write_xml_file(edir / un + '.xml', x)
            return un

        # print elem
        if elem.tag == 'descriptor':
            # print "--> %s" % list(elem)
            self.export_xml_to_directory(elem[0], dowrite=True)  # recurse on children, depth first
            elem.tag = elem.get('tag')			# change descriptor to point to new elem
            elem.set('url_name', elem.get('url_name'))
            elem.attrib.pop('tag')
            # self.export_xml_to_directory(elem)	# recurse on this tag

        elif elem.tag == etree.Comment:			# comment <!-- foo -->
            pass

        elif elem.tag not in self.DescriptorTags:  # don't recurse if not a DescriptorTag
            pass

        # elif elem.get('url_name') is None:
        #    pass

        else:
            if elem.findall('.//descriptor'):		# if any descriptors in children
                for k in elem:
                    self.export_xml_to_directory(k)  # recurse on children (don't necessarily write)
            if dowrite:
                write_xml(elem)		                # write to file and remove from parent
                elem.getparent().remove(elem)


    def course_id(self):
        return self.course.get('course', '')


    def errlog(self, msg):
        print msg


    def mkdir(self, p):
        '''p is a path'''
        if not p.exists():
            p.mkdir()
        return p


    def pp_xml(self, xml):
        # os.popen('xmllint --format -o tmp.xml -','w').write(etree.tostring(xml))
        try:
            p = subprocess.Popen(['xmllint', '--format', '-o', 'tmp.xml', '-'], stdin=subprocess.PIPE)
            p.stdin.write(etree.tostring(xml))
            p.stdin.close()
            p.wait()
            xml = open('tmp.xml').read()
        except Exception as err:
            print "[xbundle.py] Warning - no xmllint"
            xml = etree.tostring(xml, pretty_print=True)

        if xml.startswith('<?xml '):
            xml = xml.split('\n', 1)[1]
        return xml

    def make_urlname(self, xml, parent=''):
        dn = xml.get('display_name', '')
        s = dn
        if not s:
            xmlp = xml.getparent()
            s = xmlp.get('display_name', '')  # if no display_name, try to use parent's
            if not s:
                s = xmlp.tag
        s += " " + xml.tag
        s = s.encode('ascii', 'xmlcharrefreplace')
        map = {'"\':<>?|![]': '',
               ',/().;=+ ': '_',
               '/': '__',
               '&': 'and',
               }
        for m, v in map.items():
            for ch in m:
                s = s.replace(ch, v)
        if dn and s in self.urlnames and parent:
            s += '_' + parent
        while s in self.urlnames:
            m = re.match('(.+?)([0-9]*)$', s)
            (s, idx) = m.groups()
            idx = int(idx or 0)
            s += str(idx + 1)
        self.urlnames.append(s)
        return s


    def make_descriptor(self, xml, url_name='', parent=''):
        """
        Construct and return a descriptor element for the given element
        at the head of xml.

        Use url_name for the descriptor, if given.
        """
        descriptor = etree.Element('descriptor')
        descriptor.set('tag', xml.tag)
        uno = xml.get('url_name_orig', '')
        if self.keep_urls and not url_name and uno and self.is_not_random_urlname(uno):
            url_name = uno
        if not url_name:
            url_name = self.make_urlname(xml, parent=parent)
        descriptor.set('url_name', url_name)
        xml.set('url_name', url_name)
        return descriptor


    def add_descriptors(self, xml, parent=''):
        '''
        Recursively walk through self.course and add descriptors
        A descriptor is an intermediate tag, which points to content
        via a url_name.  These are used by edX to simplify loading
        of course content.
        '''
        for elem in xml:
            if self.force_studio_format:
                if xml.tag == 'sequential' and not elem.tag == 'vertical':  # studio needs seq -> vert -> other
                    # move child into vertical
                    vert = etree.Element('vertical')
                    elem.addprevious(vert)
                    # vert.set('display_name', 'vert_'+elem.get('display_name',''))
                    vert.set('url_name', self.make_urlname(vert))
                    vert.append(elem)
                    elem = vert			# continue processing on the vertical
            # if elem.tag in self.DescriptorTags and not elem.get('url_name',''):
            if elem.tag in self.DescriptorTags:
                if not elem.tag in self.KeepTogetherTags:
                    un = elem.get('url_name', '')
                    desc = self.make_descriptor(elem, url_name=un, parent=parent)
                    elem.addprevious(desc)
                    desc.append(elem)		# move descriptor to become new parent of elem
                else:
                    desc = elem
                self.add_descriptors(elem, desc.get('url_name', ''))  # recurse

# ----------------------------------------------------------------------------
# tests


def RunTests():  # pragma: no cover
    import unittest

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

    ts = unittest.makeSuite(TestXBundle)
    ttr = unittest.TextTestRunner()
    ttr.run(ts)


# ----------------------------------------------------------------------------
# main

if __name__ == '__main__':

    def usage():
        print "Usage: python xbundle.py [--force-studio] [cmd] [infn] [outfn]"
        print "where:"
        print "  cmd = test:    run unit tests"
        print "  cmd = convert: convert between xbundle and edX directory format"
        print "                 the xbundle filename must end with .xml"
        print "  --force-studio forces <sequential> to always be followed by <vertical> in export"
        print "                 this makes it compatible with Studio import"
        print ""
        print "examples:"
        print "  python xbundle.py convert ../data/edx4edx edx4edx_xbundle.xml"
        print "  python xbundle.py convert edx4edx_xbundle.xml ./"

    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    argc = 1
    options = dict(keep_urls=True)
    if len(sys.argv) > argc and sys.argv[argc] == '--force-studio':
        argc += 1
        options['force_studio_format'] = True

    cmd = sys.argv[argc]

    if cmd == 'test':
        RunTests()

    elif cmd == 'convert':
        argc += 1
        infn = sys.argv[argc]
        outfn = sys.argv[argc + 1]
        xb = XBundle(**options)
        if infn.endswith('.xml'):
            print "Converting xbundle file '%s' to edX xml directory '%s'" % (infn, outfn)
            xb.load(infn)
            xb.export_to_directory(outfn)
            print "done"
        elif outfn.endswith('.xml'):
            print "Converting edX xml directory '%s' to xbundle file '%s'" % (infn, outfn)
            xb.import_from_directory(infn)
            xb.save(outfn)
            print "done"
        else:
            usage()
    else:
        usage()
