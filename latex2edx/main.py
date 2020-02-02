#!/usr/bin/env python

import datetime
import json
import optparse
import os
import re
import py_compile
import sys
import tempfile
import urllib.request, urllib.parse, urllib.error
from . import xbundle
import pkg_resources

try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict

try:
    from path import path	# needs path.py
except Exception as err:
    from path import Path as path

from lxml import etree
from .plastexit import plastex2xhtml
from .course_tests import AnswerBoxUnitTest, CourseUnitTestSet
from .abox import split_args_with_quoted_strings

# from logging import Logger

# -----------------------------------------------------------------------------

DEFAULT_CONFIG = {
    'problem_default_attributes': {
        'showanswer': 'closed',
        'rerandomize': 'never',
    }
}

# -----------------------------------------------------------------------------


def date_parse(datestr, retbad=False, verbose=True):
    '''
    Helpful general function for parsing dates.
    Returns datetime object, or None
    '''
    if not datestr:
        return None

    formats = ['%Y-%m-%dT%H:%M:%SZ',    	# 2013-11-13T21:00:00Z
               '%Y-%m-%dT%H:%M:%S.%f',    	# 2012-12-04T13:48:28.427430
               '%Y-%m-%dT%H:%M:%S.%f+00:00',    	# 2013-12-15T18:33:32.378926+00:00
               '%Y-%m-%dT%H:%M:%S',
               '%Y-%m-%dT%H:%M',		# 2013-02-12T19:00
               '%Y-%m-%d %H:%M:%S',		# 2013-05-29 12:51:48
               '%Y-%m-%d',			# 2013-05-29
               '%B %d, %Y',			# February 25, 2013
               '%B %d, %H:%M, %Y', 		# December 12, 22:00, 2012
               '%B %d, %Y, %H:%M', 		# March 25, 2013, 22:00
               '%B %d %Y, %H:%M',		# January 2 2013, 22:00
               '%B %d %Y', 			# March 13 2014
               '%B %d %H:%M, %Y',		# December 24 05:00, 2012
               ]

    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(datestr, fmt)
            return dt
        except Exception:
            continue

    if verbose:
        print("--> Date %s unparsable" % datestr)
    if retbad:
        return "Bad"
    return None

# -----------------------------------------------------------------------------


