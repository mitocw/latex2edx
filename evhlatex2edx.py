#!/usr/bin/python
#
# File:   latex2edx.py
# Date:   19-Jun-12
# Author: I. Chuang <ichuang@mit.edu>
#
# use plasTeX to convert latex document to edX problem specification language format
#
# 1. convert to XHTML + edX tags using plasTeX
# 2. conert to edX course, with course.xml and problems
#
# Example usage:
#
# python latex2edx.py example1.tex
# python latex2edx.py -d problems example2.tex
#
# This python script expects abox.py, edXpsl.py, render/edXpsl.zpts, and render/Math.zpts
# to be in the same directory as the script.
#
# 13-Aug-12: does html files (edXtext), javascript, include, answer
# 22-Jan-13: use new XML format
# 23-Jan-13: add video tag handling, unbundle course to course/*.xml if url_name acceptable

import os, sys, string, re, urllib, fnmatch
import glob
from plasTeX.TeX import TeX
from plasTeX.Renderers import XHTML
from plasTeX.Renderers.PageTemplate import Renderer as _Renderer
from xml.sax.saxutils import escape, unescape
from lxml import etree
from lxml.html.soupparser import fromstring as fsbs
import csv
import codecs
import copy
from abox import AnswerBox, split_args_with_quoted_strings
from PIL import Image
import math

# set the zpts templates path
zptspath = os.path.abspath('render')
os.environ['XHTMLTEMPLATES'] = zptspath

INPUT_TEX_FILENAME = ''

#-----------------------------------------------------------------------------

class MyRenderer(XHTML.Renderer):
    '''
    PlasTeX class for rendering the latex document into XHTML + edX tags
    '''

    def processFileContent(self, document, s):
        s = XHTML.Renderer.processFileContent(self,document,s)

        def fix_math(m):
            x = m.group(1).strip()
            x = x.replace(u'\u2019',"'")
            x = x.decode('ascii','ignore')
            if len(x)==0:
                return "&nbsp;"
            if x=="\displaystyle":
                return "&nbsp;"

            #return '{%% math eq="%s" %%}' % urllib.quote(x,safe="")
            x = x.replace('\n','')
            x = escape(x)
            return '[mathjaxinline]%s[/mathjaxinline]' % x
            #EVH replace above with: return '\\\(%s\\\)' % x

        def fix_displaymath(m):
            x = m.group(1).strip()
            x = x.replace(u'\u2019',"'")
            x = x.decode('ascii','ignore')
            if len(x)==0:
                return "&nbsp;"
            if x=="\displaystyle":
                return "&nbsp;"
            x = x.replace('\n','')
            x = escape(x)
            return '[mathjax]%s[/mathjax]' % x

        def do_image(m):
            style = m.group(1)
            sm = re.search('width=([0-9\.]+)(.*)',style.replace(' ',''))
            if sm:
                widtype = sm.group(2)
                width = float(sm.group(1))
                if 'in' in widtype:
                    width = width * 110
                width = int(width)
                if width==0:
                    width = 400
            else:
                # CL: 16.06r -- find image size and make percentage be multiple of width in pixels #EVH: works if a PNG file
                path_to_image = m.group(2)
                img = Image.open(path_to_image + ".png")
                w, h = img.size
                width = w/8  # using this as percentage for width and height below

            def make_image_html(fn,k):
                self.imfnset.append(fn+k)
                # if file doesn't exist in edX web directory, copy it there
                fnbase = os.path.basename(fn)+k
                print "fnbase =", fnbase
                wwwfn = '%s/%s' % (self.imdir,fnbase)
                if 1:
                    cmd = 'cp %s %s' % (fn+k,wwwfn)
                    os.system(cmd)
                    print cmd
                    os.system('chmod og+r %s' % wwwfn)
                return '<img src="/static/%s/%s" width="%d%%" height="%d%%"/>' % (imurl,fnbase,width,width)  # specifying width and height percentage now

            fnset = [m.group(2)]
            fnsuftab = ['','.png','.pdf','.png','.jpg']
            for k in fnsuftab:
                for fn in fnset:
                    if os.path.exists(fn+k):
                        if k=='.pdf':		# convert pdf to png
                            dim = width if width>400 else 400
                            # see how many pages it is
                            try:
                                npages = int(os.popen('pdfinfo %s.pdf | grep Pages:' % fn).read()[6:].strip())
                            except Exception, err:
                                # print "npages error %s" % err
                                npages = 1

                            nfound = 0
                            if npages>1:	# handle multi-page PDFs
                                fnset = ['%s-%d' % (fn,x) for x in range(npages)]
                                nfound = sum([ 1 if os.path.exists(x+'.png') else 0 for x in fnset])
                                print "--> %d page PDF, fnset=%s (nfound=%d)" % (npages, fnset, nfound)

                            if not nfound==npages:
                                os.system('convert -density 800 {fn}.pdf -scale {dim}x{dim} {fn}.png'.format(fn=fn,dim=dim))

                            if npages>1:	# handle multi-page PDFs
                                fnset = ['%s-%d' % (fn,x) for x in range(npages)]
                                print "--> %d page PDF, fnset=%s" % (npages, fnset)
                            else:
                                fnset = [fn]
                            imghtml = ''
                            for fn2 in fnset:
                                imghtml += make_image_html(fn2,'.png')
                            return imghtml
                        else:
                            return make_image_html(fn,k)

            fn = fnset[0]
            print 'Cannot find image file %s' % fn
            return '<img src="NOTFOUND-%s">' % fn

        # processFileContents STARTS HERE

        ucfixset = { u'\u201d': '"',
                     u'\u2014': '-',
                     u'\u2013': '-',
                     u'\u2019': "'",
                     }

        for pre, post in ucfixset.iteritems():
            try:
                s = s.replace(pre,post)
            except Exception, err:
                print "Error in MyRenderer.processFileContent (fix unicode): ",err

        def do_abox(m):
            print "\nDOING abox!!"
            if m.group(1).find('type="justification"') >= 0: # justification response
                print m.group(1)
                print "Justification response box being processed..."
                return '</p><p><textarea rows="5" style="width:600px;height:100px"></textarea>'
            else: # handle like normal abox
                return AnswerBox(m.group(1)).xmlstr

        def do_iframe(m):
            print m.group(0).encode("utf-8")
            code = m.group(0).encode("utf-8")
            code = re.sub(r'http:',r'',code)
            # add code to put download link, by processing the video_master_list.csv file
            # 1.load csv file
            if (code.find('DOUBLEHYPHEN')>=0):
                print "FOUND VIDEO WITH DOUBLE HYPHEN!!!"
                code = re.sub(r'DOUBLEHYPHEN',r'',code)
                print code
            with open('video_master_list.csv', 'rb') as csvfile:
            # 2.for each row
                videoreader = csv.reader(csvfile, delimiter=',', quotechar='"')
                for row in videoreader:
            # 3.    grab the youtube embed code string (#7 position)
                    edXyoutubeembedcode = row[6].strip()
                    MITxyoutubeembedcode = row[4].strip()
                    # remove DOUBLEHYPHEN from video master list entry
                    edXyoutubeembedcode = re.sub(r'DOUBLEHYPHEN',r'',edXyoutubeembedcode)
                    MITxyoutubeembedcode =  re.sub(r'DOUBLEHYPHEN',r'',MITxyoutubeembedcode)
            # 4.    if this iframe call uses that string
                    if edXyoutubeembedcode!="" and code.find(edXyoutubeembedcode)>=0:
                        dlurl = row[7]
                        code += '<p><a href="%s">Download this video</a></p>' % dlurl
                        print "code =", code
                    elif MITxyoutubeembedcode!="" and edXyoutubeembedcode!="" and code.find(MITxyoutubeembedcode)>=0:
                        print "MIT embed =", MITxyoutubeembedcode
                        print "edX embed =", edXyoutubeembedcode
                        if (code.find(MITxyoutubeembedcode)>=0): # MITx youtube code in there still
                            code = re.sub(MITxyoutubeembedcode,edXyoutubeembedcode,code) # switch it to edX code
            # 5.        grab the download url from this row
                        dlurl = row[7]
            # 6.        create the extra code to append to make download link
                        code += '<p><a href="%s">Download this video</a></p>' % dlurl
                        print "code =", code
            return code

        def do_imageresponse(m):
            imgsrc = m.group(1)
            width = m.group(2)
            height = m.group(3)
            rectangle = m.group(4)
            print "inside of do_imageresponse"
            self.imfnset.append(imgsrc)
            fnbase = os.path.basename(imgsrc)
            wwwfn = '%s/%s' % (self.imdir,fnbase)
            if 1:
                cmd = 'cp %s %s' % (imgsrc,wwwfn)
                os.system(cmd)
                print cmd
                os.system('chmod og+r %s' % wwwfn)
            return '<imageinput src="/static/%s/%s" width="%s" height="%s" rectangle="%s"/>' % (imurl,fnbase,width,height,rectangle)

        try:
            s = re.sub('(?s)<math>\$(.*?)\$</math>',fix_math,s)
            s = re.sub(r'(?s)<math>\\begin{equation}(.*?)\\end{equation}</math>',fix_displaymath,s)
            s = re.sub(r'(?s)<displaymath>\\begin{edXmath}(.*?)\\end{edXmath}</displaymath>',fix_displaymath,s)
            s = re.sub(r'(?s)<math>\\\[(.*?)\\\]</math>',fix_displaymath,s)
            s = re.sub('<includegraphics style="(.*?)">(.*?)</includegraphics>',do_image,s)	# includegraphics

            s = re.sub('(?s)<edxxml>\\\\edXxml{(.*?)}</edxxml>','\\1',s)
            s = re.sub(r'(?s)<iframe(.*?)></iframe>',do_iframe,s)  # edXinlinevideo
            s = re.sub(r'LESSTHAN',r'<',s)
            s = re.sub(r'GREATERTHAN',r'>',s)

            # check 1
            fff = open('check1.txt','w')
            fff.write(s.encode('utf-8'))
            fff.close()

            s = re.sub(r'(?s)<customresponse(.*?)cfn="defaultsoln"(.*?)</customresponse>','<customresponse cfn="defaultsoln" expect=""><textline size="90" correct_answer=""/></customresponse>',s)

            s = re.sub(r'(?s)<abox>(.*?)</abox>',do_abox,s) # THIS MUST COME AFTER CUSTOMRESPONSE HANDLING!!!

            s = re.sub(r'(?s)<textline correct_answer=""/>','<textline size="90" correct_answer=""/>',s)

            # check 2
            fff = open('check2.txt','w')
            fff.write(s.encode('utf-8'))
            fff.close()

            s = re.sub(r'(?s)<imageinput src="(.*?)" width="(.*?)" height="(.*?)" rectangle="(.*?)"/>',do_imageresponse,s)

        except Exception, err:
            print "Error in MyRenderer.processFileContent: ",err
            raise

        s = s.replace('<p>','<p>\n')
        s = s.replace('<li>','\n<li>')
        s = s.replace('&nbsp;','&#160;')

        s = s[s.index('<body>')+6:s.index('</body>')]

        XML_HEADER = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta content="text/html; charset=utf-8" http-equiv="content-type" />
