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
            #print "[do_image] m=%s" % repr(m.groups())
            #print "DO IMAGE:"
            #print "   m.group(0)=", m.group(0)
            #print "   m.group(1)=", m.group(1)
            #print "   m.group(2)=", m.group(2)
            style = m.group(1)
            sm = re.search('width=([0-9\.]+)(.*)',style)
            if sm:
                widtype = sm.group(2)
                width = float(sm.group(1))
                if 'in' in widtype:
                    width = width * 110
                if 'extwidth' in widtype:
                    width = width * 110 * 6
                width = int(width)
                if width==0:
                    width = 400
            else:
                # CL: 16.101x -- find image size and make percentage be multiple of width in pixels
                #print "Image m:", m
                #print "   m.group(0):", m.group(0)
                #print "   m.group(1):", m.group(1)
                #print "   m.group(2):", m.group(2)
                path_to_image = m.group(2)
                img = Image.open(path_to_image + ".png")
                w, h = img.size
                #print path_to_image
                #print "w =", w
                #print "h =", h
                width = w/18  # using this as percentage for width and height below

            def make_image_html(fn,k):
                self.imfnset.append(fn+k)
                # if file doesn't exist in edX web directory, copy it there
                fnbase = os.path.basename(fn)+k
                wwwfn = '%s/%s' % (self.imdir,fnbase)
                #print "wwwfn =", wwwfn
                #wwwfn = re.sub(r'(?s).png(?s)','.svg',wwwfn)
                #print "wwwfn =", wwwfn
                #if not os.path.exists('/home/WWW' + wwwfn):
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
            print "\nDOING abox!!\n"
            if m.group(1).find('type="justification"') >= 0: # justification response
                print m.group(1)
                print "Justification response box being processed..."
                return '</p><p><textarea rows="5" style="width:600px;height:100px"></textarea>'
            else: # handle like normal abox
                return AnswerBox(m.group(1)).xmlstr

        def do_iframe(m):
            #print "inside iframe"
            #print m
            #print m.group(0)
            #attributes = re.findall('\>(.*?)\<',m.group(0),re.S)
            #print attributes[0].encode("utf-8")
            #print "<iframe %s></iframe>" % attributes[0].encode("utf-8")
            print m.group(0).encode("utf-8")
            #raw_input("Press ENTER inside do_iframe")
            return m.group(0).encode("utf-8")

        def do_figure_ref(m):
            print "inside figure_ref"
            print m
            print m.group(0)
            # raw_input("Press Enter to continue...")
            figure_name = re.findall('fig:(.*?)\"',m.group(0),re.S)
            figure_name = figure_name[0].encode("utf-8")
            figure_number = re.findall('\>(.*?)\<',m.group(0),re.S)
            figure_number = figure_number[0].encode("utf-8")
            print figure_name
            print figure_number
            new_window_command = "<a href=\"/static/html/%s.png\" onClick=\"window.open(this.href,\'16.101x\',\'toolbar=1\'); return false;\">%s</a>" % (figure_name,figure_number)
            print new_window_command
            return new_window_command

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
            #imgtext = '<imageinput src="/static/%s/%s" width="%s" height="%s" rectangle="%s"/>' % (imurl,fnbase,width,height,rectangle)
            #print "imgtext=",imgtext
            #raw_input("Press ENTER")
            return '<imageinput src="/static/%s/%s" width="%s" height="%s" rectangle="%s"/>' % (imurl,fnbase,width,height,rectangle)

        try:
            s = re.sub('(?s)<math>\$(.*?)\$</math>',fix_math,s)
            s = re.sub(r'(?s)<math>\\begin{equation}(.*?)\\end{equation}</math>',fix_displaymath,s)
            s = re.sub(r'(?s)<displaymath>\\begin{edXmath}(.*?)\\end{edXmath}</displaymath>',fix_displaymath,s)
            s = re.sub(r'(?s)<math>\\\[(.*?)\\\]</math>',fix_displaymath,s)
            s = re.sub('<includegraphics style="(.*?)">(.*?)</includegraphics>',do_image,s)	# includegraphics
            
            s = re.sub('(?s)<edxxml>\\\\edXxml{(.*?)}</edxxml>','\\1',s)
            s = re.sub(r'(?s)<iframe(.*?)></iframe>',do_iframe,s)  # edXinlinevideo

            # check 1
            fff = open('check1.txt','w')
            fff.write(s.encode('utf-8'))
            fff.close()
            # still good here

            s = re.sub(r'(?s)<customresponse(.*?)cfn="defaultsoln"(.*?)</customresponse>','<customresponse cfn="defaultsoln" expect=""><textline size="90" correct_answer=""/></customresponse>',s)

            s = re.sub(r'(?s)<abox>(.*?)</abox>',do_abox,s) # THIS MUST COME AFTER CUSTOMRESPONSE HANDLING!!!

            # MISSING CONTENT!
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
    while s in URLNAMES:
        s += 'x'
    URLNAMES.append(s)
    return s