class latex2edx(object):
    '''
    latex2edx works in three stages:

    1. use plastex to convert .tex file to .xhtml, with special edX macros (via py & zpts)
    2. clean up .xhtml file and convert into single .xml file, "xbundle" format
    3. convert xbundle into directory with standard XML format files for edX

    This script can be run from any directory.
    '''

    DescriptorTags = ['course', 'chapter', 'sequential', 'vertical', 'html', 'problem', 'video',
                      'conditional', 'combinedopenended', 'randomize', 'discussion', 'lti']

    def __init__(self,
                 fn,
                 fp=None,
                 extra_filters=None,
                 latex_string=None,
                 add_wrap=False,
                 extra_xml_filters=None,
                 verbose=False,
                 output_fn=None,
                 output_dir='',
                 do_merge=False,
                 imurl='images',
                 do_images=True,
                 update_policy=False,
                 suppress_policy=False,
                 suppress_verticals=False,
                 section_only=False,
                 xml_only=False,
                 units_only=False,
                 popup_flag=False,
                 allow_dirs=False,
                 output_cutset='',
                 add_timestamp=False,
                 timestamp_revision="",
                 timestamp_threshold=10,
                 ):
        '''
        extra_xml_filters = list of functions acting on XML, applied to XHTML

        output_cutset = `str` : set to filename to store output course unit tests for answer boxes.  These tests can be run using edxcut.
        '''

        if not output_dir:
            output_dir = os.path.abspath('.')
        self.output_dir = path(output_dir)
        imdir = self.output_dir / 'static/images'

        if do_images:  # make directories only if do_images
            if not os.path.exists(self.output_dir):
                os.mkdir(self.output_dir)
            if not os.path.exists(self.output_dir / 'static'):
                os.mkdir(self.output_dir / 'static')
            if not os.path.exists(imdir):
                os.mkdir(imdir)

        self.p2x = plastex2xhtml(fn, fp=fp, extra_filters=extra_filters,
                                 latex_string=latex_string,
                                 add_wrap=add_wrap,
                                 verbose=verbose,
                                 imdir=imdir,
                                 imurl=imurl,
                                 )
        self.p2x.convert()
        self.xhtml = self.p2x.xhtml
        self.do_merge = do_merge
        self.update_policy = update_policy
        self.suppress_policy = suppress_policy
        self.section_only = section_only
        self.suppress_verticals = suppress_verticals
        self.xml_only = xml_only
        self.units_only = units_only
        self.popup_flag = popup_flag
        self.verbose = verbose
        self.the_xml = None
        self.allow_dirs = allow_dirs
        self.output_cutset = output_cutset
        self.add_timestamp = add_timestamp
        self.timestamp_revision = timestamp_revision
        self.timestamp_threshold = timestamp_threshold

        if output_fn is None or not output_fn:
            if fn.endswith('.tex'):
                output_fn = fn[:-4] + '.xbundle'
            else:
                output_fn = fn + '.xbundle'
        self.output_fn = output_fn

        self.fix_filters = [self.fix_xhtml_descriptor_in_p,
                            self.fix_attrib_string,
                            self.add_url_names,
                            self.fix_table,
                            self.fix_table_p,
                            self.fix_latex_minipage_div,
                            self.handle_refs,
                            self.process_edxcite,
                            self.process_askta,
                            self.process_showhide,
                            self.process_edxxml,
                            self.process_dndtex,  # must come before process_include
                            self.process_include,
                            self.process_includepy,
                            self.process_video,
                            self.process_lti,
                            self.process_split_test,
                            self.process_custom_html,
                            self.process_marginote,
                            self.process_general_hint_system,
                            self.check_all_python_scripts,
                            self.handle_policy_settings,
                            self.process_add_timestamp,
                            ]
        if extra_xml_filters:
            self.fix_filters += extra_xml_filters

        if self.output_cutset:
            self.fix_filters.append(self.generate_course_unit_tests)

        self.URLNAMES = []

    def save_xml(self):
        '''
        Save XML file (as .xbundle, normally) to the output_fn
        '''
        open(self.output_fn, 'w').write(etree.tostring(self.xml, pretty_print=True).decode())

    def export_sections_only(self):
        '''
        Export sequentials only (no course, no chapters).
        Also save the initial XML as the xbundle file
        '''
        self.save_xml()
        xb = xbundle.XBundle(force_studio_format=(not self.suppress_verticals), keep_urls=True)
        xb.dir = self.output_dir

        tags = ['sequential', 'problem', 'html', 'video']
        for tag in tags:
            print("    %s: %d" % (tag, len(self.xml.findall('.//%s' % tag))))

        for seq in self.xml.findall('.//sequential'):
            nprob = len(seq.findall('.//problem'))
            nhtml = len(seq.findall('.//html'))
            print("--> exporting sequential %s (%d problem, %d html)" % (seq.get('display_name', '<unknown display_name>'),
                                                                         nprob, nhtml))
            xb.add_descriptors(seq)
            xb.export_xml_to_directory(seq, dowrite=True)

    def export_units_only(self):
        '''
        Export units (problem, html, video) only (no course, no chapters).
        Also save the initial XML as the xbundle file
        '''
        self.save_xml()
        xb = xbundle.XBundle(force_studio_format=(not self.suppress_verticals), keep_urls=True)
        xb.dir = self.output_dir

        tags = ['problem', 'html', 'video']
        for tag in tags:
            print("    %s: %d" % (tag, len(self.xml.findall('.//%s' % tag))))

        for tag in tags:
            for unit in self.xml.findall('.//%s' % tag):
                print("--> exporting %s (%s) url_name=%s" % (unit.get('display_name', '<unknown display_name>'),
                                                             self.get_filename_and_linenum(unit),
                                                             unit.get('url_name', '<unknown>'),
                                                             ))
                xb.add_descriptors(unit)
                xb.export_xml_to_directory(unit, dowrite=True)

    @property
    def xml(self):
        '''
        Compute our XML representation by parsing the XHTML from plastex into XML, then running it through
        all the fix_filters.

        Cache result, so we only do the computation once.

        Returns a string (giving the filter-processed XML representation)
        '''
        if self.the_xml is None:
            try:
                xml = etree.fromstring(self.xhtml)
            except Exception as err:
                print(("Error!  Failed to convert xhtml string into proper XML, err=%s" % str(err)))
                print(("xhtml string = %s" % self.xhtml))
                raise
            for filter in self.fix_filters:
                filter(xml)
            self.the_xml = xml
        return self.the_xml

    def convert(self):
        '''
        Convert xhtml to xbundle and then xbundle to directory of XML files.
        if self.do_merge then do not overwrite course files; attempt to merge them.
        '''
        if self.section_only and self.xml_only:
            print("Saving XML to file %s" % self.output_fn)
            return self.save_xml()

        if self.section_only:
            # if section_only then only export edXsections (sequentials)
            return self.export_sections_only()

        if self.units_only:
            return self.export_units_only()

        self.xhtml2xbundle()
        self.xb.save(self.output_fn)
        print("xbundle generated (%s): " % self.output_fn)
        tags = ['chapter', 'sequential', 'problem', 'html', 'video', 'lti']
        for tag in tags:
            print("    %s: %d" % (tag, len(self.xb.course.findall('.//%s' % tag))))
        if self.xml_only:
            print("Saved xbundle XML to file %s" % self.output_fn)
            return
        self.xb.export_to_directory(self.output_dir, xml_only=True)
        print("Course exported to %s/" % self.output_dir)

        if self.do_merge and self.xb.overwrite_files:
            self.merge_course()

    def merge_course(self):
        print("    merging files %s" % self.xb.overwrite_files)
        for fn in self.xb.overwrite_files:
            if str(fn).endswith('course.xml.new'):
                # course.xml shouldn't need merging
                os.unlink(fn)
            else:
                newcourse = etree.parse(open(fn)).getroot()
                oldfn = fn[:-4]
                oldcourse = etree.parse(open(oldfn)).getroot()
                oldchapters = [x.get('url_name') for x in oldcourse]
                newchapters = []
                for chapter in newcourse:
                    if chapter.get('url_name') in oldchapters:
                        continue  # already in old course, skip
                    oldcourse.append(chapter)  # wasn't in old course, move it there
                    newchapters.append(chapter.get('url_name'))
                self.xb.write_xml_file(oldfn, oldcourse, force_overwrite=True)
                os.unlink(fn)
                print("    added new chapters %s" % newchapters)

    def xhtml2xbundle(self):
        '''
        Convert XHTML output of PlasTeX to an edX xbundle file.
        Use lxml to parse the XML and extract the desired parts.
        '''
        xml = self.xml
        no_overwrite = ['course'] if self.do_merge else []
        xb = xbundle.XBundle(force_studio_format=(not self.suppress_verticals), keep_urls=True,
                             no_overwrite=no_overwrite)
        xb.KeepTogetherTags = ['sequential', 'vertical', 'conditional']
        course = xml.find('.//course')
        if course is not None:
            xb.set_course(course)
        self.xb = xb
        return xb

    def handle_policy_settings(self, tree):
        '''
        Policy settings are those normally stored in the policies/semester/policy.json
        file.  These include

        - start       : start date
        - end         : end date
        - due         : due date
        - graded      : true/false for graded or not
        - showanswer  : when to allow "show answer"
        - format      : 'grading format' - ie which collection graded components to be part of

        We (optionally) strip these settings from the XML, and (optionally) save them
        in the policy.json file, by updating that file (and not removing other info there).
        '''
        if (not self.suppress_policy) and (not self.update_policy):
            return

        def fixdate(dtin):
            dt = date_parse(dtin)
            if dt is None:
                print("--> Error: bad date '%s' given for policy setting" % dtin)
                raise
            return dt.strftime('%Y-%m-%dT%H:%M')

        def makebool(x):
            if 'true' in x.lower():
                return 'true'
            elif 'false' in x.lower():
                return 'false'
            print("--> Warning: in policy settings turning %s in to false" % x)
            return 'false'

        policy_settings = {'start': fixdate, 'end': fixdate, 'due': fixdate,
                           'graded': makebool, 'showanswer': None, 'format': None}

        if self.update_policy:
            course = tree.find('.//course')
            semester = course.get('semester', course.get('url_name'))
            policydir = self.output_dir / 'policies' / semester
            if not policydir.exists():
                print("--> Creating directory %s" % policydir)
                os.system('mkdir -p "%s"' % policydir)
            policyfile = policydir / 'policy.json'
            if not policyfile.exists():
                print("--> No existing policy.json, creating default")
                policy = OrderedDict()
                policy["course/%s" % semester] = OrderedDict(
                    start="2012-06-02T02:00",
                    end="2012-08-12T00:00",
                )
            else:
                policy = json.load(open(policyfile), object_pairs_hook=OrderedDict)

            def copy_settings(elem, policy):
                key = "%s/%s" % (elem.tag, elem.get('url_name'))
                if key not in policy:
                    policy[key] = OrderedDict()
                for setting, ffun in list(policy_settings.items()):
                    val = elem.get(setting, None)
                    if val is not None:
                        if ffun is None:
                            sval = val
                        else:
                            try:
                                sval = ffun(val)
                            except Exception:
                                msg = "Error processing element %s in %s" % (elem.tag, self.get_filename_and_linenum(elem))
                                raise Exception(msg)
                        policy[key][setting] = sval

            copy_settings(course, policy)		    # do course first

            for chapter in tree.findall('.//chapter'):
                copy_settings(chapter, policy)
                for sequential in chapter.findall('.//sequential'):
                    copy_settings(sequential, policy)

            with open(policyfile, 'w') as fp:
                fp.write(json.dumps(policy, indent=2))

        def suppress_policy_settings(elem):
            for setting in policy_settings:
                if setting in list(elem.keys()):
                    elem.attrib.pop(setting)

        if self.suppress_policy or self.update_policy:
            for chapter in tree.findall('.//chapter'):
                suppress_policy_settings(chapter)
                for sequential in chapter.findall('.//sequential'):
                    suppress_policy_settings(sequential)

    @staticmethod
    def fix_table(tree):
        '''
        Force tables to have table-layout: auto, no borders on table data
        '''
        for table in tree.findall('.//table'):
            table.set('style', 'table-layout:auto')
            for td in table.findall('.//td'):
                newstyle = td.get('style', '')
                if newstyle:
                    newstyle += '; '
                newstyle += 'border:none'
                td.set('style', newstyle)

    @staticmethod
    def fix_table_p(tree):
        '''
        Force "tabular" tables to not have <p> as top-level within <td>.
        Those <p> mess up table spacing.
        '''
        for table in tree.findall('.//table[@class="tabular"]'):
            for td in table.findall('.//td'):
                if not len(td):
                    continue
                tdtop = td[0]
                if tdtop.tag == 'p':
                    for elem in tdtop:
                        tdtop.addprevious(elem)
                td.text = (td.text or '') + tdtop.text
                td.remove(tdtop)

    @staticmethod
    def fix_latex_minipage_div(tree):
        '''
        latex minipages turn into things like <div style="width:216.81pt" class="minipage">...</div>
        but inline math inside does not render properly.  So change div to text.
        '''
        for div in tree.findall('.//div[@class="minipage"]'):
            div.tag = 'text'

    def set_tmploc(self, tree, locstr):
        '''
        Create a tmploc attribute (if none exists) for the elements:
          tocref, toclabel, ref, label, index,
          table class="equation", table class="eqnarray",
          div class="figure"
        so as to later be able to reference these items by addressing their
        location.
        '''
        for elem in tree.xpath('.//tocref|.//toclabel|.//label|'
                               './/table[@class="equation"]|'
                               './/table[@class="eqnarray"]|'
                               './/div[@class="figure"]|'
                               './/ref|.//index'):
            if elem.get('tmploc') is None:
                elem.set('tmploc', locstr)

    def handle_refs(self, tree):
        '''
        Process references to sections of content -- create section numbering and
        reference should be a link that opens in a new tab to the desired component.
        If the --popups option is specified, equations and figure references open a new window.
        '''
        if self.section_only:
            return
        if self.units_only:
            return
        # EVH: Build course map from tree.
        course = tree.find('.//course')
        if course is None:
            return
        cnumber = course.get('number')
        # EVH: Navigate course and set a 'tmploc' attribute with location for desired items
        maplist = []  # ['loc. str.']
        mapdict = {}  # {'location str.':['URL','display_name','refnum']}
        chapnum = 0
        chapref = seqref = vertref = '0'
        for chapter in tree.findall('.//chapter'):
            chapnum += 1
            if chapter.get('refnum') is not None:
                chapref = chapter.get('refnum')
                seqref = vertref = '0'
            chapurl = chapter.get('url_name')
            locstr = '{}'.format(chapnum)
            maplist.append(locstr)
            mapdict[locstr] = [
                '{}'.format(chapurl),
                chapter.get('display_name'), chapref]
            labels = [
                chapter.find('./p/label'), chapter.find('./label'),
                chapter.find('./p/toclabel'), chapter.find('./toclabel')]
            for label in labels:
                if label is not None:
                    label.set('tmploc', locstr + '.0')
            seqnum = 0
            for child1 in chapter:
                if child1.tag == 'p' and (child1.find('./') is not None):
                    seq = child1[0]
                else:
                    seq = child1
                if seq.tag not in ['sequential', 'vertical', 'section']:
                    continue
                seqnum += 1
                if seq.get('refnum') is not None:
                    seqref = seq.get('refnum')
                    vertref = '0'
                sequrl = seq.get('url_name')
                locstr = '{}.{}'.format(chapnum, seqnum)
                maplist.append(locstr)
                mapdict[locstr] = [
                    '{}/{}'.format(chapurl, sequrl),
                    seq.get('display_name'), '.'.join([chapref, seqref])]
                labels = [
                    seq.find('./p/label'), seq.find('./label'),
                    seq.find('./p/toclabel'), seq.find('./toclabel')]
                for label in labels:
                    if label is not None:
                        label.set('tmploc', locstr + '.0')
                if seqnum == 1:
                    mapdict['{}'.format(chapnum)][0] = (
                        '{}/{}/1'.format(chapurl, sequrl))
                vertnum = 0
                for child2 in seq:
                    if child2.tag == 'p' and (child2.find('./') is not None):
                        vert = child2.find('./')
                    else:
                        vert = child2
                    if vert.tag not in ['sequential', 'vertical', 'section',
                                        'problem', 'html']:
                        continue
                    vertnum += 1
                    if vert.get('refnum') is not None:
                        vertref = vert.get('refnum')
                    locstr = '{}.{}.{}'.format(chapnum, seqnum, vertnum)
                    maplist.append(locstr)
                    mapdict[locstr] = [
                        '{}/{}/{}'.format(chapurl, sequrl, vertnum),
                        vert.get('display_name'),
                        '.'.join([chapref, seqref, vertref])]
                    labels = [
                        vert.find('./p/label'), vert.find('./label'),
                        vert.find('./p/toclabel'), vert.find('./toclabel')]
                    for label in labels:
                        if label is not None:
                            label.set('tmploc', locstr + '.0')
                    self.set_tmploc(vert, locstr)
                locstr = '.'.join(locstr.split('.')[:-1])
                self.set_tmploc(seq, locstr)
            locstr = '.'.join(locstr.split('.')[:-1])
            self.set_tmploc(chapter, locstr)
        # EVH 01-13-15: tmploc assignment added at course level
        self.set_tmploc(course, '0')
        mapdict['0'] = ['#', cnumber, '0']
        # EVH: Handle figure references. Search for labels and build dictionary
        figdict = {}  # {'figlabel':'fignum'}
        figattrib = {}  # {'figlabel':{'attrib':'value'}}
        for fig in tree.findall('.//div[@class="figure"]'):
            locstr = fig.attrib.pop('tmploc')
            # Retrieve Figure number if it is captioned
            caption = fig.find('.//div[@class="caption"]/b')
            if caption is not None:
                fignum = caption.text.split(' ')[1]
            figlabel = None
            label = fig.find('.//label')
            if label is not None:
                figlabel = label.text
                figdict[figlabel] = fignum
                plabel = label.getparent()
                if plabel.tag == 'p':  # TODO: Find a clean way to build eTree
                    label = plabel
                    plabel = plabel.getparent()
                plabel.remove(label)
            if figlabel is not None:
                # CHAD: for multi-image figures, collect all the image names
                # TODO: Find example and investigate how to refine (as above)
                fig.set('id', 'fig{}'.format(fignum))
                figattrib[figlabel] = {
                    'href': '{}#fig{}'.format(mapdict[locstr][0], fignum),
                    'onClick': 'location.reload()'}
                if self.popup_flag:
                    imgsrcs = []
                    for img in fig.findall('.//img'):
                        imgsrc = img.get('src')
                        imgsrcs.append(imgsrc)
                    if len(imgsrcs) == 1:  # single image figure
                        figfile = imgsrcs[0]
                        # TODO: Find a way to resize popup window to the figure
                        figattrib[figlabel] = {
                            'href': '{}'.format(figfile),
                            'onClick': ("window.open(this.href, \'{}\',"
                                        "\'width=400,height=200\',"
                                        "\'toolbar=1\'); return false;".
                                        format(cnumber))}
                    else:  # multi-image figure
                        htmlbodycontent = ""
                        for figfile in imgsrcs:
                            htmlbodycontent += (
                                "<img src=\"{}\" width=\"400\""
                                "height=\"200\">".format(figfile))
                        htmlstr = (
                            "\'<html><head></head><body>{}</body></html>\'".
                            format(htmlbodycontent))
                        figattrib[figlabel] = {
                            'onClick': ("return newWindow({}, 'Figure {}');".
                                        format(htmlstr, fignum)),
                            'href': 'javascript: void(0)'}
        # EVH: Build cross reference dictionaries for ToC refs
        toclist = []  # ['toclabel']
        tocdict = {}  # {'toclabel',['locstr','label text']}
        labeldict = {}  # {'labeltag':['loc. URL','chapnum.labelnum']}
        tocrefdict = {}  # {'tocref':[['locstr'],['parent name']]}
        labelcnt = {}  # {'labeltag':cnt}
        chapref = '0'
        for label in tree.xpath('.//label|//toclabel'):
            locstr = label.get('tmploc')
            if not locstr:
                continue
            if locstr.split('.')[-1] == '0':
                locstr = locstr[:-2]
                hlabel = True
            else:
                hlabel = False
            locref = mapdict[locstr][2]
            labelref = label.text
            if locref.split('.')[0] != chapref:
                chapref = locref.split('.')[0]
                labelcnt = {}  # Reset label count
            if hlabel:
                labeldict[labelref] = [mapdict[locstr][0], locref]
            else:
                labeltag = labelref.split(':')[0]
                if labeltag in labelcnt:
                    labelcnt[labeltag] += 1
                else:
                    labelcnt[labeltag] = 1
                if chapref == '0':
                    labelnum = '{}'.format(labelcnt[labeltag])
                else:
                    labelnum = '{}.{}'.format(chapref, labelcnt[labeltag])
                if ':' in labelref:
                    labeltag += ':' + labelnum
                labeldict[labelref] = [mapdict[locstr][0], labeltag]
            # Get label tail and parent text, and remove label
            labeltail = label.tail
            plabel = label.getparent()
            ptext = plabel.text
            if labeltail != ' ' and (labeltail is not None):
                if ptext == '\n' or (ptext is None):
                    ptext = labeltail
                else:
                    ptext = ptext[:-1] + labeltail  # remove ptext CR, add tail
            if label.tag == 'toclabel':
                toclist.append(labelref)
                tocdict[labelref] = [locstr, ptext]
                # Change URL to point to the ToC location
                labeldict[labelref][0] = ('../tocindex/#anchor{}'.
                                          format(labeldict[labelref][1].
                                                 upper().replace(r'.', 'p').
                                                 replace(':', '')))
            if plabel.tag == 'p':
                label = plabel
                plabel = plabel.getparent()
            plabel.text = ptext
            plabel.remove(label)
        for tocref in tree.findall('.//tocref'):
            tagref = tocref.text
            locstr = tocref.get('tmploc')
            paref = tocref.getparent()
            paref.text += tocref.tail
            paref.remove(tocref)
            while paref.tag not in ['html', 'problem', 'vertical']:
                paref = paref.getparent()
                pareftag = paref.tag
            # EVH: Prepend letter to identify content type
            if pareftag == 'vertical':
                parind = len(paref)+1
                for i, child in enumerate(paref):
                    if child.tag in ['html', 'problem']:
                        parind = min(parind, i)
                    if child.tag == 'problem':
                        pareftag = 'problem'
                paref = paref[parind]
            if pareftag == 'problem':
                parefname = 'P' + paref.get('display_name')
                oldtag = paref.get('measureable_outcomes')
                tagname = tagref
                if ':' in tagname:
                    tagname = tagname.split(':')[1]
                if oldtag is None:
                    newtag = tagname
                else:
                    newtag = oldtag + ',' + tagname
                paref.set('measureable_outcomes', newtag)
            else:
                parefname = 'H' + paref.get('display_name')
            if tagref in tocrefdict:
                tocrefdict[tagref][0].append(locstr)
                tocrefdict[tagref][1].append(parefname)
            else:
                tocrefdict[tagref] = [[locstr], [parefname]]
            taglist = paref.find(".//p[@id='taglist']")
            if taglist is None:
                taglist = etree.Element('p', id='taglist', tmploc=locstr,
                                        tags=tagref)
                paref.insert(0, taglist)
            else:
                taglist.set('tags', taglist.get('tags') + ',' + tagref)
        # EVH: Parse taglist to create ToC button links at the top of each vert
        for taglist in tree.findall(".//p[@id='taglist']"):
            locstr = taglist.get('tmploc')
            tags = taglist.get('tags').split(',')
            for tocref in tags:
                tocrefid = tocref
                if ':' in tocrefid:
                    tocrefid = tocrefid.split(':')[1]
                if tocref not in labeldict:
                    continue
                link = etree.SubElement(
                    taglist, 'button',
                    {'type': "button", 'border-radius': "2px",
                     'title': "{}:\n{}".format(labeldict[tocref][1].upper().
                                               replace(':', ''),
                                               tocdict[tocref][1]),
                     'style': "cursor:pointer", 'class': "mo_button",
                     'onClick': ("window.location.href='{}{}'".
                                 format('../' * (len(locstr.split('.')) - 1),
                                        labeldict[tocref][0]))})
                link.text = labeldict[tocref][1].upper().replace(':', '')
                link.set('id', tocrefid)
        tochead = ['h2', 'h3', 'h4']
        if len(toclist) != 0:
            # EVH: Start building tocindex.html
            toctree = etree.Element('html')
            toctree.append(etree.fromstring('<head></head>'))
            tocbody = etree.SubElement(toctree, 'body')
            tocbody.append(etree.Element('h1'))
            tocbody[0].text = 'Table of Contents'
        while len(toclist) != 0:
            hlabel = False
            toclabel = toclist.pop(0)
            tocloc = tocdict[toclabel][0]
            tocname = tocdict[toclabel][1]
            if tocloc.split('.')[-1] == '0':
                hlabel = True
                tocloc = tocloc[:-2]
            while tocloc in maplist:
                tocentry = maplist.pop(0)
                entryname = mapdict[tocentry][1]
                toclevel = len(tocentry.split('.'))
                if toclevel == 1:
                    if tocentry.split('.')[0] != '1':
                        tocbody.append(etree.Element('br'))
                    # Insert chapter titles if no toclabel exist
                    if not hlabel:
                        tocitem = etree.Element(
                            'a', {'href': ('../courseware/' +
                                           mapdict[tocentry][0])})
                        tocitem.append(etree.Element('h2'))
                        tocitem[0].text = entryname
                        tocbody.append(tocitem)
            if toclabel in tocrefdict:
                toctag = labeldict[toclabel][1].replace(':', '')
                tocbody.append(etree.Element(
                    'a', {'name': 'anchor{}'.format(toctag.upper().
                                                    replace('.', 'p'))}))
                toctable = etree.Element(
                    'table',
                    {'id': 'label',
                     'class': 'wikitable collapsible collapsed'})
                toctable.append(etree.Element('tbody'))
                tablecont = etree.SubElement(toctable[0], 'tr')
                tablecont = etree.SubElement(tablecont, 'th')
                tablecont.append(etree.Element(
                    'a',
                    {'id': 'ind{}l'.format(toctag.replace('.', 'p')),
                     'onclick': ("$('#ind{}').toggle();return false;".
                                 format(toctag.replace('.', 'p'))),
                     'name': 'ind{}l'.format(toctag.replace('.', 'p')),
                     'href': '#'}))
                if hlabel:
                    tablecont = etree.SubElement(
                        tablecont[0], tochead[toclevel - 1])
                    tablecont.text = entryname
                else:
                    tablecont[0].append(etree.Element(
                        'strong', {'itemprop': 'name'}))
                    tablecont[0][0].text = toctag.upper()
                    tablecont = etree.SubElement(
                        tablecont, 'span', {'itemprop': 'description'})

                    tablecont.text = tocname

                tablecont = etree.SubElement(
                    toctable[0], 'tr',
                    {'id': 'ind{}'.format(toctag.replace('.', 'p')),
                     'style': 'display:none'})
                tablecont = etree.SubElement(tablecont, 'td')
                tablecont.append(etree.Element('h4'))
                tablecont[0].text = 'Learn'
                tablecont.append(etree.Element(
                    'ul', {'class': '{}learn'.format(toclabel.split(':')[0].
                                                     upper())}))
                tablecont.append(etree.Element('h4'))
                tablecont[2].text = 'Assess'
                tablecont.append(etree.Element(
                    'ul', {'class': '{}assess'.format(toclabel.split(':')[0].
                                                      upper())}))
                tocrefs = tocrefdict.pop(toclabel)
                tocrefnames = tocrefs[1]
                tocrefs = tocrefs[0]
                for tocref in tocrefs:
                    tableli = etree.Element('li')
                    tableli.append(etree.Element(
                        'a', {'href': ('../courseware/' +
                                       mapdict[tocref][0]),
                              'itemprop': 'name'}))
                    tocrefname = tocrefnames.pop(0)
                    tableli[0].text = tocrefname[1:]
                    if tocrefname[0] == 'H':
                        tablecont[1].append(tableli)
                    else:
                        tablecont[3].append(tableli)
            else:
                toctable = etree.Element('a', {'href': ('../courseware/' +
                                                        mapdict[tocloc][0])})
                if hlabel:
                    tablecont = etree.SubElement(
                        toctable, tochead[toclevel - 1])
                    tablecont.text = entryname
                else:
                    toctable.append(etree.Element(
                        'strong', {'itemprop': 'name'}))
                    toctable[0].text = (labeldict[toclabel][1].upper().
                                        replace(':', ''))
                    tablecont = etree.SubElement(
                        toctable, 'span', {'itemprop': 'description'})
                    tablecont.text = tocname
            tocbody.append(toctable)
        if len(tocdict) != 0:
            print("Writing ToC index content...")
            if not os.path.exists(self.output_dir):
                os.mkdir(self.output_dir)
            if not os.path.exists(self.output_dir / 'tabs'):
                os.mkdir(self.output_dir / 'tabs')
            tocf = open(self.output_dir / 'tabs' / 'tocindex.html', 'w')
            tocf.write(etree.tostring(
                toctree, method='html', pretty_print=True).decode())
            tocf.close()

        class MissingLabel(Exception):
            '''
            Exception raised when a referrence to a non-existent label is found
            '''

            def __init__(self, value):
                '''
                Add a new value to the Exception call
                Arg: value (str)
                '''
                self.value = value

            def __str__(self):
                '''
                Return the value of the Exception as a string
                '''
                return repr(self.value)

        # EVH: Check for unused tocrefs
        for tocref in tocrefdict:
            try:
                raise MissingLabel(tocref)
            except MissingLabel as referr:
                print(('WARNING: There is a reference to non-existent '
                       'ToC label: {}'.format(str(referr))))

        # EVH: Handle equation refs. Search for labels and build dictionaries
        eqndict = {}  # {'eqnlabel':'eqnnum'}
        eqnattrib = {}  # {'eqnlabel':{'attrib':'value'}}
        chapref = '0'
        eqncnt = 0
        for table in tree.xpath('.//table[@class="equation"]|'
                                './/table[@class="eqnarray"]'):
            if 'tmploc' in table.attrib:
                locstr = table.attrib.pop('tmploc')
            if not locstr:
                continue
            locref = mapdict[locstr][2]
            if chapref != locref.split('.')[0]:
                chapref = locref.split('.')[0]
                eqncnt = 0
            for tr in table.findall('.//tr'):  # Max one label per table row
                eqnnumcell = None
                eqnlabel = []
                for td in tr.findall('.//td'):
                    if td.get('class') == 'eqnnum' and td.text != '\u00A0':
                        eqnnumcell = td
                        # EVH: Use plasTeX output to handle equation numbering
                        eqncnt += 1
                        if chapref == '0':
                            eqnnum = '{}'.format(eqncnt)
                        else:
                            eqnnum = '{}.{}'.format(chapref, eqncnt)
                        tr.remove(eqnnumcell)
                        eqnnumcell = etree.SubElement(
                            tr, "td", attrib=eqnnumcell.attrib)
                        eqnnumcell.text = '({})'.format(eqnnum)
                        eqnnumsty = eqnnumcell.get('style')
                        eqnnumsty = re.sub('text-align:[a-zA-Z]+;', '', eqnnumsty)
                        eqnnumsty += ';text-align:right'
                        eqnnumcell.set('style', eqnnumsty)
                    elif td.text is not None:
                        eqncontent = td.text
                        if re.search(r'\\label\{(.*?)\}',
                                     eqncontent, re.S) is not None:
                            eqnlabel = re.findall(r'\\label\{(.*?)\}',
                                                  eqncontent, re.S)
                            eqncontent = re.sub(r'\\label{.*?}', r'',
                                                eqncontent)
                            td.text = eqncontent
                if len(eqnlabel) != 0:
                    # NOTE: EVH 2015-07-24 find a better way to handle labels
                    # to unnumbered equations
                    if eqnnumcell is None:
                        eqnnum = 'NaN'
                    eqnlabel = eqnlabel[0]
                    eqnlabel = eqnlabel.replace(' ', '')
                    eqndict[eqnlabel] = '{}'.format(eqnnum)
                    # EVH: Set id for linking if pop-up flag is False
                    tr.set('id', 'eqn{}'.format(eqnnum.replace('.', 'p')))
                    eqnattrib[eqnlabel] = {
                        'href': '{}#eqn{}'.format(mapdict[locstr][0],
                                                  eqnnum.replace('.', 'p')),
                        'onClick': 'location.reload()'}
                if self.popup_flag and len(eqnlabel) != 0:
                    eqnattrib[eqnlabel]['href'] = 'javascript: void(0)'
                    eqntablecontent = (etree.tostring(
                        tr, encoding="utf-8", method="html")).rstrip().decode()
                    eqntablecontent = ''.join(re.findall(
                        r'\[mathjax[a-z]*\](.*?)\[/mathjax[a-z]*\]',
                        eqntablecontent, re.S))
                    eqntablecontent = re.escape('$$' + eqntablecontent + '$$')
                    if re.search(r'\\boxed', eqntablecontent,
                                 re.S) is not None:
                        eqntablecontent = eqntablecontent.replace(
                            r'\boxed', '')
                    eqntablecontent = (
                        "<table width=\"100%%\" cellspacing=\"0\""
                        "cellpadding=\"7\" style=\"table-layout:auto;"
                        "border-style:hidden\"><tr><td style=\"width:80%%;"
                        "vertical-align:middle;text-align:center;"
                        "border-style:hidden\">{}</td><td style=\"width:20%%;"
                        "vertical-align:middle;text-align:left;"
                        "border-style:hidden\">({})</td></tr></table>".
                        format(eqntablecontent, eqnnum))
                    mathjax = (
                        "<script type=\"text/javascript\" src=\"https://edx-"
                        "static.s3.amazonaws.com/mathjax-MathJax-727332c/Math"
                        "Jax.js?config=TeX-MML-AM_HTMLorMML-full\"> </script>")
                    htmlstr = (
                        "\'<html><head>{}</head><body>{}</body></html>\'".
                        format(mathjax, eqntablecontent))
                    eqnattrib[eqnlabel]['onClick'] = (
                        "return newWindow({}, \'Equation {}\');".
                        format(htmlstr, eqnnum))

        # EVH: Build keymap dictionary for keywords specified by the \index
        # command
        keymap = {}  # {keyword: [[URL], [display_name]]}
        for indexref in tree.findall('.//index'):
            locstr = indexref.get('tmploc')
            keyref = indexref.text
            if keyref in keymap:
                keymap[keyref][0].append(mapdict[locstr][0])
                keymap[keyref][1].append(mapdict[locstr][1])
            else:
                keymap[keyref] = [[mapdict[locstr][0]],
                                  [mapdict[locstr][1]]]
            p = indexref.getparent()
            p.remove(indexref)

        # EVH: Find and replace references everywhere with ref number and link
        for aref in tree.findall('.//ref'):
            reflabel = aref.text
            if not 'tmploc' in aref.attrib:
                continue
            locstr = aref.attrib.pop('tmploc')
            if self.popup_flag:
                relurl = ''
            else:
                relurl = '../' * (len(locstr.split('.')) - 1)
            if reflabel in figdict:
                aref.tag = 'a'
                aref.text = figdict[reflabel]
                for attrib in figattrib[reflabel]:
                    aref.set(attrib, figattrib[reflabel][attrib])
                rawref = aref.get('href')
                aref.set('href', (relurl + rawref))
            elif reflabel in labeldict:
                aref.tag = 'a'
                aref.text = labeldict[reflabel][1].replace(':', ' ')
                aref.set('href', ('../' * (len(locstr.split('.')) - 1) +
                                  labeldict[reflabel][0]))
                aref.set('target', "_blank")
            elif reflabel in eqndict:
                aref.tag = 'a'
                aref.text = eqndict[reflabel]
                for attrib in eqnattrib[reflabel]:
                    aref.set(attrib, eqnattrib[reflabel][attrib])
                rawref = aref.get('href')
                aref.set('href', (relurl + rawref))
            else:
                try:
                    raise MissingLabel(aref.text)
                except MissingLabel as referr:
                    print(('WARNING: There is a reference to non-existent '
                           'label: {}'.format(str(referr))))

        if len(keymap) != 0:
            if not os.path.exists(self.output_dir):
                os.mkdir(self.output_dir)
            if not os.path.exists(self.output_dir / 'static'):
                os.mkdir(self.output_dir / 'static')
            print("Writing key_map.json to static/ ...")
            kwjson = open(self.output_dir / 'static' / 'key_map.json', 'w')
            kwjson.write(json.dumps(keymap, default=lambda o: o.__dict__))
            kwjson.close()

    def process_askta(self, tree):
        '''
        add "Ask TA!" links
        arguments are taken as space delimited settings

        if "settings" set, then:
           - save key,value for next uses of edXaskta
           - do not display a link

        examples:

        % sets settings, does not display link
        \edXaskta{settings=1 label="Ask TA!" url_base="htps://edx.org/mycourse" to:"me@example.edu" cc:"ta@example.edu"}

        % displays Email TA link
        \edXaskta{label="Email TA" subject:"help"}
        '''

        special_attribs = ['url_base', 'cnt', 'label']

        if not hasattr(self, 'askta_data'):
            subject = "Question about {name}"
            body = "This is a question about the problem at COURSE_URL/{url_name}\n\n"
            self.askta_data = {'cnt': 0, 'label': 'Ask TA!', 'to': '', 'cc': '', 'subject': subject,
                               'body': body,
                               'url_base': 'https://edx.org',
                               }

        for askta in tree.findall('.//askta'):
            text = askta.text
            args = {}
            if text:
                argset = split_args_with_quoted_strings(text)
                try:
                    args = dict([x.split('=', 1) for x in argset])
                    for arg in args:
                        args[arg] = self.stripquotes(args[arg], checkinternal=True)
                except Exception as err:
                    print("Error %s" % err)
                    print("Failed in parsing args to edXaskta = %s" % text)
                    raise
                if 'settings' in args:
                    args.pop('settings')
                    self.askta_data.update(args)
                    print("askTA settings updated: %s" % self.askta_data)
                    # remove this element from xml tree
                    # self.remove_parent_p(askta)
                    p = askta.getparent()
                    p.remove(askta)
                    if p.tag=='p' and not p.text.strip():	# remove extra <p> if present
                        pp = p.getparent()
                        pp.remove(p)
                    continue

            # generate button link, something like this:
            #   <input style="float:right" class="check Check" type="button" value="Ask TA!" onclick="SendMail();"/>
            # <script type="text/javascript">
            # var amp = String.fromCharCode(38);
            # function SendMail() {
            #          var link = "mailto:me@example.com"
            #             + "?cc=myCCaddress@example.com"
            #             + amp + "subject=" + escape("This is my subject")
            #             + amp + "body=";
            #          window.open(link,'AskTA', "height=500,width=700");
            # }
            # </script>

            data = {}
            data.update(self.askta_data)
            data.update(args)

            display_name = ''
            url_name = ''
            for parent in askta.xpath('ancestor::*')[::-1]:
                display_name = parent.get('display_name', '')
                if display_name:
                    url_name = parent.get('url_name')
                    break

            data['subject'] = data['subject'].format(name=display_name)
            data['body'] = data['body'].format(url_name=url_name, **data)

            self.askta_data['cnt'] += 1
            smfn = 'SendMail_%d' % self.askta_data['cnt']

            askta.tag = 'span'
            askta.text = ''

            atin = etree.SubElement(askta, 'input')
            atin.set('style', 'float:right')
            atin.set('class', 'check Check')
            atin.set('value', data['label'])
            atin.set('type', 'button')
            atin.set('onclick', '%s();' % smfn)

            for attrib in special_attribs:
                data.pop(attrib)

            atlid = 'aturl_%s' % self.askta_data['cnt']
            atlink = etree.SubElement(askta, 'a')
            atlink.set('style', 'display:none')
            atlink.set('href', '/course/jump_to_id')
            atlink.set('id', atlid)

            mailto = 'mailto:%s' % data['to']
            data.pop('to')
            body = data.pop('body')
            mailto += '?' + urllib.parse.urlencode(data)
            mailto += '&' + urllib.parse.urlencode({'body': body})

            jscode = ('\nfunction %s() {\n'
                      '    var cu = encodeURI(window.location.origin + $("#%s").attr("href"));\n'
                      '    var link = "%s";\n'
                      '    link = link.replace("COURSE_URL", cu);\n'
                      '    link = link.replace(/&/g, String.fromCharCode(38));\n'
                      '    console.log(link);\n'
                      '    Logger.log("askta",{link:link});\n'
                      '    window.open(link, "AskTA", "height=500,width=700"); \n'
                      '}') % (smfn, atlid, mailto)

            script = etree.SubElement(askta, 'script')
            script.set('type', 'text/javascript')
            script.text = jscode

    @staticmethod
    def stripquotes(x, checkinternal=False):
        if x.startswith('"') and x.endswith('"'):
            if checkinternal and '"' in x[1:-1]:
                return x
            return x[1:-1]
        if x.startswith("'") and x.endswith("'"):
            return x[1:-1]
        return x

    def process_add_timestamp(self, tree):
        '''
        Add timestamps at the bottom of every HTML page
        '''
        if not self.add_timestamp:
            return
        ts = datetime.datetime.now().strftime("%A %B %d, %Y; %I:%M:%S %p")
        stamp = "This page was last updated on %s" % ts
        if self.timestamp_revision:
            stamp += " (revision %s)" % self.timestamp_revision
        nadd = 0
        nskip = 0
        for html in tree.findall('.//html'):
            if(len(html) < self.timestamp_threshold):
                nskip += 1
                continue
            stamp_xml = etree.fromstring('<span><br/><span style="color:gray;font-size:10pt"><center>%s</center></span></span>' % stamp)
            html.append(stamp_xml)
            nadd += 1
        print(("Added timestamp to %d html pages (skipped %s)" % (nadd, nskip)))
        print(("    timestamp = '%s'" % stamp))

    def process_edxcite(self, tree):
        '''
        Add citation link visible on mouse hoover.
        '''
        if not hasattr(self, 'edxcitenum'):
            self.edxcitenum = 0
        for edxcite in tree.findall('.//edxcite'):
            self.edxcitenum += 1
            ref = edxcite.get('ref', None)
            if ref is None or not ref:
                ref = '[%d]' % self.edxcitenum
            text = edxcite.text
            exc = etree.Element('a')
            edxcite.addnext(exc)
            sup = etree.SubElement(exc, 'sup')
            sup.text = ref
            exc.set('href', '#')
            exc.set('title', text)
            # print "  --> %s" % etree.tostring(exc)
            p = edxcite.getparent()
            p.remove(edxcite)

    @staticmethod
    def remove_parent_p(xml):
        '''
        If xml is inside an otherwise empty <p>, then push it up and remove the <p>
        '''
        p = xml.getparent()
        todrop = xml
        where2add = xml
        if p.tag == 'p' and not p.text.strip() and len(p) == 1:	 # if in empty <p> then remove that <p>
            todrop = p
            where2add = p
            p = p.getparent()

        # move from xml to parent: text, children, and tail
        if xml.text:
            if xml.getprevious() is not None:
                if xml.getprevious().tail:
                    xml.getprevious().tail += xml.text
                else:
                    xml.getprevious().tail = xml.text
            else:
                if p.text:
                    p.text += xml.text
                else:
                    p.text = xml.text
        for child in xml:
            where2add.addprevious(child)
        if xml.tail:
            if 'child' in locals():
                if child.tail:
                    child.tail += xml.tail
                else:
                    child.tail = xml.tail
            else:
                if p.text:
                    p.text += xml.tail
                else:
                    p.text = xml.tail
        p.remove(todrop)

    def process_edxxml(self, tree):
        '''
        move content of edXxml into body
        If edXxml is within a <p> then drop the <p>.  This allows edXxml to be used for discussion and video.
        '''
        for edxxml in tree.findall('.//edxxml'):
            self.remove_parent_p(edxxml)

    def process_video(self, tree):
        '''
        If the "youtubeid" begins with "http" then make the video an html5 video.
        '''
        for video in tree.findall('.//video'):
            ytid = video.get('youtube_id_1_0')
            if ytid.startswith('http'):
                video.set('html5_sources', '["%s"]' % ytid)
                video.set('youtube_id_1_0', '')
                vsource = etree.Element('source')
                vsource.set('src', ytid)
                video.append(vsource)

    def process_lti(self, tree):
        '''
        For LTI elements, any custom_* attributes should be moved into a special single
        "custom_parameters" attribute.
        '''
        for lti in tree.findall('.//lti'):
            cplist = []
            for key, val in list(lti.attrib.items()):
                if key.startswith('custom_'):
                    cplist.append("%s=%s" % (key[7:], val))  # strip "custom_" prefix
                    lti.attrib.pop(key)
            if cplist:
                lti.set('custom_parameters', '[%s]' % ', '.join(['"' + x + '"' for x in cplist]))
            if self.verbose:
                print("    lti %s, cp=%s" % (lti, lti.get('custom_parameters')))

    def process_split_test(self, tree):
        '''
        For split_test elements, take all group_id_to_child<#>=gid attributes and combine them into a dict of the form { '<#>': gid, ...}
        and set JSONified string of that dict as the group_id_to_child attribute value.
        '''
        for st in tree.findall('.//split_test'):
            gilist = {}
            for key, val in list(st.attrib.items()):
                if key.startswith('group_id_to_child'):
                    gk = key.split('group_id_to_child')[-1]
                    gilist[gk] = val
                    st.attrib.pop(key)
            if gilist:
                st.set('group_id_to_child', json.dumps(gilist))

            # remove parent <p> if it exists
            parent = st.getparent()
            pp = parent.getparent()
            if parent.tag == 'p' and not parent.text.strip() and pp is not None:
                parent.addprevious(st)
                pp.remove(parent)

            if self.verbose:
                print("    split_test %s, group_id_to_child=%s" % (st, st.get('group_id_to_child')))

    def process_marginote(self, tree):
        '''
        \marginote[options]{note}{anchor text}
        --> <marginote options><desc>note</desc> anchor text</marginote>
        '''
        for mn in tree.findall('.//marginote'):
            mn.tag = "span"
            mn.set('class', "marginote")
            desc = mn.find(".//desc")
            if desc is None:
                raise Exception("Oops, missing note text in marginote=%s" % etree.tostring(mn))
            desc.tag = "span"
            desc.set('class', 'marginote_desc')
            desc.set('style', "display:none")
            if self.verbose:
                print(("    marginote %s" % (mn)))

            # insert <script> tag for marginote javascript, if not already in this container
            par = self.find_container_root(mn, "marginote")
            if not par.findall('.//script[@src="/static/marginotes.js"]'):
                par.append(etree.Element("script", 
                                        {'type': 'text/javascript',
                                         'src': '/static/marginotes.js'}))
                self.copy_to_static("marginotes.js", 'marginotes JavaScript')

    def find_container_root(self, elem, name="current_element"):
        '''
        Find containing html or parent container, for element elem
        '''
        par = elem.getparent()
        parent_tags = [elem.tag, par.tag]
        while (par.tag != 'html') and (par.tag != 'problem'):
            oldpar = par
            par = par.getparent()
            if par is not None:
                parent_tags.append(par.tag)
            if par is None:
                print(("Error finding root for %s" % etree.tostring(elem)))
                print(("parent tags = %s" % parent_tags))
                raise Exception("Strange - %s is in a %s environment?" % (name, oldpar.tag))
            if par.tag == 'vertical' or par.tag == 'sequential':
                raise Exception("Must use %s inside html or problem element" % name)
        return par

    def copy_to_static(self, resource_fn, description="resource file"):
        '''
        Copy named resource file to the course's static files directory.
        Ensure that the static files directory exists.
        '''
        staticdir = self.output_dir / 'static'
        if not os.path.exists(staticdir):
            if not os.path.exists(self.output_dir):
                os.mkdir(self.output_dir)
            os.mkdir(staticdir)
        if not os.path.exists(staticdir / resource_fn):
            l2ejs = pkg_resources.resource_filename(__name__, resource_fn)
            cmd = 'cp {} {}/'.format(l2ejs, staticdir)
            print('----> Copying {}: {}'.format(description, cmd))
            sys.stdout.flush()
            os.system(cmd)

    def process_showhide(self, tree):
        for showhide in tree.findall('.//edxshowhide'):
            desc = showhide.get('description', '')
            oneup = showhide.getparent()
            newsh = etree.SubElement(oneup, 'div', {'class': 'hideshowbox'})
            sub1 = etree.SubElement(newsh, 'h4',
                                    {'onclick': 'hideshow(this);',
                                     'style': 'margin: 0px'})
            sub1.text = desc
            etree.SubElement(sub1, 'span',
                             {'class': 'icon-caret-down toggleimage'})
            newsh.append(showhide)
            showhide.tag = 'div'  # change edxshowhide tag
            showhide.attrib.pop('description')  # remove description
            showhide.set('class', 'hideshowcontent')
            sub2 = etree.SubElement(newsh, 'p',
                                    {'class': 'hideshowbottom',
                                     'onclick': 'hideshow(this);',
                                     'style': 'margin: 0px'})
            subsub2 = etree.SubElement(sub2, 'a',
                                       {'href': 'javascript: {return false;}'})
            subsub2.text = 'Show'
            par = self.find_container_root(newsh, "showhide")

            scriptforsh = etree.Element('SCRIPT',
                                        {'type': 'text/javascript',
                                         'src': '/static/latex2edx.js'})
            styleforsh = etree.Element('LINK',
                                       {'type': 'text/css',
                                        'rel': 'stylesheet',
                                        'href': '/static/latex2edx.css'})
            if len(par.findall('.//SCRIPT[@src="/static/latex2edx.js"]')) == 0:
                par.append(scriptforsh)
                par.append(styleforsh)
                self.copy_to_static("latex2edx.js", 'showhide JavaScript')
                self.copy_to_static("latex2edx.css", 'showhide CSS')

    def process_include(self, tree, do_python=False):
        '''
        Include XML or python file.

        For python files, wrap inside <script><![CDATA[ ... ]]></script>
        '''
        tag = './/edxinclude'
        cmd = 'edXinclude'
        if do_python:
            tag += 'py'
            cmd += "py"
        for include in tree.findall(tag):
            incfn = include.text
            linenum = include.get('linenum', '<unavailable>')
            texfn = include.get('filename', '<unavailable>')
            if incfn is None:
                print("Error: %s must specify file to include!" % cmd)
                raise Exception(self.standard_error_msg(include))
            incfn = incfn.strip()
            if not os.path.exists(incfn):
                print("Error: include file %s does not exist!" % incfn)
                raise Exception(self.standard_error_msg(include))
            try:
                incdata = open(incfn).read()
            except Exception as err:
                print("Error %s: cannot open include file %s to read" % (err, incfn))
                raise Exception(self.standard_error_msg(include))

            # if python script, then check its syntax
            if do_python:
                try:
                    py_compile.compile(incfn, doraise=True)
                except Exception as err:
                    print("Error in python script %s! Err=%s" % (incfn, err))
                    print("Aborting!")
                    raise Exception(self.standard_error_msg(include))

            try:
                if do_python:
                    incxml = etree.fromstring('<script><![CDATA[\n%s\n]]></script>' % incdata)
                else:
                    incxml = etree.fromstring(incdata)
            except Exception as err:
                print("Error %s parsing XML for include file %s" % (err, incfn))
                print("See tex file %s line %s" % (texfn, linenum))
                raise Exception(self.standard_error_msg(include))

        # remove parent <p> if it exists
            parent = include.getparent()
            pp = parent.getparent()
            if parent.tag == 'p' and not parent.text.strip() and pp is not None:
                parent.addprevious(include)
                pp.remove(parent)

            print("--> including file %s at line %s" % (incfn, linenum))
            if incxml.tag == 'html' and len(incxml) > 0:  # strip out outer <html> container
                for k in incxml:
                    include.addprevious(k)
            else:
                include.addprevious(incxml)
            p = include.getparent()
            if p is not None:
                p.remove(include)

    def process_includepy(self, tree):
        '''
        Handle \edXincludepy{script_file.py} inclusion of python scripts.
        '''
        self.process_include(tree, do_python=True)

    @staticmethod
    def get_filename_and_linenum(elem):
        linenum = elem.get('linenum', '<unavailable>')
        texfn = elem.get('tex_filename', elem.get('filename', '<unavailable>'))
        return "file %s line %s" % (texfn, linenum)

    def standard_error_msg(self, elem):
        msg = "Error processing element %s in %s" % (elem.tag, self.get_filename_and_linenum(elem))
        return msg

    def process_dndtex(self, tree):
        '''
        Handle \edXdndtex{dnd_file.tex} inclusion of latex2dnd tex inputs.
        The file may also be a dnd_file.dndspec
        '''
        tag = './/edxdndtex'
        for dndxml in tree.findall(tag):
            dndfn = dndxml.text
            linenum = dndxml.get('linenum', '<unavailable>')
            texfn = dndxml.get('filename', '<unavailable>')
            if dndfn is None:
                print("Error: %s must specify dnd tex filename!" % tag)  # EVH changed 'cmd' to 'tag'
                print("See tex file %s line %s" % (texfn, linenum))
                raise
            dndfn = dndfn.strip()
            if not (dndfn.endswith('.tex') or dndfn.endswith('.dndspec')):
                print("Error: dnd file %s should be a .tex or a .dndspec file!" % dndfn)
                print("See tex file %s line %s" % (texfn, linenum))
                raise
            if not os.path.exists(dndfn):
                print("Error: dnd tex file %s does not exist!" % dndfn)
                print("See tex file %s line %s" % (texfn, linenum))
                raise
            try:
                dndsrc = open(dndfn).read()
            except Exception as err:
                print("Error %s: cannot open dnd tex / dndpec file %s to read" % (err, dndfn))
                print("See tex file %s line %s" % (texfn, linenum))
                raise

            # Use latex2dnd to compile dnd tex into edX XML.
            #
            # For dndfile.tex, at least two files must be produced: dndfile_dnd.xml and
            # dndfile_dnd.png
            #
            # we copy all the *.png files to static/images/<dndfile>/
            #
            # run latex2dnd only when the dndfile_dnd.xml file is older than dndfile.tex

            fnb = os.path.basename(dndfn)
            fnpre = fnb.rsplit('.', 1)[0]
            fndir = path(os.path.dirname(dndfn))
            xmlfn = fndir / (fnpre + '_dnd.xml')

            run_latex2dnd = False
            if not os.path.exists(xmlfn):
                run_latex2dnd = True
            if not run_latex2dnd:
                dndmt = os.path.getmtime(dndfn)
                xmlmt = os.path.getmtime(xmlfn)
                if dndmt > xmlmt:
                    run_latex2dnd = True
            if run_latex2dnd:
                options = ''
                if dndxml.get('can_reuse', 'False').lower().strip() != 'false':
                    options += '-C'
                cmd = 'cd "%s"; latex2dnd --cleanup -r %s -v %s %s' % (fndir, dndxml.get('resolution', 210), options, fnb)
                print("--> Running %s" % cmd)
                sys.stdout.flush()
                status = os.system(cmd)
                if status:
                    print("Oops - latex2dnd apparently failed - aborting!")
                    raise Exception("Oops - latex2dnd apparently failed - aborting!")
                imdir = self.output_dir / ('static/images/%s' % fnpre)
                os.system('mkdir -p %s' % imdir)
                cmd = "cp %s/%s*.png %s/" % (fndir, fnpre, imdir)
                print("----> Copying dnd images: %s" % cmd)
                sys.stdout.flush()
                status = os.system(cmd)
                if status:
                    print("Oops - copying images from latex2dnd apparently failed - aborting!")
                    raise Exception("Oops - latex2dnd apparently failed - aborting!")
            else:
                print("--> latex2dnd XML file %s is up to date: %s" % (xmlfn, fnpre))

            # change dndtex tag to become include
            # change filename to become dndfile_dnd.xml
            # this will trigger an include of that XML in process_include, which happens after this filter

            dndxml.tag = 'edxinclude'
            dndxml.text = xmlfn

    def process_general_hint_system(self, tree):
        '''
        Include general_hint_system.py script for problems which have hints specified.
        '''
        mydir = os.path.dirname(__file__)
        libpath = path(os.path.abspath(mydir + '/python_lib'))
        ghsfn = libpath / 'general_hint_system.py'

        # find all instances of <edx_general_hint_system />,
        # but at most one per problem

        for problem in tree.findall('.//problem'):
            isdone = False
            for eghs in problem.findall('.//edx_general_hint_system'):
                incxml = etree.fromstring('<script><![CDATA[\n%s\n]]></script>' % open(ghsfn).read())
                if not isdone:
                    eghs.addprevious(incxml)
                    # print "  added eghs to problem %s" % problem.get('url_name')
                    isdone = True
                p = eghs.getparent()
                p.remove(eghs)

    def check_all_python_scripts(self, tree):
        '''
        Run syntax check on all python scripts
        '''
        for script in tree.findall('.//script[@type="text/python"]'):
            pyfile = tempfile.NamedTemporaryFile(mode='w', delete=False)
            if script.text is None:
                print("Warning: empty script!")
                print("Script location: %s" % etree.tostring(script))
                continue
            try:
                pyfile.write(script.text)
            except Exception as err:
                print("Error checking python script %s" % script.text)
                print(str(err))
                print("Script location: %s" % etree.tostring(script))
                continue
            pyfile.close()
            try:
                py_compile.compile(pyfile.name, doraise=True)
            except Exception as err:
                print("Error in python script %s! Err=%s" % (pyfile.name, err))
                print("Script location: %s" % etree.tostring(script))
                print("Aborting!")
                raise Exception(self.standard_error_msg(script))
            os.unlink(pyfile.name)

    def generate_course_unit_tests(self, xml):
        '''
        Generate course unit tests for all (suitable) answer boxes.
        The unit tests are stored as a YAML file, and may be used
        to test an edX course (on an openedx site) using the edxcut package.

        We construct the unit test set by going through all responses elements
        in the XML, and retrieving their corresponding AnswerBox objects, which
        have unit test response & expectation specifications.

        The actual unit test YAML file is generated using CourseUnitTestSet.
        '''
        responsetags = ['customresponse', 'optionresponse', 'multiplechoiceresponse', 
                        'choiceresponse', 'numericalresponse', 'formularesponse',
                        'stringresponse', 'symbolicresponse']
        cutset = CourseUnitTestSet()
        for problem in xml.findall('.//problem'):
            dn = problem.get('display_name')
            un = problem.get('url_name')
            # need to know the order of the responses, if there are multiple aboxes in a problem.
            # this is because they are submitted all together, and the edx platform uses a 
            # sequential index to number the input string IDs.
            #
            # Thus, we walk the tree, and keep orer intact

            response_elements = []
            def walk(xml):
                if xml.tag in responsetags:
                    response_elements.append(xml)
                else:
                    for elem in xml:
                        walk(elem)
            walk(problem)

            response_tests = []

            for response in response_elements:
                xmlstr = etree.tostring(response).strip().decode()
                abox = self.p2x.renderer.answer_box_objects.get(xmlstr, None)
                if not abox:
                    if self.verbose:
                        print("[latex2edx] generate_course_unit_tests %s: failed to find abox for response '%s'" % (un, xmlstr))
                    continue
                if self.verbose:
                    print("[latex2edx] generate_course_unit_tests %s: found abox %s" % (un, abox.aboxstr))
                
                # turn abox test list (of dicts) into list of AnswerBoxUnitTest objects
                abox_test_set = []
                count = 0
                for test in abox.tests:
                    count += 1
                    test['url_name'] = un
                    # print "test_spec=%s" % test
                    abut = AnswerBoxUnitTest(test_spec=test, test_name="%s/test_%d" % (dn, count))
                    abox_test_set.append(abut)

                response_tests.append(abox_test_set)

            # now construct the actual test cases, combining all tests for all aboxes in this problem
            all_combined_tests = []
            def make_test(all_tests, the_test=None):
                if len(all_tests)>0:
                    this_test_set = all_tests[0]
                    for a_test in this_test_set:
                        if not the_test:
                            make_test(all_tests[1:], a_test)
                        else:
                            make_test(all_tests[1:], the_test + a_test)
                else:
                    if the_test:
                        all_combined_tests.append(the_test)

            try:
                make_test(response_tests)
            except Exception as err:
                print("[latex2edx] Failed to generate course unit tests for problem %s, err=%s" % (un, str(err)))
                continue
            if self.verbose:
                print("[latex2edx] generate_course_unit_tests adding %d tests for problem %s" % (len(all_combined_tests), un))

            count = 0
            for test in all_combined_tests:	# rename tests, since counts may have changed
                count += 1
                test.name = "(%s) %s/test_%d" % (dn, un, count)
                
            cutset.add_tests(all_combined_tests)
        cutset.output_to_file(self.output_cutset)
        print("[latex2edx] %s course unit tests output to %s" % (len(cutset.tests), self.output_cutset))

    def add_url_names(self, xml):
        '''
        Generate unique url_name database keys for all XML descriptor tags, for
        which the user did not provide one.  Do this by recursively walking the
        xml tree.
        '''
        # print "add_url_names: %s" % xml.tag
        if xml.tag in self.DescriptorTags:
            if not xml.tag == 'course':
                dn = xml.get('display_name', '')
                if not dn:
                    dn = xml.getparent().get('display_name', '') + '_' + xml.tag
                new_un = self.make_url_name(xml.get('url_name', dn), xml.tag)
                if 'url_name' in list(xml.keys()) and not new_un == xml.get('url_name'):
                    print("Warning: url_name %s changed to %s" % (xml.get('url_name'), new_un))
                xml.set('url_name', new_un)
        if xml.tag not in ['problem', 'html']:
            for child in xml:
                self.add_url_names(child)

    def make_url_name(self, s, tag=''):
        '''
        Turn string s into a valid url_name.
        Use tag if provided.
        '''
        map = {'"\':<>': '',
               ',().;=+ ': '_',
               '&': 'and',
               '[': 'LB_',
               ']': '_RB',
               '?#* ': '_',
               '\u2013': '-',
               '\u2014': '-',
               }
        if not self.allow_dirs:
            map['/'] = '_'
        if not s:
            s = tag
        for m, v in list(map.items()):
            for ch in m:
                s = s.replace(ch, v)
        if self.allow_dirs:
            # Have to do this after the rest of the mapping, as we don't want
            # ': to turn into nothing (ordering in dictionary is not guaranteed)
            s = s.replace('/', ':')
        if s in self.URLNAMES and not s.endswith(tag):
            s = '%s_%s' % (tag, s)
        while s in self.URLNAMES:
            s += 'x'
        self.URLNAMES.append(s)
        return s

    @staticmethod
    def do_attrib_string(elem):
        '''
        parse attribute strings, and add to xml elements.
        attribute strings are space delimited, and optional for elements
        like chapter, sequential, vertical, text
        '''
        attrib_string = elem.get('attrib_string', '')
        if attrib_string:
            attrib_list = split_args_with_quoted_strings(attrib_string)
            if len(attrib_list) == 1 & len(attrib_list[0].split('=')) == 1:  # a single number n is interpreted as weight="n"
                elem.set('weight', attrib_list[0])
            else:  # the normal case, can remove backwards compatibility later if desired
                for s in attrib_list:
                    attrib_and_val = s.split('=')
                    if len(attrib_and_val) != 2:
                        print("ERROR! the attribute list '%s' for element %s is not properly formatted" % (attrib_string, elem.tag))
                        # print "attrib_and_val=%s" % attrib_and_val
                        print(etree.tostring(elem))
                        sys.exit(-1)
                    elem.set(attrib_and_val[0], attrib_and_val[1].strip("\""))  # remove extra quotes
        if 'attrib_string' in list(elem.keys()):
            elem.attrib.pop('attrib_string')  # remove attrib_string

    def fix_attrib_string(self, xml):
        '''
        Convert attrib_string in <problem>, <chapter>, etc. to attributes, intelligently.
        '''
        TAGS = ['problem', 'chapter', 'sequential', 'vertical', 'course', 'html', 'video', 'discussion', 'edxdndtex',
                'conditional', 'lti', 'split_test']
        for tag in TAGS:
            for elem in xml.findall('.//%s' % tag):
                self.do_attrib_string(elem)

    def process_custom_html(self, tree):
        '''
        Handle \begin{html}{tag}[attribs] ... \end{html}
        '''
        cnt = 0
        for ch in tree.findall(".//customhtml"):
            tag = ch.get("tag")
            if not tag:
                raise Exception("Oops, empty tag specified in custom html %s" % etree.tostring(ch))
            ch.tag = tag
            ch.attrib.pop("tag")
            self.do_attrib_string(ch)
            cnt += 1
        print(("Processed %s custom HTML stanzas" % cnt))

    def fix_xhtml_descriptor_in_p(self, xml):
        '''
        Sometimes have <sequential><p><problem>...</problem></p></sequential>
        Have to remove contaiing <p>
        This happens for problem, chapter, sequential, html, any DescriptorTag
        '''
        for tag in self.DescriptorTags:
            for elem in xml.findall('.//%s' % tag):
                parent = elem.getparent()
                if parent.tag == 'p':
                    for pcont in parent:
                        parent.addprevious(pcont)  # move each element in <p> up before <p>
                    parent.getparent().remove(parent)  # remove the <p>