</head>
<document>
"""
        XML_TRAILER = """</document></html>"""

        return XML_HEADER + s + XML_TRAILER

    def cleanup(self, document, files, postProcess=None):
        res = _Renderer.cleanup(self, document, files, postProcess=postProcess)
        return res

#-----------------------------------------------------------------------------
# make an acceptable url name
# note that all url names must be unique!

URLNAMES = []

def make_urlname(s):
    map = {'"\':<>': '',
           ',/().;=+ ': '_',
           '/': '__',
           '&': 'and',
            '?': '',
           }
    for m,v in map.items():
        for ch in m:
            s = s.replace(ch,v)
    URLNAMES.append(s)
    return s

#-----------------------------------------------------------------------------
# output problem into XML file

def content_to_file(content, tagname, fnsuffix, pdir='.', single='', fnprefix=''):
    pname = content.get('url_name','noname')
    dispname = content.get('display_name')
    if pname=="noname":
        pname = dispname
    pfn = make_urlname(pname)
    pfn = fnprefix + pfn
    if (pfn.find("Measurable_outcomes")>=0 or pfn.find("Pre-requisite_material")>=0):
        pfn = pfn + content.get('chapnum')
        print "pfn =", pfn
    print "  %s '%s' --> %s/%s.%s" % (tagname,pname,pdir,pfn,fnsuffix)

    #set default attributes for problems
    if tagname=='problem':
        if content.get('showanswer') is None:
            content.set('showanswer','closed')
        if content.get('rerandomize') is None:
            content.set('rerandomize','never')

    # EVH, this is CL setting display_name
    if content.get('display_name') is None:
        content.set('display_name',pname)

    #extract attributes from attrib_string
    attrib_string = content.get('attrib_string','')
    if attrib_string:
        attrib_list=split_args_with_quoted_strings(attrib_string)
        if len(attrib_list)==1 & len(attrib_list[0].split('='))==1: #a single number n is interpreted as weight="n"
            content.set('weight',attrib_list[0])
            content.attrib.pop('attrib_string') #remove attrib_string
        else: #the normal case, can remove backwards compatibility later if desired
            for s in attrib_list:
                attrib_and_val=s.split('=')
                if len(attrib_and_val) != 2:
                    print "ERROR! the attribute list for content %s.%s is not properly formatted" % (pfn,fnsuffix)
                    sys.exit(-1)
                content.set(attrib_and_val[0],attrib_and_val[1].strip("\"")) #remove extra quotes
            content.attrib.pop('attrib_string') #remove attrib_string

    # create a copy to return of the content tag, with just the filename as the url_name
    nprob = etree.Element(tagname)
    nprob.set('url_name',pfn)
    content.attrib.pop('url_name')       	# remove url_name from our own tag

    #open('%s/%s.xml' % (pdir,pfn),'w').write(etree.tostring(content,pretty_print=True))
    if single:
        ppath = single
    else:
        ppath = '%s/%s.%s' % (pdir,pfn,fnsuffix)
        if not os.path.exists(pdir):
            print "ERROR! Directory %s does not exist - please create it, or specify differently" % pdir
            sys.exit(-1)
    os.popen('xmllint -format -o %s -' % ppath,'w').write(etree.tostring(content,pretty_print=True))
    if single:
        print "Generated single output file '%s'" % ppath
        sys.exit(0)
    return pfn, nprob

def problem_to_file(problem, pdir='.', single='', fnprefix=''):
    return content_to_file(problem,'problem','xml', pdir, single=single, fnprefix=fnprefix)

def html_to_file(html, pdir='.', single='', fnprefix=''):
    return content_to_file(html,'html','xml',pdir, single=single, fnprefix=fnprefix)

#-----------------------------------------------------------------------------
# helper functions for constructing course.xml

def cleanup_xml(xml):

    # clean up course tree so it has nothing but allowed tags

    psltags = ['course', 'chapter', 'section', 'sequential', 'vertical', 'problem', 'html', 'video', 'iframe', 'discussion']
    def walk_tree(tree):
        nchildren = [walk_tree(x) for x in tree]
        while None in nchildren: nchildren.remove(None)
        if tree.tag not in psltags:
            # print "    Dropping %s (%s)" % (tree.tag,etree.tostring(tree))
            if len(tree)==0: return None
            for nc in nchildren:
                tree.addprevious(nc)
                # print "      moving up %s" % nc
            tree.getparent().remove(tree)
        return tree

    walk_tree(xml)

    FLAG_drop_sequential = False

    if FLAG_drop_sequential:
        # 21jan13 new xml format: drop section, add display_name to sequential and to chapter
        for ch in xml.findall('.//chapter'):
            un = ch.get('url_name','')
            if un:
                ch.set('display_name',un)
                ch.attrib.pop('url_name')
        for seq in xml.findall('.//sequential'):
            p = seq.getparent()
            dn = seq.get('display_name','')
            if p.tag=='section':
                ndn = p.get('url_name','')
                if not dn and ndn:
                    seq.set('display_name',ndn)
                p.addnext(seq)	# move up to parent's level

        for sec in xml.findall('.//section'):
            if len(sec)>0:
                print "oops, non-empty section!  sec=%s" % etree.tostring(sec)
            else:
                sec.getparent().remove(sec)

    FLAG_convert_section_to_sequential = True
    if FLAG_convert_section_to_sequential:
        # 23jan13 - convert <section> (which is no longer used) to <sequential>
        # and turn url_name into display_name
        # 11jun13 - added section counter to allow for multiple chapters with
        # the same section heading; creates url_name attribute with appended number

        chapnum = 0
        for chap in xml.findall('.//chapter'):
            if chap.get('nocount') is None:
                chapnum += 1
            for sec in chap.findall('.//section'):
                sec.tag = 'sequential'
                un = sec.get('url_name','')
                if un:
                    sec.set('display_name',un)
                    if un.lower() in ['overview','sample problems', 'homework problems']:
                        sec.set('url_name',make_urlname(un+str(chapnum)))
                    else:
                        sec.set('url_name',make_urlname(un))
                    #sec.attrib.pop('url_name')
                    print sec.get('url_name')

    # move contents of video elements into attrib
    for video in xml.findall('.//video'):
        try:
            chk = etree.XML('<video %s/>' % video.text)
        except Exception, err:
            print "[latex2edx] Oops, badly formatted video tag attributes: '%s'" % video.text
            sys.exit(-1)
        video.addprevious(chk)
        video.getparent().remove(video)
        print "  video element: %s" % etree.tostring(chk)

    return xml

#-----------------------------------------------------------------------------
# update content (problem or html)

def update_content(section, existing_section, tagname):
    for content in section.findall('.//%s' % tagname):
        pfound = False
        for existing_content in existing_section.findall('.//%s' % tagname):
            if content.get('url_name') == existing_content.get('url_name'):	# content exists
                pfound = True
        if not pfound:					# add content to sequential inside section
            seq = existing_section.find('.//sequential')
            if seq is None:
                seq = etree.SubElement(existing_section,'sequential')
            seq.append(content)
            print "         Added new %s '%s' to section" % (tagname,content.get('url_name'))

#-----------------------------------------------------------------------------
# update chapter in course.xml file

def update_chapter(chapter,cdir):

    # find the course.xml file
    cxfn = '%s/course.xml' % (cdir)
    if not os.path.exists(cxfn):
        print "Error: Cannot find %s ; please specify the proper directory with -d" % cxfn
        usage()
    course = etree.parse(cxfn)

    # extract problems & html
    pdir = '%s/problem' % cdir
    hdir = '%s/html' % cdir
    extract_problems(chapter,pdir)
    extract_html(chapter,hdir)
    cleanup_xml(chapter)

    # see if chapter exists already
    chapfound = False
    for existing_chapter in course.findall('//chapter'):
        if chapter.get('url_name') == existing_chapter.get('url_name'):			# chapter exists
            print "    --> Found existing chapter '%s'" % chapter.get('url_name')
            for section in chapter.findall('.//section'):
                secfound = False
                for existing_section in existing_chapter.findall('.//section'):
                    if section.get('url_name') == existing_section.get('url_name'):	# section exists
                        print "      --> Found existing section '%s'" % section.get('url_name')
                        secfound = True
                        update_content(section,existing_section,'problem')
                        update_content(section,existing_section,'html')
                if not secfound:						# section does not exist
                    print "      --> Adding section '%s'" % section.get('url_name')
                    existing_chapter.append(section)				# add new section to the chapter
            chapfound = True
    if not chapfound:								# chapter does not exist
        print "      --> Adding chapter '%s'" % chapter.get('url_name')
        course.getroot().append(chapter)					# add new chapter to the course

    # write out course.xml
    os.popen('xmllint -format -o %s -' % cxfn,'w').write(etree.tostring(course,pretty_print=True))

#-----------------------------------------------------------------------------
# extract problems into separate XML files

def extract_problems(tree,pdir,fnprefix=''):
    # extract problems and put those in separate files
    for problem in tree.findall('.//problem'):
        # EVH: can this be turned into a latex macro?
        # CL: attempt to insert a javascript tag at the top of the page
        jselement = etree.Element("script")
        jselement.set('src',"/static/latex2edx.js")
        jselement.set('type',"text/javascript")
        problem.insert(0,jselement)
        problem.set('source_file',INPUT_TEX_FILENAME)
        pfn, nprob = problem_to_file(problem,pdir,fnprefix=fnprefix)	# write problem to file
        # remove all attributes, put in url_name, source_file into the <problem> tag in course.xml
        #for a in nprob.attrib:
        #    nprob.attrib.pop(a)
        #nprob.set('url_name',pfn)
        parent = problem.getparent()		# replace problem with <problem ... /> course xml link
        parent.insert(parent.index(problem),nprob)
        parent.remove(problem)

#-----------------------------------------------------------------------------
# extract html segments into separate XML files

def extract_html(tree,pdir,fnprefix=''):
    # extract html segments and put those in separate files
    for html in tree.findall('.//html'):
        # EVH: again
        # CL: attempt to insert a javascript tag at the top of the page
        jselement = etree.Element("script")
        jselement.set('src',"/static/latex2edx.js")
        jselement.set('type',"text/javascript")
        html.insert(0,jselement)
        html.set('source_file',INPUT_TEX_FILENAME)
        pfn, nprob = html_to_file(html,pdir,fnprefix=fnprefix)
        # nprob.set('filename',pfn)
        parent = html.getparent()		# replace html with <html ... /> course xml link
        parent.insert(parent.index(html),nprob)
        parent.remove(html)

#-----------------------------------------------------------------------------
# create a partial policy file for easier policy generation

def generate_partial_policy_file(course,pdir):
    '''
    This function is intended to generate a partial policy file (the part pertaining to edX problems) with default information so that setting point values for the problems is much easier, but without interfering with the content (in LaTeX source) itself.  The output goes to /partial_policy.json, where / refers to the latex directory in content repo.
    '''

    # little function for getting the display_name attribute from already saved separate problem files
    def get_problem_display_name(url_name,pdir):
        pfile = open(os.path.join(pdir, url_name + ".xml"),'r')
        topline = pfile.readline()
        topline = pfile.readline() # the info we need is on the second line of the file
        # print topline
        # get the display_name attribute from there
        m = re.search('display_name=\"(.+?)\"',topline)
        if m:
            display_name = m.group(1)
        else:
            display_name = ""
        m = re.search('weight=\"(.+?)\"',topline)
        if m:
            weight = m.group(1)
        else:
            weight = 0
        pfile.close()
        # print display_name
        return display_name, weight

    print "\n\nENTERED GENERATE_PARTIAL_POLICY_FILE\n"
    fpath = os.path.abspath(fn)
    dir = os.path.dirname(fpath)
    f = open(os.path.join(dir, "partial_policy.json"),'w')
    for chapter in course.findall('.//chapter'):
        name = chapter.get('display_name')
        #print name
        #raw_input("Press enter yo")
        if name=="Overview of 16.06r" or name=="Test":
            continue
        modtotCQweight = 0
        modtotHWweight = 0
        print name
        for sequential in chapter.findall('.//sequential'):
            seqwritten = False
            for problem in sequential.findall('.//problem'):
                # because of the order things are done, it is necessary to go dig up the problem display name
                # from the already saved problem file
                problem_display_name, problem_weight = get_problem_display_name(problem.get('url_name'),pdir)
                print problem_display_name
                print "weight =", problem_weight
                if not seqwritten:
                    f.write('\t\"sequential/%s\": {\n' % sequential.get('url_name'))
                    if sequential.get('display_name')=="Sample Problems":
                        f.write('\t\t\"graded\": false\n')
                    else:
                        f.write('\t\t\"graded\": true,\n')
                        f.write('\t\t\"due\": \"2013-08-06T03:59\"\n')
                    f.write('\t},\n')
                    seqwritten = True
                problem_format = ""
                if sequential.get('display_name')=="Homework Problems":
                    print "homework problem\n"
                    problem_format = "%s Homework Problems" % name
                    problem_attempts = str(2)
                    problem_graded = "true"
                    problem_showanswer = "past_due"
                    modtotHWweight += int(problem_weight)
                elif sequential.get('display_name')=="Sample Problems":
                    print "sample problem\n"
                    problem_format = "%s Sample Problems" % name
                    problem_attempts = "0"
                    problem_graded = "false"
                    problem_showanswer = "always"
                else:
                    print "concept question\n"
                    problem_format = "%s Concept Questions" % name
                    problem_attempts = "10"
                    problem_graded = "true"
                    problem_showanswer = "closed"
                    modtotCQweight += int(problem_weight)

                f.write('\t\"problem/%s\": {\n' % problem.get('url_name'))
                f.write('\t\t\"display_name\": \"%s\",\n' % problem_display_name)
                f.write('\t\t\"graded\": %s,\n' % problem_graded)
                f.write('\t\t\"format\": \"%s\",\n' % problem_format)
                f.write('\t\t\"showanswer\": \"%s\",\n' % problem_showanswer)
                f.write('\t\t\"attempts\": \"%s\"\n' % problem_attempts)
                f.write('\t},\n')
    f.close()


#-----------------------------------------------------------------------------
# output course into XML file

def course_to_files(course, update_mode, default_dir, fnprefix=''):

    cnumber = course.get('number')	# course number, like 18.06x
    print "Course number: %s" % cnumber
    cdir = cnumber

    #EVH added
    attrib_string = course.get('attrib_string','')
    if attrib_string:
        attrib_list=split_args_with_quoted_strings(attrib_string)
        for s in attrib_list:
            attrib_and_val=s.split('=')
            if len(attrib_and_val) != 2:
                print "ERROR! the attribute list for content %s.%s is not properly formatted" % (pfn,fnsuffix)
                sys.exit(-1)
            course.set(attrib_and_val[0],attrib_and_val[1].strip("\""))
        course.attrib.pop('attrib_string')

    # if udpating instead of creating, use dir if given
    if update_mode and not default_dir == '.':
        cdir = default_dir

    if update_mode:
        for chapter in course.findall('.//chapter'):	# get all chapters
            update_chapter(chapter,default_dir)
        return

    pdir = '%s/problem' % cdir
    hdir = '%s/html' % cdir
    if not os.path.exists(cdir):
        os.mkdir(cdir)
        if not os.path.exists(pdir):
            os.mkdir(pdir)
        if not os.path.exists(hdir):
            os.mkdir(hdir)

    extract_problems(course,pdir,fnprefix)
    extract_html(course,hdir,fnprefix)
    cleanup_xml(course)

    # EVH - CL's policy
    # write partial policy file
    generate_partial_policy_file(course,pdir)

    # if the url_name given is in reasonable format, eg 2013_Fall (no spaces), then write
    # contents of <course> to that filename in the course subdir, ie unbundle it
    if not ' ' in course.get('url_name',''):
        course = unbundle(cdir, course)

    if not course.get('course',''):	# ensure that <course> has course="number" and org="MITx"
        course.set('course',cnumber)
        course.set('org','MITx')

    # write out course.xml
    #open('%s/course.xml' % cdir,'w').write(etree.tostring(course,pretty_print=True))
    os.popen('xmllint -format -o %s/course.xml -' % cdir,'w').write(etree.tostring(course,pretty_print=True))


def unbundle(cdir, xml):
    '''Unbundle XML by one level, by writing pointer tag using url_name, and contents to subdir of tag name'''
    un = xml.get('url_name','')
    if not un:
        return xml
    uname = make_urlname(un)

    # write out out XML as a file with name url_name in directory ./tag
    xml.attrib.pop('url_name')
    tdir = '%s/%s' % (cdir, xml.tag)
    if not os.path.exists(tdir):
        os.mkdir(tdir)
    os.popen('xmllint -format -o %s/%s.xml -' % (tdir,uname),'w').write(etree.tostring(xml,pretty_print=True))

    nxml = etree.Element(xml.tag)
    nxml.set('url_name',uname)
    return nxml

#-----------------------------------------------------------------------------
# process edX macros like edXshowhide and edXinclude, which are not handled by plasTeX

def process_edXmacros(tree):
    add_chapter_url_names(tree)
    fix_div(tree)
    fix_table(tree)
    fix_center(tree)
    fix_figure_refs(tree)
    handle_equation_labels_and_refs(tree)
    handle_section_refs(tree)
    check_for_missing_refs(tree)
    add_figure_padding(tree)
    process_include(tree)
    process_showhide(tree)
    fix_boxed_equations(tree)  # note this should come after fix_table always
    add_chap_num_to_content(tree)
    check_for_repeated_urlnames(tree)
    ensure_relative_url_for_youtube_embeds(tree)
    change_problem_display_names_to_have_counters(tree)
    add_titles_to_edxtext(tree)

# EVH: this is way too convoluted, and should be changed, possibly to a macro
# attempt to set display names with numbers below (but I think display_names are being set elsewhere down the line
def change_problem_display_names_to_have_counters(tree):
    chapnum = -1
    for chap in tree.findall('.//chapter'):
        if chap.get('nocount') is not None:
            continue
        chapnum += 1
        sectionnum = 0
        for section in chap.findall('.//section'):
            sectionnum += 1
            pagenum = 0
            for p in section.findall('.//p'): # CHAD: use surrounding p-tags to my advantage
                htmls = p.findall('.//html')
                probs = p.findall('.//problem')
                verts = p.findall('.//vertical')
                allverts = htmls + probs + verts
                for vert in allverts:
                    verttag = vert.tag
                    if (verttag=="html" or verttag=="problem"):
                        # check if this is contained in a vertical, because if it is, we want to skip it here
                        in_vertical = False
                        for testvert in section.findall('.//vertical'):
                            for testproblem in testvert.findall('.//problem'):
                                if testproblem.get('url_name')==vert.get('url_name'):
                                    in_vertical = True
                        if not in_vertical:
                            currdispname = vert.get('url_name')
                            pagenum += 1
                            vert.set('display_name',"%d.%d.%d %s" % (chapnum,sectionnum,pagenum,currdispname))
                    elif (verttag=="vertical"):
                        for problem in vert.findall('.//problem'):
                            currdispname = problem.get('url_name')
                            pagenum += 1
                            problem.set('display_name',"%d.%d.%d %s" % (chapnum,sectionnum,pagenum,currdispname))
                            break # name contained in first problem of vertical
                    else:
                        print "UNRECOGNIZED VERTICAL TAG TYPE"

# EVH: this is a good check, but should be standardized
def check_for_repeated_urlnames(tree):
    urlnames = []
    for html in tree.findall('.//html'):
        pname = html.get('url_name','noname')
        if pname=="noname":
            pname = html.get('display_name')
        pfn = make_urlname(pname)
        if pfn in urlnames:
            print "ERROR: REPEATED URL_NAME = %s" % pfn
            sys.exit(-1)
        if (pfn.find("Measurable_outcomes")>=0 or pfn.find("Pre-requisite_material")>=0):
            urlnames = urlnames # dont add it
        else:
            urlnames.append(pfn)
    for problem in tree.findall('.//problem'):
        pname = problem.get('url_name','noname')
        if pname=="noname":
            pname = problem.get('display_name')
        pfn = make_urlname(pname)
        if pfn in urlnames:
            print "ERROR: REPEATED URL_NAME = %s" % pfn
            sys.exit(-1)
        if (pfn.find("Measurable_outcomes")>=0 or pfn.find("Pre-requisite_material")>=0):
            urlnames = urlnames
        else:
            urlnames.append(pfn)

# EVH: should be able to make a macro of this as well
def add_chap_num_to_content(tree):
    '''
    Add a trailing module number to measurable outcomes urlname
    '''
    chapnum = 0
    for chap in tree.findall('.//chapter'):
        #if chap.get('nocount') is not None:
        #    continue
        #chapnum += 1
        if chap.get('nocount') is None:
            chapnum += 1
        for section in chap.findall('.//section'):
            for html in section.findall('.//html'):
                html.set('chapnum','%d' % chapnum)
            for problem in section.findall('.//problem'):
                problem.set('chapnum','%d' % chapnum)
            for vertical in section.findall('.//vertical'):
                for html in vertical.findall('.//html'):
                    html.set('chapnum','%d' % chapnum)
                for problem in vertical.findall('.//problem'):
                    problem.set('chapnum','%d' % chapnum)

def ensure_relative_url_for_youtube_embeds(tree):
    '''
    Make sure links for youtube embeds are relative (like <iframe src="//www.youtube.com/embed/RaRLRRLHjnc?rel=0" width="600" height="400"/>)
    '''
    for iframe in tree.findall('.//iframe'):
        print "found iframe"
        iframe_src = iframe.get('src')
        iframe_src = re.sub(r'http:',r'',iframe_src)
        iframe.set('src',iframe_src)

def add_chapter_url_names(tree):
    '''
    Add chapter url_name so we can reference them in policy file
    '''
    for chapter in tree.findall('.//chapter'):
        display_name = chapter.get('display_name')
        url_name = make_urlname(display_name)
        chapter.set('url_name',url_name)
        print "\n CHAPTER URL: %s \n" % url_name

#EVH Needs a macro
def add_titles_to_edxtext(tree):
    '''
    Add the titles as <h2 class="problem-header">?</h2> elements to each edXtext section
    '''
    for html in tree.findall('.//html'):
        disp_name = html.get('display_name')
        header_sub_element = etree.Element('h2',{'class':"problem-header"})
        header_sub_element.text = disp_name
        html.insert(0, header_sub_element)
        # raw_input("Press ENTER")

# EVH
def getlabel(tree): #TODO: Find a cleaner way to build the eTree
    '''
    Search etree element for label tag, retrieve label text, and delete label element.
    '''
    labeltext = None
    label = tree.find('./p/label')
    if label is None:
        label = tree.find('./label')
        plabel = label
    else:
        plabel = label.getparent()
    if label is not None:
        labeltext = label.text
        #Need to save the tail text for measurable outcomes
        #Save the tail and append to tree text before deletion
        labeltail = label.tail
        if labeltail != ' ':
            treetext = tree.text
            if treetext == '\n':
                tree.text = labeltail
            else:
                treetext = treetext[:-1] #remove final carriage return (usually from a p tag)
                tree.text = '{}{}'.format(treetext,labeltail)
        tree.remove(plabel)
    return labeltext

# EVH: need to fix this, don't understand the complexity
def handle_section_refs(tree):
    '''
    Process references to sections of content -- create section numbering and the reference should be a link that opens in a new tab to the desired component
    '''
    tocFlag = True #EVH: choose whether or not to create a Table of Contents (tocindex.html)
    #EVH: if the above is false create internal links only, if true created ToC
    if tocFlag:
        #EVH start building tocindex.html
        toctree = etree.Element('html')
        toctree.append(etree.fromstring('<head></head>'))
        tocbody = etree.SubElement(toctree,'body')
        tocbody.append(etree.Element('h1'))
        tocbody[0].text = 'Measurable Outcome Index'
        tocbody.append(etree.Element('p'))
        tocbody[1].text = 'This index provides the links associated to each of the measurable outcomes for the course. By clicking on a measurable outcome below, you will see the content you can use to learn about that measurable outcome and the content that we use to assess your understanding of that measurable outcome.'
        tocbody[1].append(etree.Element('i'))
        tocbody[1][0].text = 'Please note that while some future content will be indexed here, some links may not work until the content has been officially released!'
    refdict = {} # start building a reference dictionary {'labeltag':'href'}
    numdict = {} # start building a numbering dictionary {'labeltag':'number'}
    chapnum = seqnumstr = vertnumstr = linum = 0 #eqnnum = fignum = 0
    for chapter in tree.findall('.//chapter'):
        if chapter.get('nocount') is None:
            chapnum += 1
            seqnumstr = vertnumstr = linum = 0 #eqnnum = fignum = 0
        chapname = chapter.get('display_name')
        chapurl = re.sub(r' ',r'_',chapname)
        chaplabel = getlabel(chapter)
        if tocFlag: #and chaplabel is not None:
            tocchap = etree.SubElement(tocbody,'a',href='../courseware/{}'.format(chapurl)) #EVH set initial chapter link
            tocchap.append(etree.Element('h2'))
            tocchap[0].text = chapname
        seqnum = 0
        for child1 in chapter:
            if child1.tag == 'p':
                if child1.find('./') is not None:
                    seq = child1.find('./')
            else:
                seq = child1
            if seq.tag not in ['sequential','vertical','section']:
                continue
            seqnum +=1
            seq.set('level','1') #EVH keep track of level
            if seq.get('nocount') is None:
                seqnumstr += 1
                vertnumstr = 0 #eqnnum = fignum = 0
            sequrl = seq.get('url_name')
            if sequrl.lower() in ["overview","sample problems","homework problems"]:
                sequrl += str(chapnum+1)
            sequrl = re.sub(r' ',r'_',sequrl)
            if seqnum==1 and (chaplabel is not None):
                if tocFlag: #and chaplabel is not None:
                    tocchap.set('href','../courseware/{}/{}'.format(chapurl,sequrl))
                refdict[chaplabel] = '../courseware/{}/{}'.format(chapurl,sequrl) #EVH is a /1 necessary?
                numdict[chaplabel] = str(chapnum)
            seqlabel = getlabel(seq)
            if seqlabel is not None:
                refdict[seqlabel] = '../courseware/{}/{}'.format(chapurl,sequrl)
                numdict[seqlabel] = '{}.{}'.format(chapnum,seqnumstr)
            vertnum = 0
            for child2 in seq:
                if child2.tag == 'p':
                    if child2.find('./') is not None:
                        vert = child2.find('./')
                else:
                    vert = child2
                #if vert.tag not in ['sequential','vertical','section']:
                if vert.tag not in ['sequential','vertical','section','problem','html']:
                    continue
                vertnum += 1
                vert.set('level','2') #EVH keep track of level
                if vert.get('nocount') is None:
                    vertnumstr += 1
                vertlabel = getlabel(vert)
                if vertlabel is not None:
                    refdict[vertlabel] = '../courseware/{}/{}/{}'.format(chapurl,sequrl,vertnum)
                    numdict[vertlabel] = '{}.{}.{}'.format(chapnum,secnum,vertnumstr)
                #EVH: Search for labeled lists (for measurable outcome)
                for childlist in vert.findall('.//'):
                    if childlist.tag not in ['ol','ul']:
                        continue
                    for li in childlist.findall('./li/p'):
                        linum += 1
                        lilabel = getlabel(li)
                        if lilabel is not None:
                            lilabelstr = '{}{}.{}'.format(lilabel.split(':')[0].upper(),chapnum,linum)
                            numdict[lilabel] = lilabelstr
                            linumstr = lilabelstr.replace(r'.','').lower()
                            if tocFlag:
                                refdict[lilabel] = 'CROSSREF{}'.format(li.text) #EVH save list item text
                                tocbody.append(etree.Element('a',name='anchor{}'.format(linumstr.upper())))
                                toctable = etree.SubElement(tocbody,'table',{'class':"wikitable collapsible collapsed",'itemtype':'measurable_outcome','id':'{}'.format(lilabel.split(':')[1])})
                                toctable = etree.SubElement(toctable,'tbody')
                                toctable.append(etree.Element('tr'))
                                toctable[0].append(etree.Element('th'))
                                toctable[0][0].append(etree.Element('a',{'href':'#','onClick':"$('#ind{}').toggle();return false;".format(linumstr),'id':'ind{}l'.format(linumstr),'name':'ind{}l'.format(linumstr)}))
                                #toctablabel = etree.SubElement(toctable[0][0][0],'strong',itemprop='name')
                                toctable[0][0][0].append(etree.Element('strong',itemprop='name'))
                                toctable[0][0][0][0].text = lilabelstr
                                toctable[0][0].append(etree.Element('span',itemprop='description'))
                                toctable[0][0][1].text = li.text
                                toctable.append(etree.Element('tr',id='ind{}'.format(linumstr),style='display:none'))
                                toctable[1].append(etree.Element('td'))
                                toctable[1][0].append(etree.Element('h3'))
                                toctable[1][0][0].text = 'Learn'
                                toctable[1][0].append(etree.Element('ul',{'class':'MOlearn','reftag':'{}'.format(lilabel),'reftype':'html'}))
                                toctable[1][0].append(etree.Element('h3'))
                                toctable[1][0][2].text = 'Assess'
                                toctable[1][0].append(etree.Element('ul',{'class':'MOasses','reftag':'{}'.format(lilabel),'reftype':'problem'}))
                            else:
                                refdict[lilabel] = '../courseware/{}/{}/{}/#ind{}'.format(chapurl,sequrl,vertnum,linumstr)
                                li.set('id','ind{}'.format(linumstr))
        if tocFlag:
            tocbody.append(etree.XML('<br/>'))
    # now find and replace reference everywhere with the correct number (and make it a link)
    chapnum = 0
    for chap in tree.findall('.//chapter'):
        chapname = chapter.get('display_name')
        chapurl = re.sub(r' ',r'_',chapname)
        if chap.get('nocount') is None:
            chapnum += 1
        for level1 in chap.findall(".//*[@level='1']"):
            levelcnt = level1.attrib.pop('level')
            sequrl = level1.get('url_name')
            if sequrl.lower() in ["overview","sample problems","homework problems"]:
                sequrl += str(chapnum+1)
            sequrl = re.sub(r' ',r'_',sequrl)
            vertnum = 0
            for level2 in level1.findall(".//*[@level='2']"):
                vertnum += 1
                for aref in level2.findall('.//ref'):
                    reflabel = aref.text
                    if reflabel in numdict:
                        if refdict[reflabel][:8] == 'CROSSREF': #EVH if tocFlag
                            print "EVH looking for reflabel: ", reflabel
                            paref = aref.getparent()
                            paref.remove(aref)
                            while paref.tag not in ['html','problem']:
                                paref = paref.getparent()
                            ptag = paref.tag
                            if ptag == 'problem':
                                oldmo = paref.get('measureable_outcomes')
                                if oldmo is None:
                                    newmo = reflabel.split(':')[1]
                                else:
                                    newmo = oldmo+','+reflabel.split(':')[1]
                                paref.set('measureable_outcomes',newmo)
                            #EVH create crossref link and add button at top of vertical
                            #href = '/jump_to_id/{}'.format(paref.get('url_name'))
                            href = '../courseware/{}/{}/{}'.format(chapurl,sequrl,vertnum)
                            taglist = paref.find(".//p[@id='taglist']")
                            if taglist is None:
                                taglist = etree.Element('p',id='taglist')
                                paref.insert(0,taglist)
                            linktext = {'type':"button",'border-radius':"2px",'title':"{}{}".format(numdict[reflabel],refdict[reflabel][8:]),'style':"cursor:pointer",'class':"mo_button",'onClick':"window.location.href='../tocindex/#anchor{}';".format(numdict[reflabel].replace(r'.',''))}
                            print "EVH link: ",linktext
                            link = etree.SubElement(taglist,'button',{'type':"button",'border-radius':"2px",'title':"{}{}".format(numdict[reflabel],refdict[reflabel][8:]),'style':"cursor:pointer",'class':"mo_button",'onClick':"window.location.href='../tocindex/#anchor{}';".format(numdict[reflabel].replace(r'.',''))})
                            print "EVH link: ",etree.tostring(link)
                            link.text = numdict[reflabel]
                            link.set('id',reflabel.split(':')[1])
                            tocitem = etree.Element('li')
                            tocitem.append(etree.Element('a',itemtype=ptag,href=href,itemprop='name'))
                            tocitem[0].text = paref.get('display_name')
                            for ul in toctree.findall(".//ul[@reftag='{}']".format(reflabel)):
                                if ul.get('reftype') == ptag:
                                    ul.append(tocitem)
                        else:
                            aref.tag = 'a'
                            aref.text = numdict[reflabel]
                            aref.set('href',refdict[reflabel])
                            aref.set('target',"_blank")

            for aref in level1.findall('.//ref'):
                reflabel = aref.text
                if reflabel in numdict:
                    if refdict[reflabel][:8] == 'CROSSREF': #EVH if tocFlag
                        paref = aref.getparent()
                        paref.remove(aref)
                        while paref.tag not in ['html','problem']:
                            paref = paref.getparent()
                        ptag = paref.tag
                        if ptag == 'problem':
                            oldmo = paref.get('measureable_outcomes')
                            if oldmo is None:
                                newmo = reflabel.split(':')[1]
                            else:
                                newmo = oldmo+','+reflabel.split(':')[1]
                            paref.set('measureable_outcomes',newmo)
                        #EVH create crossref link and add button at top of vertical
                        #href = '/jump_to_id/{}'.format(paref.get('url_name'))
                        href = '../courseware/{}/{}'.format(chapurl,sequrl)
                        taglist = paref.find(".//p[@id='taglist']")
                        if taglist is None:
                            taglist = etree.Element('p',id='taglist')
                            paref.insert(0,taglist)
                        link = etree.SubElement(taglist,'button',{'type':'button','border-radius':'2px','title':'{}{}'.format(numdict[reflabel],refdict[reflabel][8:]),'style':'cursor:pointer','class':'mo_button','onClick':"window.location.href='../tocindex/#anchor{}';".format(numdict[reflabel].replace(r'.',''))})
                        link.text = numdict[reflabel]
                        link.set('id',reflabel.split(':')[1])
                        tocitem = etree.Element('li')
                        tocitem.append(etree.Element('a',itemtype=ptag,href=href,itemprop='name'))
                        tocitem[0].text = paref.get('display_name')
                        for ul in toctree.findall(".//ul[@reftag='{}']".format(reflabel)):
                            if ul.get('reftype') == ptag:
                                ul.append(tocitem)
                    else:
                        aref.tag = 'a'
                        aref.text = numdict[reflabel]
                        aref.set('href',refdict[reflabel])
                        aref.set('target',"_blank")
    # end look for chapter references
    if tocFlag:
        print "EVH: writing ToC index content..."
        #os.popen('xmllint -format -o 'tocindex.html -','w').write(etree.tostring(toctree,pretty_print=True))
        tocf = open('tocindex.html','w')
        tocf.write(etree.tostring(toctree,method='html',pretty_print=True))
        tocf.close()

def check_for_missing_refs(tree):
    # once all of the labels have been found... need to go through and do something about the references that do not have associated labels
    # issue warning that requires user to press enter to continue
    for aref in tree.findall('.//ref'):
        print "\nref.text =", aref.text
        if aref.text is None:
            break
        else:
            print "WARNING: There is a reference to non-existent label %s" % aref.text
            raw_input("Press ENTER to continue")

#EVH: need to identify when this is used
def fix_boxed_equations(tree):
    '''
    Fix boxed equations: move boxed command outside of mathjax and instead
    modify the style of the cell containing the equation
    '''
    boxedFlag = False
    for table in tree.findall('.//table'):
        for tr in table.findall('.//tr'):
            for td in tr.findall('.//td'):
                if td.get('class') == "equation":
                    if re.search(r'\\boxed',td.text,re.S) is not None:
                        boxedFlag = True
                        tr.set('style',"border: 1px solid #000000 !important")
                        innertext = td.text
                        innertext = innertext.replace(r'\boxed','')
                        td.text = innertext
                        table.set('style',"table-layout:auto")
                        td.set('style',"border-right-style:hidden")
                if boxedFlag and td.get('class') == "eqnnum":
                    td.set('style',"width:20%;vertical-align:middle;text-align:left;border-left-style:hidden")
                    boxedFlag = False

def fix_figure_refs(tree):
    '''
    Fix figure references
    '''
    chapnum = fignum = 0
    for chapter in tree.findall('.//chapter'):
        if chapter.get('nocount') is None:
            chapnum = chapnum + 1
            fignum = 0
        for div in chapter.findall('.//div[@class="figure"]'):
            #Increment count if Figure is captioned
            for b in div.findall('.//b'):
                if re.search(r'Figure [0-9]+$',b.text,re.S) is not None:
                    fignum += 1
                    b.text = "Figure {}.{}".format(chapnum,fignum)
            figlabel = None
            label = div.find('.//label')
            if label is not None:
                figlabel = label.text
                plabel = label.getparent()
                if plabel.tag == 'p': #TODO: Find a cleaner way to build the eTree
                    label = plabel
                    plabel = plabel.getparent()
                plabel.remove(label)
            if figlabel is not None:
                # CHAD: for multi-image figures, collect all the image names
                # TODO: Find an example and investigate how to refine (as above)
                img_names = []
                for img in div.findall('.//img'):
                    img_src = img.get('src')
                    img_name = os.path.basename(img_src)
                    img_names.append(img_name)
                # look for references and put the right code
                print "looking for the reference %s ..." % figlabel
                for aref in tree.findall('.//ref'):
                    if aref.text == figlabel:
                        # change this ref element
                        aref.tag = 'a'
                        aref.text = '{}.{}'.format(chapnum,fignum)
                        if len(img_names)==1:  # single image figure
                            fig_name = img_names[0]
                            # find the image within directory of modules.tex (the tex file this is being run on)
                            latexfolder = os.getcwd()
                            imgpath = ''
                            for path, dirs, files in os.walk(latexfolder):
                                for filename in fnmatch.filter(files,fig_name):
                                    imgpath = os.path.join(path, filename)
                                    #if imgpath.find('figs') != -1:
                                    if os.path.exists(imgpath):
                                        fullimgpath = imgpath
                                        img = Image.open(fullimgpath)
                                        w, h = img.size
                                        ws = 0.50
                                        wp = (int)(w*ws)
                                        hp = (int)(h*ws)
                                        href = "/static/html/{}".format(fig_name)
                                        onClick = "window.open(this.href,\'16.06r\',\'width={},height={}\',\'toolbar=1\'); return false;".format(wp,hp)
                                        aref.set('href',href)
                                        aref.set('onClick',onClick) #TODO:HTML Generation could be modular.
                        else: # multi-image figure
                            htmlbodycontent = ""
                            for fig_name in img_names:
                                htmlbodycontent += "<img src=\"/static/html/{}\" width=\"400\" height=\"200\">".format(fig_name)
                            htmlstr = "\'<html><head></head><body>{}</body></html>\'".format(htmlbodycontent)
                            onClick = "return newWindow({},'Figure {}.{}');".format(htmlstr,chapnum,fignum)
                            aref.set('href',"javascript: void(0)")
                            aref.set('onClick',onClick)#TODO:Blend this with above

# EVH still need to code internal linking, and cleanup code
#TODO: This function looks eeriely familar to above. Unify it?
def handle_equation_labels_and_refs(tree):
    '''
    Add equation numbers to all equation and eqnarray and modify equation
    references to give correct numbers and also link that opens pop-up with
    equation on it
    '''
    popupFlag = True #EVH added
    chapnum = eqnnum = 0 # counter for equation numbering
    for chapter in tree.findall('.//chapter'):
        if chapter.get('nocount') is None:
            chapnum += 1
            eqnnum = 0  # reset counter for equation numbering
        for table in chapter.findall('.//table'):
            tabclass = table.get('class')
            if tabclass in ['equation','eqnarray']:  # handle equation
                for tr in table.findall('.//tr'):
                    eqnlabel = []
                    for td in tr.findall('.//td'):
                        if td.get('class') == 'eqnnum':
                            eqnnumcell = td
                        elif td.text is not None:
                            eqncontent = td.text
                            eqnlabel = re.findall(r'\\label\{(.*?)\}',eqncontent,re.S)
                        if len(eqnlabel) == 0:
                            eqnnumstr = ""
                        else:
                            eqnnum = eqnnum + 1 # iterate equation number
                            eqnlabel = eqnlabel[0].encode("utf-8")
                            eqnnumstr = '({}.{})'.format(chapnum,eqnnum)
                            eqncontent = eqncontent.replace('\\label{%s}' % eqnlabel,r'')
                            eqnlabel = eqnlabel.replace(' ','')
                            td.text = eqncontent
                    if not popupFlag: #EVH added, not currently used.
                        # Set id for linking if the pop-up option is off
                        eq_id = '{}{}{}'.format(eqnlabel.split(":")[0],chapnum,eqnnum)
                        tr.set('id',eq_id)

                    # now find all references to this equation and modify it to make number and link
                    # identify equation tag
                    for aref in tree.findall('.//ref'):
                        if aref.text == eqnlabel:
                            # change this ref element
                            aref.tag = 'a'
                            aref.text = '{}.{}'.format(chapnum,eqnnum)
                            if popupFlag: #TODO: Modularize HTML generation.
                                aref.set('href',"javascript: void(0)")
                                tablestr_etree = (etree.tostring(tr,encoding="utf-8",method="html")).rstrip()
                                tablestr_find = re.findall(r'\[mathjax[a-z]*\](.*?)\[/mathjax[a-z]*\]',tablestr_etree,re.S)
                                tstr = ""
                                nn = len(tablestr_find)
                                for ii in range(nn):
                                    tstr = tstr + tablestr_find[ii]
                                tablestr = re.escape('$$' + tstr + '$$')

                                if re.search(r'\\boxed',tablestr,re.S) is not None:
                                    tablestr = tablestr.replace(r'\boxed','')

                                tablestr_etree = "<table width=\"100%%\" cellspacing=\"0\" cellpadding=\"7\" style=\"table-layout:auto;border-style:hidden\"><tr><td style=\"width:80%%;vertical-align:middle;text-align:center;border-style:hidden\">%s</td><td style=\"width:20%%;vertical-align:middle;text-align:left;border-style:hidden\">(%d.%d)</td></tr></table>" % (tablestr,chapnum,eqnnum)
                                mathjax = "<script type=\"text/javascript\" src=\"https://edx-static.s3.amazonaws.com/mathjax-MathJax-727332c/MathJax.js?config=TeX-MML-AM_HTMLorMML-full\"> </script>"
                                htmlstr = "\'<html><head>%s</head><body>%s</body></html>\'" % (mathjax,tablestr_etree)
                                eqnstr = "\'Equation %s\'" % eqnnumstr
                                onClick = "return newWindow(%s,%s);" % (htmlstr,eqnstr)
                                aref.set('onClick',onClick)
                            else:
                                #EVH create internal link (placeholder)
                                aref.set('href','../courseware/chapname/secname/vertnum/#{}'.format(eq_id))

                    # replace the necessary subelements to get desired behavior
                    if tabclass == 'equation': #Only one tr element in equation table
                        tr.clear()
                        eqncell = etree.SubElement(tr,"td",attrib={'style':"width:80%;vertical-align:middle;text-align:center;border-style:hidden",'class':"equation"})
                        eqncell.text = eqncontent
                        eqnnumcell = etree.SubElement(tr,"td",attrib={'style':"width:20%;vertical-align:middle;text-align:left;border-style:hidden",'class':"eqnnum"})
                    else:
                        tr.remove(eqnnumcell)
                        eqnnumcell = etree.SubElement(tr,"td",attrib=eqnnumcell.attrib)
                    eqnnumcell.text = eqnnumstr

def fix_table(tree):
    '''
    Force tables to have table-layout: auto and hidden border lines
    '''
    for table in tree.findall('.//table'):
        table.set('style','table-layout:auto;border-style:hidden')
    '''
    Force cells to have hidden border lines
    '''
    for td in tree.findall('.//td'):
        current_style = td.get('style')
        if current_style is not None:
            new_style = current_style + ';border-style:hidden'
        else:
            new_style = 'border-style;hidden'
        td.set('style',new_style)

def fix_div(tree):
    '''
    latex minipages turn into things like <div style="width:216.81pt" class="minipage">...</div>
    but inline math inside does not render properly.  So change div to text.
    '''
    for div in tree.findall('.//div[@class="minipage"]'):
        div.tag = 'text'

def fix_center(tree):
    '''
    Force <center> to have border-style:hidden for figures within edXproblems
    '''
    for center in tree.findall('.//center'):
        center.set('style','border-style:hidden')

def add_figure_padding(tree):
    '''
    Force figures to have top and bottom padding to separate from text
    '''
    for div in tree.findall('.//div'):
        if div.get('class') == 'figure':
            padding_settings = 'padding-top:%dpx;padding-bottom:%dpx' %(5,15)
            div.set('style',padding_settings)

def process_showhide(tree):
    for showhide in tree.findall('.//edxshowhide'):
        shid = showhide.get('id')
        if shid is None:
            print "Error: edXshowhide must be given an id argument.  Aborting."
            raise Exception
        print "---> showhide %s" % shid
        #jscmd = "javascript:toggleDisplay('%s','hide','show')" % shid
        jscmd = "javascript:$('#%s').toggle()" % shid

        shtable = etree.Element('table')
        showhide.addnext(shtable)

        desc = showhide.get('description','')
        shtable.set('class',"wikitable collapsible collapsed")
        shdiv = etree.XML('<tbody><tr><th> %s [<a href="%s" id="%sl">show</a>]</th></tr></tbody>' % (desc,jscmd,shid))
        shtable.append(shdiv)

        tr = etree.SubElement(shdiv,'tr')
        tr.set('id',shid)
        tr.set('style','display:none')
        tr.append(showhide)	# move showhide to become td of table
        showhide.tag = 'td'
        showhide.attrib.pop('id')
        showhide.attrib.pop('description')

def process_include(tree):
    for include in tree.findall('.//edxinclude'):
        incfn = include.text
        if incfn is None:
            print "Error: edXinclude must specify file to include!"
            print "See xhtml source line %s" % getattr(include,'sourceline','<unavailable>')
            raise
        incfn = incfn.strip()
        try:
            incdata = open(incfn).read()
        except Exception, err:
            print "Error %s: cannot open include file %s to read" % (err,incfn)
            print "See xhtml source line %s" % getattr(include,'sourceline','<unavailable>')
            raise
        try:
            incxml = etree.fromstring(incdata)
        except Exception, err:
            print "Error %s parsing XML for include file %s" % (err,incfn)
            print "See xhtml source line %s" % getattr(include,'sourceline','<unavailable>')
            raise

        print "--> including file %s at line %s" % (incfn,getattr(include,'sourceline','<unavailable>'))
        if incxml.tag=='html' and len(incxml)>0:		# strip out outer <html> container
            for k in incxml:
                include.addprevious(k)
        else:
            include.addprevious(incxml)
        p = include.getparent()
        p.remove(include)

#-----------------------------------------------------------------------------
# usage

def usage():
    print "%s [-d directory] [-update] file.tex" % sys.argv[0]
    print "   -d directory : specifies directory in which problems or course are stored"
    print "   -update      : update the course.xml file, instead of creating it from scratch"
    print "   -imurl       : image URL prefix (eg '8.01') -- only sometimes needed, eg for stable-edx4edx branch"
    print "   -single fn   : only do single problem or HTML file creation, generating file fn"
    print "   -prefix pfx  : add this prefix in front of all html / problem filenames (for disambiguation)"
    sys.exit(0)

#-----------------------------------------------------------------------------
# main

default_dir = '.'
UPDATE_MODE = False
SINGLE_FN = ''
imdir = 'static/html'	# image directory
imurl = 'html'	# image url (may need to be class number)
fnprefix = ''	# prefix for url_name filenames

if len(sys.argv)==1:
    usage()

while sys.argv[1][0]=='-':
    if sys.argv[1]=='-d':
        default_dir = sys.argv[2]
        #imdir = '%s/%s' % (default_dir,imdir)
        sys.argv.pop(1)
        sys.argv.pop(1)
    elif sys.argv[1]=='-update':
        UPDATE_MODE = True
        sys.argv.pop(1)
    elif sys.argv[1]=='-imurl':
        imurl = sys.argv[2]
        sys.argv.pop(1)
        sys.argv.pop(1)
    elif sys.argv[1]=='-imdir':
        imdir = sys.argv[2]
        sys.argv.pop(1)
        sys.argv.pop(1)
    elif sys.argv[1]=='-single':
        SINGLE_FN = sys.argv[2]
        sys.argv.pop(1)
        sys.argv.pop(1)
    elif sys.argv[1]=='-prefix':	# fnprefix
        fnprefix = sys.argv[2]
        sys.argv.pop(1)
        sys.argv.pop(1)
    else:
        print "Unknown argument %s" % sys.argv[1]
        usage()

# input and output files
fn = sys.argv[1]
if not fn.endswith('.tex'):
    usage()
ofn = fn[:-4]+'.xhtml'

# set global variable with path of input file, relative to git repo root
def get_git_relpath(fn):
    fpath = os.path.abspath(fn)
    dir = os.path.dirname(fpath)
    while not dir=='/':
        if os.path.exists('%s/course.xml' % dir):
            break
        dir = os.path.dirname(dir)
    return fpath.replace('%s/' % dir,'')

INPUT_TEX_FILENAME = get_git_relpath(fn)

if 1:

    print "============================================================================="
    print "Converting latex to XHTML using PlasTeX with custom edX macros"
    print "Source file: %s" % INPUT_TEX_FILENAME
    print "============================================================================="

    # get the input latex file
    # latex_str = open(fn).read()
    latex_str = codecs.open(fn).read()
    latex_str = latex_str.replace('\r','\n')	# convert from mac format for EOL

    # Instantiate a TeX processor and parse the input text
    tex = TeX()
    tex.ownerDocument.config['files']['split-level'] = -100
    tex.ownerDocument.config['files']['filename'] = ofn
    tex.ownerDocument.config['general']['theme'] = 'plain'

    tex.input(latex_str)
    document = tex.parse()

    renderer = MyRenderer()
    renderer.imdir = imdir
    renderer.imurl = imurl
    renderer.imfnset = []

    renderer.render(document)

    if not SINGLE_FN:
        print "\n======================================== IMAGE FILES"
        print renderer.imfnset or "None"
        print "========================================"

#--------------------
# read XHTML file in and extract course + problems

print "============================================================================="
print "Converting XHTML into edX course and problems"
if UPDATE_MODE:
    print "--> updating course.xml file instead of creating it from scratch"
print "============================================================================="

xml = etree.parse(ofn)  # already broken by the time it gets here

process_edXmacros(xml.getroot())

if SINGLE_FN:
    print '[latex2edx] Generating just a single problem or HTML'

    for problem in xml.findall('.//problem'):
        problem_to_file(problem, default_dir, single=SINGLE_FN)

    for html in xml.findall('.//html'):
        html_to_file(html, default_dir, single=SINGLE_FN)

course = xml.find('.//course')		# top-level entry for edX course - should only be one
chapters = xml.findall('.//chapter')	# get all chapters

if course is not None:
    course_to_files(course, UPDATE_MODE, default_dir, fnprefix=fnprefix)


elif chapters and UPDATE_MODE:
    for chapter in chapters:
        update_chapter(chapter,default_dir)

else:
    print '[latex2edx] No edX course defined in the latex file!  looking for just problems and html.'

    for problem in xml.findall('.//problem'):
        problem_to_file(problem, default_dir)

    for html in xml.findall('.//html'):
        html_to_file(html, default_dir)