#-----------------------------------------------------------------------------
# output problem into XML file

def content_to_file(content, tagname, fnsuffix, pdir='.', single='', fnprefix=''):
    pname = content.get('url_name','noname')
    pfn = make_urlname(pname)
    pfn = fnprefix + pfn
    print "  %s '%s' --> %s/%s.%s" % (tagname,pname,pdir,pfn,fnsuffix)

    #set default attributes for problems
    if tagname=='problem':
        content.set('showanswer','closed')
        content.set('rerandomize','never')

    # set display_name (will be overwritten below if it is specified in attrib_string)
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

    psltags = ['course', 'chapter', 'section', 'sequential', 'vertical', 'problem', 'html', 'video', 'iframe']
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
        secnum = 1
        for sec in xml.findall('.//section'):
            sec.tag = 'sequential'
            un = sec.get('url_name','')
            if un:
                sec.set('display_name',un)
                sec.set('url_name',make_urlname(un+str(secnum)))
            secnum = secnum + 1

    # move contents of video elements into attrib
    for video in xml.findall('.//video'):
        print "*** video.text = %s" % video.text
        try:
            chk = etree.XML('<video %s/>' % video.text)
        except Exception, err:
            print "[latex2edx] Oops, badly formatted video tag attributes: '%s'" % video.text
            sys.exit(-1)
        video.addprevious(chk)
        video.getparent().remove(video)
        print "  video element: %s" % etree.tostring(chk)

#    # move contents of iframe elements into attrib
#    for iframe in xml.findall('.//iframe'):
#        print "*** iframe.text = %s" % iframe.text
#        try:
#            chk = etree.XML('<iframe %s/>' % iframe.text)
#        except Exception, err:
#            print "[latex2edx] Oops, badly formatted iframe tag attributes: '%s'" % iframe.text
#            sys.exit(-1)
#        iframe.addprevious(chk)
#        iframe.getparent().remove(iframe)
#        print "  iframe element: %s" % etree.tostring(chk)

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
    #pdir = '%s/problems' % cdir
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
        if name=="Overview of 16.101x" or name=="Test":
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
        if modtotCQweight != 50:
            print "\n *** WARNING *** Module: %s, Concept Question weights sum to %d != 50!!!\n" % (name, modtotCQweight)
            raw_input("Press ENTER to continue")
        if modtotHWweight != 50:
            print "\n *** WARNING *** Module: %s, Homework Question weights sum to %d != 50!!!\n" % (name, modtotHWweight)
            raw_input("Press ENTER to continue")
    f.close()


#-----------------------------------------------------------------------------
# output course into XML file

def course_to_files(course, update_mode, default_dir, fnprefix=''):
    
    cnumber = course.get('number')	# course number, like 18.06x
    print "Course number: %s" % cnumber
    cdir = cnumber

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
    handle_measurable_outcomes(tree)
    add_figure_padding(tree)
    process_include(tree)
    process_showhide(tree)
    fix_boxed_equations(tree)  # note this should come after fix_table always
    handle_section_refs(tree)
    add_titles_to_edxtext(tree)
    #ensure_https_for_youtube_embeds(tree)
    #fix_edXvideos_in_solutions(tree)   # this line currently breaks the normal video handling --- only bring back if we will be able to use <video> tags in solutions and replace all the iframe videos

def ensure_https_for_youtube_embeds(tree):
    '''
    Make sure links for youtube embeds are https, not http
    '''
    for iframe in tree.findall('.//iframe'):
        print "found iframe"
        iframe_src = iframe.get('src')
        if iframe_src[:5] != "https":
            iframe_src = iframe_src[:4] + "s" + iframe_src[4:]
        print "iframe_src: ", iframe_src
        iframe.set('src',iframe_src)

def add_chapter_url_names(tree):
    '''
    Add chapter url_name so we can reference them in policy file
    '''
    for chapter in tree.findall('.//chapter'):
        display_name = chapter.get('display_name')
        url_name = make_urlname(display_name)
        chapter.set('url_name',url_name)
        print "\n\n CHAPTER URL: %s \n" % url_name
        raw_input('Press ENTER')