def CommandLine():
    import pkg_resources  # part of setuptools
    version = pkg_resources.require("latex2edx")[0].version
    parser = optparse.OptionParser(usage="usage: %prog [options] filename.tex",
                                   version="%prog version " + version)
    parser.add_option('-v', '--verbose',
                      dest='verbose',
                      default=False, action='store_true',
                      help='verbose error messages')
    parser.add_option("-o", "--output-xbundle",
                      action="store",
                      dest="output_fn",
                      default="",
                      help="Filename for output xbundle file",)
    parser.add_option("-d", "--output-directory",
                      action="store",
                      dest="output_dir",
                      default="course",
                      help="Directory name for output course XML files",)
    parser.add_option("-c", "--config-file",
                      action="store",
                      dest="config_file",
                      default="latex2edx_config",
                      help="configuration file to load",)
    parser.add_option("-m", "--merge-chapters",
                      action="store_true",
                      dest="merge",
                      default=False,
                      help="merge chapters into existing course directory",)
    parser.add_option("-P", "--update-policy-file",
                      action="store_true",
                      dest="update_policy",
                      default=False,
                      help="update policy.json from settings in latex file",)
    parser.add_option("--suppress-policy-settings",
                      action="store_true",
                      dest="suppress_policy",
                      default=False,
                      help="suppress policy settings from XML files",)
    parser.add_option("--suppress-verticals",
                      action="store_true",
                      dest="suppress_verticals",
                      default=False,
                      help="do not automatically add extra verticals needed for Studio compatibility",)
    parser.add_option("-S", "--section-only",
                      action="store_true",
                      dest="section_only",
                      default=False,
                      help="export only edXsections (sequentials) -- no course or chapters",)
    parser.add_option("-x", "--xml-only",
                      action="store_true",
                      dest="xml_only",
                      default=False,
                      help="export only xbundle xml file -- no separate course content",)
    parser.add_option("--units-only",
                      action="store_true",
                      dest="units_only",
                      default=False,
                      help="export only units, including problem, html -- no course, chapter, section",)
    parser.add_option("--timestamp",
                      action="store_true",
                      default=False,
                      help="add timestamps at the bottom of each HTML page",)
    parser.add_option("--timestamp-revision",
                      action="store",
                      default="",
                      help="additional revision number to add to the timestamp",)
    parser.add_option("--timestamp-threshold",
                      type="int",
                      action="store",
                      default=10,
                      help="minimum number of elements in HTML, for a timestamp to be added",)
    parser.add_option("--popups",
                      action="store_true",
                      dest="popups",
                      default=False,
                      help="enable equation and figure popup windows on clicking their references",)
    parser.add_option("--add-wrap",
                      action="store_true",
                      dest="add_wrap",
                      default=False,
                      help="add a standard latex wrapper, with documentclass and begin{document}...end{document}",)
    parser.add_option("--allow-directories",
                      action="store_true",
                      dest="allow_dirs",
                      default=False,
                      help="allow subdirectory structure in the xml output",)
    parser.add_option("--output-course-unit-tests",
                      action="store",
                      dest="output_cutset",
                      default="",
                      help="filename in which to output answer box unit test set (YAML format) for the course, made for testing with edxcut",)
    (opts, args) = parser.parse_args()

    if len(args) < 1:
        print('latex2edx: wrong number of arguments')
        parser.print_help()
        sys.exit(-2)
    fn = args[0]

    config = DEFAULT_CONFIG
    extra_xml_filters = []
    # load local configuration file if available
    if os.path.exists(opts.config_file):
        import imp
        # prepend the config file's directory to the path to allow local imports inside it
        sys.path.insert(0, os.path.dirname(opts.config_file))
        cf = imp.load_source('config_file', opts.config_file)
        config.update(getattr(cf, 'local_config', {}))
        extra_xml_filters.extend(getattr(cf, 'extra_xml_filters', []))

    c = latex2edx(fn, verbose=opts.verbose, output_fn=opts.output_fn,
                  output_dir=opts.output_dir,
                  do_merge=opts.merge,
                  update_policy=opts.update_policy,
                  suppress_policy=opts.suppress_policy,
                  suppress_verticals=opts.suppress_verticals,
                  section_only=opts.section_only,
                  add_wrap=opts.add_wrap,
                  xml_only=opts.xml_only,
                  units_only=opts.units_only,
                  popup_flag=opts.popups,
                  allow_dirs=opts.allow_dirs,
                  output_cutset=opts.output_cutset,
                  extra_xml_filters=extra_xml_filters,
                  add_timestamp=opts.timestamp,
                  timestamp_revision=opts.timestamp_revision,
                  timestamp_threshold=opts.timestamp_threshold,
                  )
    c.convert()


