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

import os, sys, string, re, urllib
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
                width = 400

            def make_image_html(fn,k):
                self.imfnset.append(fn+k)
                # if file doesn't exist in edX web directory, copy it there
                fnbase = os.path.basename(fn)+k
                wwwfn = '%s/%s' % (self.imdir,fnbase)
                #if not os.path.exists('/home/WWW' + wwwfn):
                if 1:
                    cmd = 'cp %s %s' % (fn+k,wwwfn)
                    os.system(cmd)
                    print cmd
                    os.system('chmod og+r %s' % wwwfn)
                return '<img src="/static/%s/%s" width="%d" />' % (imurl,fnbase,width)

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
            return AnswerBox(m.group(1)).xmlstr

        try:
            s = re.sub('(?s)<math>\$(.*?)\$</math>',fix_math,s)
            s = re.sub(r'(?s)<math>\\begin{equation}(.*?)\\end{equation}</math>',fix_displaymath,s)
            s = re.sub(r'(?s)<displaymath>\\begin{edXmath}(.*?)\\end{edXmath}</displaymath>',fix_displaymath,s)
            s = re.sub(r'(?s)<math>\\\[(.*?)\\\]</math>',fix_displaymath,s)
            s = re.sub(r'(?s)<abox>(.*?)</abox>',do_abox,s)
            s = re.sub('<includegraphics style="(.*?)">(.*?)</includegraphics>',do_image,s)	# includegraphics
            s = re.sub('(?s)<edxxml>\\\\edXxml{(.*?)}</edxxml>','\\1',s)

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

    psltags = ['course', 'chapter', 'section', 'sequential', 'vertical', 'problem', 'html', 'video']
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
        for sec in xml.findall('.//section'):
            sec.tag = 'sequential'
            un = sec.get('url_name','')
            if un:
                sec.set('display_name',un)
                sec.attrib.pop('url_name')

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
        html.set('source_file',INPUT_TEX_FILENAME)
        pfn, nprob = html_to_file(html,pdir,fnprefix=fnprefix)
        # nprob.set('filename',pfn)
        parent = html.getparent()		# replace html with <html ... /> course xml link
        parent.insert(parent.index(html),nprob)
        parent.remove(html)

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
    fix_div(tree)
    fix_table(tree)
    process_include(tree)
    process_showhide(tree)

def fix_table(tree):
    '''
    Force tables to have table-layout: auto 
    '''
    for table in tree.findall('.//table'):
        table.set('style','table-layout:auto')

def fix_div(tree):
    '''
    latex minipages turn into things like <div style="width:216.81pt" class="minipage">...</div>
    but inline math inside does not render properly.  So change div to text.
    '''
    for div in tree.findall('.//div[@class="minipage"]'):
        div.tag = 'text'

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

xml = etree.parse(ofn)

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
    
    