def fix_edXvideos_in_solutions(tree):
    '''
    The edXvideos placed inside solutions within problem need to be reformatted
    '''
    for problem in tree.findall('.//problem'):
        for text in problem.findall('.//text'):
            for p1 in text.findall('.//p'):
                for solution in p1.findall('.//solution'):
                    for font in solution.findall('.//font'):
                        for p2 in font.findall('.//p'):
                            for video in p2.findall('.//video'):
                                video_inner_text = video.text
                                m = re.search('display_name=\"(.+?)\"',video_inner_text)
                                if m:
                                    viddn = m.group(1)
                                else:
                                    viddn = ""
                                m = re.search('youtube=\"(.+?)\"',video_inner_text)
                                if m:
                                    vidyt = m.group(1)
                                else:
                                    print "\n\n"
                                    print video_inner_text
                                    print "\n*** WARNING *** Youtube code not specified for video in solution"
                                    raw_input("Press ENTER to continue...")
                                print solution
                                print solution.text
                                print p2.text
                                solution_text = etree.XML('<video display_name="%s" youtube="%s"/>' % (viddn,vidyt))
                                soltextelem = solution.insert(0,solution_text)
                                #solution.text = r'<video display_name="%s" youtube="%s"/>' % (viddn,vidyt)
                                #solution.text = solution.text.replace("&lt;", "<")
                                #solution.text = solution.text.replace("&gt;", ">")
                                print "solution text = ", solution.text
                        solution.remove(font);


def add_titles_to_edxtext(tree):
    '''
    Add the titles as <h2 class="problem-header">?</h2> elements to each edXtext section
    '''
    for html in tree.findall('.//html'):
        disp_name = html.get('url_name')
        # print disp_name
        header_sub_element = etree.Element('h2',{'class':"problem-header"})
        header_sub_element.text = disp_name
        html.insert(0, header_sub_element)
        # raw_input("Press ENTER")

def handle_measurable_outcomes(tree):
    '''
    Process the labels and references to measurable outcomes, placing 'tags' at the top of the vertical that have mouseovers revealing the measurable outcome
    '''
    chapternum = 0
    print "inside HANDLE_MEASURABLE_OUTCOMES"
    #raw_input("Press ENTER")
    for chapter in tree.findall('.//chapter'):
        chapternum += 1
        for section in chapter.findall('.//section'):
            if section.get('url_name')=="Overview":
                for html in section.findall('.//html'):
                    if html.get('url_name')=="Measurable outcomes":
                        print "Found MEASURABLE OUTCOMES section"
                        for ol in html.findall('.//ol'): # ordered list of measurable outcomes
                            ol.tag = 'ul'
                            monum = 0
                            for li in ol.findall('.//li'): # items
                                monum += 1
                                for p in li.findall('.//p'): # paragraph
                                    print "p.text =", p.text
                                    m = re.search('\(label-mo:(.*?)\)',p.text)
                                    tag = m.group(1)
                                    oldtext = p.text
                                    oldtext = re.sub(r'\(label-mo:(.*?)\)',r'',oldtext)
                                    newtext = "MO%d.%d: " % (chapternum,monum) + oldtext
                                    p.text = newtext
                                    # find the references to this everywhere else (will be in html or problem OR vertical)
                                    print "Finding reference to " + newtext + "..."
                                    #raw_input("Press ENTER")
                                    for html in tree.findall('.//html'): #look in html
                                        for p in html.findall('.//p'):
                                            for a in p.findall('.//a'):
                                                if a.text=="mo:"+tag:
                                                    print "a.text =", a.text
                                                    print "Found an <a> with mo: tag"
                                                    #raw_input("Press ENTER")
                                                    # we need to distinguish here between relmo calls and places where the outcome is referenced in the text (look for the word "outcome", any case) in the preceding text  
                                                    print "\n", p.text
                                                    if p.text.lower().find(r'outcome')>0 and p.text.find(r'<a>mo'):
                                                        p.text = p.text + "%d.%d" % (chapternum,monum)
                                                        print p.text
                                                        p.remove(a)
                                                        continue # i.e. don't go below to where we do the tagging
                                                    p.remove(a)
                                                    # put tag at the bottom of the html section
                                                    # determine if a taglist paragraph exists yet
                                                    taglist_exists = False
                                                    for p in html.findall('.//p'):
                                                        if p.get('id')=="taglist":
                                                            taglist_exists = True
                                                    if not taglist_exists: # tag list element doesn't exist yet
                                                        print "Taglist being created..."
                                                        #raw_input("Press ENTER")
                                                        taglist = etree.Element("p",{'id':"taglist"})
                                                        html.insert(0,taglist)
                                                        # taglist = etree.SubElement(html,"ul",{'id':"taglist",'display':"block",'list-style':"none",'overflow':"hidden"})
                                                    else: # taglist element already exists
                                                        # find it and get it by the name taglist
                                                        for p in html.findall('.//p'):
                                                            if p.get('id')=="taglist":
                                                                taglist = p
                                                                break
                                                    link = etree.SubElement(taglist,"button",{'type':"button",'disabled':"disabled",'border-radius':"2px",'title':"%s" % newtext,'style':"cursor:pointer",'class':"mo_button"}) # add the link inside
                                                    link.text = "MO%d.%d" % (chapternum,monum)  
                                                    link.set('id',tag)
                                    for problem in tree.findall('.//problem'): #look in problem
                                        for p in problem.findall('.//p'):
                                            for a in p.findall('.//a'):
                                                if a.text=="mo:"+tag:
                                                    # add measurable outcome attribute to the xml tag
                                                    if problem.get('measurable_outcomes') is not None:
                                                        # add it and reset (comma-separated list, no space per P. Pinch)
                                                        currmo = problem.get('measurable_outcomes') 
                                                        newmo = currmo + ",%s" % tag
                                                        problem.set('measurable_outcomes',newmo)
                                                    else:
                                                        problem.set('measurable_outcomes',tag)
                                                    p.remove(a)
                                                    # put tag at the bottom of the html section
                                                    # determine if a taglist paragraph exists yet
                                                    taglist_exists = False
                                                    for p in problem.findall('.//p'):
                                                        if p.get('id')=="taglist":
                                                            taglist_exists = True
                                                    if not taglist_exists: # tag list element doesn't exist yet
                                                        taglist = etree.Element("p",{'id':"taglist"})
                                                        problem.insert(0,taglist)
                                                    else: # taglist element already exists
                                                        # find it and get it by the name taglist
                                                        for p in problem.findall('.//p'):
                                                            if p.get('id')=="taglist":
                                                                taglist = p
                                                                break
                                                    link = etree.SubElement(taglist,"button",{'type':"button",'disabled':"disabled",'border-radius':"2px",'title':"%s" % newtext,'style':"cursor:pointer",'class':"mo_button"}) # add the link inside
                                                    link.text = "MO%d.%d" % (chapternum,monum)  
                                                    link.set('id',tag)
                                    for vertical in tree.findall('.//vertical'): # look in vertical
                                        print "\nVERTICAL %s" % vertical.get('display_name')
                                        for p in vertical.findall('.//p'):
                                            # print "p.text=",p.text
                                            for a in p.findall('.//a'):
                                                #print "a.text =",a.text 
                                                if a.text=="mo:"+tag:
                                                # found MO tag in vertical.
                                                    # need to put these tags in the measurable_outcomes attribute of problems in this vertical (for Cole's reporting tool)
                                                    # assume here that verticals encapsulate only problems !!!
                                                    # get first problem
                                                    
                                                    #print "\nPROCESSING TAG mo:%s\n" % tag
                                                    #raw_input("Press ENTER")
                                                    for problem in vertical.findall('.//problem'):
                                                        firstproblem = problem
                                                        break
                                                    # set measurable_outcome attribute for all problems
                                                    for problem in vertical.findall('.//problem'):
                                                        # add measurable outcome attribute to the xml tag
                                                        if problem.get('measurable_outcomes') is not None:
                                                            # add it and reset (comma-separated list, no space per P. Pinch)
                                                            currmo = problem.get('measurable_outcomes') 
                                                            newmo = currmo + ",%s" % tag
                                                            problem.set('measurable_outcomes',newmo)
                                                        else:
                                                            problem.set('measurable_outcomes',tag)
                                                    p.remove(a)
                                                    # check if this p should be removed (the last a was just taken out)
                                                    totalaswithmos = 0
                                                    for a in p.findall('.//a'):
                                                        print "a.text =",a.text
                                                        if a.text.find('mo:')!=-1:
                                                            totalaswithmos += 1
                                                    print "TOTAL MOs remaining in this <p> =", totalaswithmos
                                                    if totalaswithmos==0:
                                                        vertical.remove(p)
                                                    taglist_exists = False
                                                    for pt in firstproblem.findall('.//p'):
                                                        if pt.get('id')=="taglist":
                                                            taglist_exists = True
                                                    if not taglist_exists: # tag list element doesn't exist yet
                                                        taglist = etree.Element("p",{'id':"taglist"})
                                                        firstproblem.insert(0,taglist)
                                                    else: # taglist element already exists
                                                        # find it and get it by the name taglist
                                                        for pt in firstproblem.findall('.//p'):
                                                            if pt.get('id')=="taglist":
                                                                taglist = pt
                                                                break
                                                    link = etree.SubElement(taglist,"button",{'type':"button",'disabled':"disabled",'border-radius':"2px",'title':"%s" % newtext,'style':"cursor:pointer",'class':"mo_button"}) # add the link inside
                                                    link.text = "MO%d.%d" % (chapternum,monum)  
                                                    link.set('id',tag)
                                        
        # find a measurable outcome (do by Chapter, like MO1.2, MO3.5 etc.)
        # look through the rest of the document for references to that measurable outcome
        # where there is a reference to the MO, make a tag at the bottom of that vertical that says "MO1.2" or whatever, but that permits a hover that brings up the full-length description of the measurable outcome

def handle_section_refs(tree):
    '''
    Process references to sections of content -- create section numbering and the reference should be a link that opens in a new tab to the desired component
    '''
    # For the purposes of this function, I will think of "chapter" (e.g., Differential Forms of Compressible Flow Equations) --- what we call Modules --- and then "section" (e.g., Kinematics of a Fluid Element), followed by "subsection" to refer to the component level (e.g., Normal Strain)
    pathtocourseware = "/courses/MITx/16.101x/2013_SOND"
    chapternum = 0
    for chapter in tree.findall('.//chapter'):
        chapternum = chapternum + 1
        # look for chapter label
        chaplabel = ""
        for p in chapter.findall('.//p'):
            if not any(p==chapterchild for chapterchild in list(chapter)):
                continue
            if re.search(r'(?s)sec:(.*?)(?s)',p.text) is not None: # found label sec:?
                tmp = (re.search(r'sec:(.*?) ',p.text))
                chaplabel = (tmp.group(0)).rstrip()
                print chaplabel
                chapter.remove(p)
                chapname = chapter.get('display_name')
                chapnamewithunderscores = re.sub(r' ',r'_',chapname)
                for section in chapter.findall('.//section'):
                    firstsectioninchap = section
                    firstsectionurlname = section.get('url_name')
                    break #only the first one needed
                globalsecnum = 0
                for section2 in tree.findall('.//section'):
                    globalsecnum = globalsecnum + 1
                    if section2 is firstsectioninchap:
                        break
                break  # chapter is only permitted to have one label so don't keep going through other paragraphs
        # end look for chapter label
        # now find and replace this everywhere else with the correct number (and make it a link)
        if chaplabel != "":
            for a in tree.findall('.//a'):
                if a.text == chaplabel:
                    a.text = '%d' % chapternum
                    # chapters actually don't contain any content themselves (clicking chapter in the menu just changes display --- no url)
                    # instead, take the user to the first section and first subsection of the chapter
                    href = "%s/courseware/%s" % (pathtocourseware,chapnamewithunderscores)
                    # href = "%s/courseware/%s/%s%d" % (pathtocourseware,chapnamewithunderscores,firstsectionurlname,globalsecnum)
                    print "href =",href
                    # raw_input("Press ENTER")
                    a.set('href',href)
                    a.set('target',"_blank")
            # end look for chapter references            
        sectionnum = 0
        for section in chapter.findall('.//section'):
            sectionnum = sectionnum + 1
            # look for section label
            seclabel = ""
            for p in section.findall('.//p'):
                if not any(p==sectionchild for sectionchild in list(section)):
                    continue
                if re.search(r'(?s)sec:(.*?)(?s)',p.text) is not None: # found label sec:?
                    tmp = (re.search(r'sec:(.*?) ',p.text))
                    seclabel = (tmp.group(0)).rstrip()
                    print seclabel
                    print list(section)
                    print p
                    # raw_input("Press ENTER")
                    # WORKING HERE
                    section.remove(p)
                    chapname = chapter.get('display_name')
                    chapnamewithunderscores = re.sub(r' ',r'_',chapname)
                    sectionurlname = section.get('url_name')
                    globalsecnum = 0
                    for section2 in tree.findall('.//section'):
                        globalsecnum = globalsecnum + 1
                        if section2 is section:
                            break
                    break  # section is only permitted to have one label so don't keep going through other paragraphs
            # end look for section label
            # now find and replace this everywhere else with the correct number (and make it a link)
            if seclabel != "":
                for a in tree.findall('.//a'):
                    if a.text == seclabel:
                        a.text = '%d.%d' % (chapternum,sectionnum)
                        # chapters actually don't contain any content themselves (clicking chapter in the menu just changes display --- no url)
                        # instead, take the user to the first section and first subsection of the chapter
                        sectionurlname = re.sub(r' ',r'_',sectionurlname)
                        href = "%s/courseware/%s/%s%d/1/" % (pathtocourseware,chapnamewithunderscores,sectionurlname,globalsecnum)
                        # href = "%s/courseware/%s/%s%d" % (pathtocourseware,chapnamewithunderscores,firstsectionurlname,globalsecnum)
                        print "href =",href
                        # raw_input("Press ENTER")
                        a.set('href',href)
                        a.set('target',"_blank")
                # end look for section references  
            subsectionnum = 0
           
            #for subsection in section.findall('.//problem'):
            #for subsection in section.findall('.//html' or './/problem'):  # here we do list (go through children) because children are either of 'html' or 'problem' type
            for subsection in section.findall(".//"):
                # debugging...
                #print "section type=",section.tag
                #print "section name=",section.get('url_name')
                #print "subsection type=",subsection.tag       
                if (subsection.tag == "problem" or subsection.tag == "html") and subsection.get('url_name') is not None:
                    print "PROBLEM OR HTML COMPONENT TYPE!!!"         
                    subsectionnum = subsectionnum + 1
                    # raw_input("Press ENTER")
                    # look for subsection label
                    subseclabel = ""
                    for p in subsection.findall('.//'):
                        #if not any(p==subsectionchild for subsectionchild in list(subsection)):
                        #    continue
                        print "p text =", p.text
                        if p.text is not None and p.tag == "p" and re.search(r'(?s)sec:(.*?)(?s)',p.text) is not None: # found label sec:?
                            print "section type=",section.tag
                            print "section name=",section.get('url_name')
                            print "subsection type=",subsection.tag   
                            print "subsection name=",subsection.get('url_name')
                            print "P TEXT =", p.text
                            tmp = (re.search(r'sec:(.*?) ',p.text))
                            subseclabel = (tmp.group(0)).rstrip()
                            print subseclabel
                            #raw_input("SUBSECTION LABEL")
                            pparent = p.getparent()
                            pparent.remove(p)
                            chapname = chapter.get('display_name')
                            chapnamewithunderscores = re.sub(r' ',r'_',chapname)
                            sectionurlname = section.get('url_name')
                            globalsecnum = 0
                            for section2 in tree.findall('.//section'):
                                globalsecnum = globalsecnum + 1
                                if section2 is section:
                                    break
                            break  # subsection is only permitted to have one label so don't keep going through other paragraphs

                        # end look for subsection label
                        # now find and replace this everywhere else with the correct number (and make it a link)
                    print "HERE: subseclabel =",subseclabel
                    if subseclabel != "":
                        for a in tree.findall('.//a'):
                            if a.text == subseclabel:
                                a.text = '%d.%d.%d' % (chapternum,sectionnum,subsectionnum)
                                # chapters actually don't contain any content themselves (clicking chapter in the menu just changes display --- no url)
                                # instead, take the user to the first section and first subsection of the chapter
                                sectionurlname = re.sub(r' ',r'_',sectionurlname)
                                href = "%s/courseware/%s/%s%d/%d/" % (pathtocourseware,chapnamewithunderscores,sectionurlname,globalsecnum,subsectionnum)
                                # href = "%s/courseware/%s/%s%d" % (pathtocourseware,chapnamewithunderscores,firstsectionurlname,globalsecnum)
                                print "href =",href
                                # raw_input("Press ENTER")
                                a.set('href',href)
                                a.set('target',"_blank")
                                #raw_input("FOUND REFERENCE TO %s" % subseclabel)
                            # end look for subsection references 
                
    # once all of the labels have been found... need to go through and do something about the references that do not have associated labels
    # issue warning that requires user to press enter to continue
    for a in tree.findall('.//a'):
        print "\na.text =", a.text
        if a.text is None:
            break
        if re.search(r'(?s)sec:(.*?)(?s)',a.text) is not None:
            print "WARNING: There is a reference to non-existent label %s" % a.text
            raw_input("Press ENTER to continue")

def fix_boxed_equations(tree):
    '''
    Fix boxed equations: move boxed command outside of mathjax and instead modify the style of the cell containing the equation
    '''
    boxedFlag = False
    for table in tree.findall('.//table'):
        for tr in table.findall('.//tr'):
            for td in tr.findall('.//td'):
                boxedflag = False
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
    modulenum = 0
    for chapter in tree.findall('.//chapter'):
        modulenum = modulenum + 1
        fignum = 0
        for div in chapter.findall('.//div'):
            print "CHAPTER: %s" % chapter.get('display_name')
            print "div information:"
            print "  div class: %s" % div.get('class')
            print "  div id: %s" % div.get('id')
            #raw_input("Press ENTER")
            if div.get('class') == "figure":
                print "\n\n"
                figlabel = div.get('id')
                if figlabel == "fig:aeroforces":
                    print "FOUND AEROFORCES FIG"
                    print figlabel
                    #raw_input("Press ENTER")
                if figlabel is None:
                    print "No label for this figure."
                    #raw_input("Press ENTER to continue.")
                    continue
                print figlabel
                #raw_input("Press ENTER")
                # get fignum
                for b in div.findall('.//b'):
                    if re.search(r'Figure [0-9]+$',b.text,re.S) is not None:
                        splitres = b.text.split()
                        #fignum = int(splitres[1])
                        fignum += 1
                        b.text = "Figure %d.%d" % (modulenum,fignum)
                # for multi-image figures, i need to collect all the image names
                image_names = []
                for img in div.findall('.//img'):
                    img_src = img.get('src')
                    print img_src
                    m = re.search(r'/static/html/(.*?).png',img_src,re.S)
                    this_name = m.group(1)
                    image_names.append(this_name)
                    #print "\n\nadded %s.png to image_names list" % this_name
                    #raw_input("Press ENTER")
                # look for references and put the right code
                for a in tree.findall('.//a'):
                    print "looking for the reference %s ..." % figlabel
                    print "a.text =", a.text
                    if a.text == figlabel:
                        print "found reference"
                        #raw_input("Press ENTER")
                        # change this ref element
                        a.text = "%d.%d" % (modulenum,fignum)
                        if len(image_names)==1:  # single image figure
                            print "\nfiglabel =", figlabel
                            figure_info = figlabel.split(":")
                            figure_name = figure_info[1]
                            # find the image within directory of modules.tex (the tex file this is being run on)
                            ##print INPUT_TEX_FILENAME
                            latexfolder = os.getcwd()
                            imgpath = ""
                            for path, dirs, files in os.walk(latexfolder):
                                for filename in fnmatch.filter(files,figure_name+".png"):
                                    imgpath = os.path.join(path, filename)
                                    if imgpath.find('figs') != -1:
                                        #print "FOUND figs IN PATH"
                                        fullimgpath = imgpath
                            #print fullimgpath
                            img = Image.open(fullimgpath)
                            w, h = img.size
                            #print "w =", w
                            ws = 0.50
                            wp = (int)(w*ws)
                            #wp = w
                            #hp = h
                            hp = (int)(h*ws)
                            href = "/static/html/%s.png" % figure_name
                            onClick = "window.open(this.href,\'16.101x\',\'width=%s,height=%s\',\'toolbar=1\'); return false;" % (wp,hp)
                            a.set('href',href)
                            a.set('onClick',onClick)
                        else: # multi-image figure
                            htmlbodycontent = ""
                            for figure_name in image_names:
                                htmlbodycontent += "<img src=\"/static/html/%s.png\" width=\"400\" height=\"200\">" % figure_name
                            htmlstr = "\'<html><head></head><body>%s</body></html>\'" % htmlbodycontent
                            print htmlstr
                            #raw_input("CHECK OUT THIS HTML STRING")
                            onClick = "return newWindow(%s,'Figure %d.%d');" % (htmlstr,modulenum,fignum)
                            a.set('href',"javascript: void(0)")
                            a.set('onClick',onClick)

def handle_equation_labels_and_refs(tree):
    ''' 
    Add equation numbers to all equation and eqnarray and modify equation references to give correct numbers and also link that opens pop-up with equation on it
    '''
    modulenum = 0
    for chapter in tree.findall('.//chapter'):
        modulenum = modulenum + 1
        eqnnum = 1  # counter for equation numbering
        for table in chapter.findall('.//table'):
            if table.get('class') == 'equation':  # handle equation
                for tr in table.findall('.//tr'):
                    for td in tr.findall('.//td'):
                        if td.get('class') == 'equation':
                            eqncontent = td.text   #equation content
                    # tr is this element's parent
                    tr.clear()     
                    # add the necessary subelements to get desired behavior
                    eqncell = etree.SubElement(tr,"td",attrib={'style':"width:80%;vertical-align:middle;text-align:center;border-style:hidden",'class':"equation"})
                    eqncell.text = eqncontent
                    eqnnumcell = etree.SubElement(tr,"td",attrib={'style':"width:20%;vertical-align:middle;text-align:left;border-style:hidden",'class':"eqnnum"})
                    eqnnumcell.text = "(%d.%d)" % (modulenum,eqnnum)
                                       
                    # now find all references to this equation and modify it to make number and link
                    # identify equation tag
                    if re.search(r'\\label\{(.*?)\}',eqncontent) is not None:  # equation has a label so it is probably referenced somewhere       
                        eqnlabelfind = re.findall(r'\\label\{(.*?)\}',eqncontent,re.S)   
                        eqnlabel = eqnlabelfind[0].encode("utf-8")   
                        eqnlabel = "".join(eqnlabel.split())
                        for a in tree.findall('.//a'):
                            # print "looking for the reference..."
                            if a.text == eqnlabel:
                                # change this ref element
                                a.text = "%d.%d" % (modulenum,eqnnum)
                                a.set('href',"javascript: void(0)")
                                eqnstr = "\'Equation (%d.%d)\'" % (modulenum,eqnnum)
                                tablestr_etree = (etree.tostring(table,encoding="utf-8",method="html")).rstrip()
                                #print "etree to string =", tablestr_etree
                                tablestr_find = re.search(r'\[mathjax\](.*?)\[/mathjax\]',tablestr_etree,re.S)
                                tablestr = re.escape('$$' + tablestr_find.group(1).encode("US-ASCII") + '$$') 

                                if re.search(r'\\boxed',tablestr,re.S) is not None:
                                    tablestr = tablestr.replace(r'\boxed','')
        
                                tablestr_etree = "<table width=\"100%%\" cellspacing=\"0\" cellpadding=\"7\" style=\"table-layout:auto;border-style:hidden\"><tr><td style=\"width:80%%;vertical-align:middle;text-align:center;border-style:hidden\">%s</td><td style=\"width:20%%;vertical-align:middle;text-align:left;border-style:hidden\">(%d.%d)</td></tr></table>" % (tablestr,modulenum,eqnnum)                  
                                #print "tablestr_etree =", tablestr_etree
                                mathjax = "<script type=\"text/javascript\" src=\"https://c328740.ssl.cf1.rackcdn.com/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML\"> </script>"
                                htmlstr = "\'<html><head>%s</head><body>%s</body></html>\'" % (mathjax,tablestr_etree)
                                onClick = "return newWindow(%s,%s);" % (htmlstr,eqnstr)
                                a.set('onClick',onClick)

                    eqnnum = eqnnum + 1 # iterate equation number          

            if table.get('class') == 'eqnarray':  # handle eqnarray
                for tr in table.findall('.//tr'):
                    for td in tr.findall('.//td'):
                        if td.get('class') == "eqnnum":
                            eqnnumcell = td
                       
                        if td.text is not None and re.search(r'\\label\{(.*?)\}',td.text,re.S) is not None:
                            eqnlabelfind = re.findall(r'\\label\{(.*?)\}',td.text,re.S)   
                            eqnlabel = eqnlabelfind[0].encode("utf-8")   
                            eqnlabel = "".join(eqnlabel.split())
                            for a in tree.findall('.//a'):
                                # print "looking for the reference..."
                                if a.text == eqnlabel:
                                    # change this ref element
                                    # change this ref element
                                    a.text = "%d.%d" % (modulenum,eqnnum)
                                    a.set('href',"javascript: void(0)")
                                    eqnstr = "\'Equation (%d.%d)\'" % (modulenum,eqnnum)
                                    tablestr_etree = (etree.tostring(tr,encoding="utf-8",method="html")).rstrip()
                                    #print "etree to string =", tablestr_etree
                                    tablestr_find = re.findall(r'\[mathjaxinline\](.*?)\[/mathjaxinline\]',tablestr_etree,re.S)
                                    #print tablestr_find
                                    #print "group 0:", tablestr_find.group(0)
                                    #print "group 1:", tablestr_find.group(1)
                                    #print "group 2:", tablestr_find.group(2)
                                    print "\n\ntablestr_find =", tablestr_find
                                    tstr = ""
                                    nn = len(tablestr_find)
                                    for ii in range(nn):
                                        tstr = tstr + tablestr_find[ii]
                                    tablestr = re.escape('$$' + tstr + '$$') 
                                    #print tablestr
                                    if re.search(r'\\boxed',tablestr,re.S) is not None:
                                        tablestr = tablestr.replace(r'\boxed','')
                                    tablestr = tablestr.replace(r',','')
                                    tablestr_etree = "<table width=\"100%%\" cellspacing=\"0\" cellpadding=\"7\" style=\"table-layout:auto;border-style:hidden\"><tr><td style=\"width:80%%;vertical-align:middle;text-align:center;border-style:hidden\">%s</td><td style=\"width:20%%;vertical-align:middle;text-align:left;border-style:hidden\">(%d.%d)</td></tr></table>" % (tablestr,modulenum,eqnnum)                  
                                    #print "tablestr_etree =", tablestr_etree
                                    mathjax = "<script type=\"text/javascript\" src=\"https://c328740.ssl.cf1.rackcdn.com/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML\"> </script>"
                                    htmlstr = "\'<html><head>%s</head><body>%s</body></html>\'" % (mathjax,tablestr_etree)
                                    onClick = "return newWindow(%s,%s);" % (htmlstr,eqnstr)
                                    a.set('onClick',onClick)
                    tr.remove(eqnnumcell)
                    eqnnumcell = etree.SubElement(tr,"td",attrib=eqnnumcell.attrib)
                    eqnnumcell.text = "(%d.%d)" % (modulenum,eqnnum)
                    eqnnum = eqnnum + 1  # have to iterate inside of eqnarray as well

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

    # open all tex files that are sub to the main file and replace \item\label{mo:*}
    fpath = os.path.abspath(fn)
    dir = os.path.dirname(fpath)
    for path, subdirs, files in os.walk(dir):
        for name in files:
            if name.endswith('.tex'):
                print os.path.join(path, name)
                # open the file
                f = open(os.path.join(path, name),'r')
                fsrc = f.read()
                # do the replace
                print fsrc[1:1500]
                fsrc = re.sub(r'(\\item\\label\{mo:)(.*)(\})',r'\item (label-mo:\2)',fsrc)
                print fsrc[1:1500]
                f.close()
                # write the file
                f = open(os.path.join(path, name),'w')
                f.write(fsrc)
                f.close()   

    # get the input latex file
    # latex_str = open(fn).read()
    latex_str = codecs.open(fn).read()
    latex_str = latex_str.replace('\r','\n')	# convert from mac format for EOL
    
    print latex_str[-500:]
    raw_input('Press ENTER')

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

