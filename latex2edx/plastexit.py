import sys
import os
import re
import codecs
from logging import CRITICAL, DEBUG, INFO 
try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict
    
from plasTeX.Renderers import XHTML
from plasTeX.TeX import TeX
from plasTeX.Renderers.PageTemplate import Renderer as _Renderer
from plasTeX.Config import config as plasTeXconfig
from xml.sax.saxutils import escape, unescape
from .abox import AnswerBox, split_args_with_quoted_strings
from io import StringIO

class MyRenderer(XHTML.Renderer):
    """
    PlasTeX class for rendering the latex document into XHTML + edX tags
    """
    def __init__(self, imdir='', imurl='', extra_filters=None):
        '''
        imdir = directory where images should be stored
        imurl = url base for web base location of images
        '''
        XHTML.Renderer.__init__(self)
        self.imdir = imdir
        self.imurl = imurl
        self.imfnset = []
        self.answer_box_objects = {}	# tracks AnswerBox objects, using their xmlstr repr as keys
        self.abox_config = {}	# used by AnswerBox to store state, like default config parameters

        # setup filters
        self.filters = OrderedDict()
        for ffm in self.filter_fix_math_match:
            self.filters[ffm] = self.filter_fix_math
        for ffm in self.filter_fix_displaymath_match:
            self.filters[ffm] = self.filter_fix_displaymath
        for ffm in self.filter_fix_displaymathverbatim_match:
            self.filters[ffm] = self.filter_fix_displaymathverbatim
        self.filters[self.filter_fix_abox_match] = self.filter_fix_abox
        self.filters[self.filter_fix_abox_match_with_linenum] = self.filter_fix_abox_with_linenum
        self.filters[self.filter_fix_image_match] = self.filter_fix_image
        self.filters[self.filter_fix_edxxml_match] = self.filter_fix_edxxml

        if extra_filters is not None:
            self.filters.update(extra_filters)

    filter_fix_edxxml_match = '(?s)<edxxml>\\\\edXxml{(.*?)}</edxxml>'

    @staticmethod
    def filter_fix_edxxml(m):
        xmlstr = m.group(1)
        xmlstr = xmlstr.replace('\\$ ','$')	# dollar sign must be escaped in plasTeX, but shouldn't be in XML
        xmlstr = xmlstr.replace('& ', '&')  # remove ampersand space from plasTeX
        xmlstr = xmlstr.replace('\\% ', '%')  # unescape percentage sign

        # new for python3 plastex2.1 version: unescape xmlstr
        xmlstr = unescape(xmlstr)

        # return xmlstr
        return "<edxxml>%s</edxxml>" % xmlstr

    @staticmethod
    def fix_math_common(m, removenl=True):
        x = m.group(1).strip()
        x = x.replace('\\$ ','$')	# dollar sign must be escaped in plasTeX, but shouldn't be in XML
        x = x.replace('\u2019',"'")
        x = x.replace('\u201c',"'")
        x = x.replace('\\ensuremath','')
        x = x.replace('{^\\circ','{}^\\circ')	# workaround plasTeX bug
        if removenl:
            x = x.replace('\n','')
        x = escape(x)
        return x

    filter_fix_math_match  = ['(?s)<math>\$(.*?)\$</math>',
                              '(?s)<math>\\\\ensuremath{(.*?)}</math>']

    @classmethod
    def filter_fix_math(cls, m):
        try:
            x = cls.fix_math_common(m)
        except Exception as err:
            print("Failed to fix_math_common, match=")
            print((m.group(1)))
            raise
        if len(x)==0 or x=="\displaystyle":
            return "&nbsp;"
        return '[mathjaxinline]%s[/mathjaxinline]' % x
        
    filter_fix_displaymath_match = [r'(?s)<math>\\begin{equation}(.*?)\\end{equation}</math>',
                                    r'(?s)<math>\\begin{equation\*}(.*?)\\end{equation\*}</math>',
                                    r'(?s)<displaymath>\\begin{edXmath}(.*?)\\end{edXmath}</displaymath>',
                                    r'(?s)<math>\\\[(.*?)\\\]</math>',
                                    ]

    @classmethod
    def filter_fix_displaymath(cls, m):
        x = cls.fix_math_common(m)
        if len(x)==0 or x=="\displaystyle":
            return "&nbsp;"
        return '[mathjax]%s[/mathjax]' % x
        
    filter_fix_displaymathverbatim_match = [r'(?s)<displaymathverbatim>\\begin{edXmath}(.*?)\\end{edXmath}</displaymathverbatim>',
                                            r'(?s)<displaymathverbatim>\\edXmath(.*?)</displaymathverbatim>',
                                            ]

    @classmethod
    def filter_fix_displaymathverbatim(cls, m):
        # x = escape(m.group(1).strip())
        x = m.group(1).strip()			# plastex2.1 - already escaped
        return '[mathjax]%s[/mathjax]' % x.replace('\\end{edXmath}', '')

    filter_fix_image_match = '<includegraphics style="(.*?)">(.*?)</includegraphics>'

    def filter_fix_image(self, m):
        width = 400
        attribs = []
        print("[do_image] m=%s" % repr(m.groups()))
        style = m.group(1)
        sms = style.split(',')
        for sm in sms:
            w = re.search('width=([0-9\.]+)(.*)',sm)
            if w:
                widtype = w.group(2)
                width = float(w.group(1))
                if 'in' in widtype:
                    width = width * 110
                elif 'cm' in widtype:
                    width = width * 110 / 2.54
                if '\\textwidth' in widtype:
                    width = width * 770
                width = int(width)
                if width==0:
                    width = 400
            else:
                sm = sm.strip().replace('=', ':')
                attribs.append(sm)
        attribs = ';'.join(attribs)
        if attribs:
            attribs = 'style="' + attribs + '"'

        def make_image_html(fn,k,attribs):
            self.imfnset.append(fn+k)
            # if file doesn't exist in edX web directory, copy it there
            fnbase = os.path.basename(fn)+k
            wwwfn = '%s/%s' % (self.imdir,fnbase)
            #if not os.path.exists('/home/WWW' + wwwfn):
            if 1:
                cmd = 'cp %s %s' % (fn+k,wwwfn)
                os.system(cmd)
                print(cmd)
                os.system('chmod og+r %s' % wwwfn)
            return '<img src="/static/%s/%s" width="%d" %s/>' % (self.imurl,
                    fnbase, width, attribs)

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
                        except Exception as err:
                            # print "npages error %s" % err
                            npages = 1
                        nfound = 0
                        if npages>1:	# handle multi-page PDFs
                            fnset = ['%s-%d' % (fn,x) for x in range(npages)]
                            nfound = sum([ 1 if os.path.exists(x+'.png') else 0 for x in fnset])
                            print("--> %d page PDF, fnset=%s (nfound=%d)" % (npages, fnset, nfound))
                        if not nfound==npages:
                            os.system('convert -density 800 {fn}.pdf -scale {dim}x{dim} {fn}.png'.format(fn=fn,dim=dim))
                        if npages>1:	# handle multi-page PDFs
                            fnset = ['%s-%d' % (fn,x) for x in range(npages)]
                            print("--> %d page PDF, fnset=%s" % (npages, fnset))
                        else:
                            fnset = [fn]
                        imghtml = ''
                        for fn2 in fnset:
                            imghtml += make_image_html(fn2, '.png', attribs)
                        return imghtml
                    else:
                        return make_image_html(fn, k, attribs)
                
        fn = fnset[0]
        print('Cannot find image file %s' % fn)
        return '<img src="NOTFOUND-%s" />' % fn

    filter_fix_abox_match = r'(?s)<abox(|linenum="\d+" filename="[^>]+")>(.*?)</abox>'

    def filter_fix_abox(self, m):
        abox = AnswerBox(m.group(1), config=self.abox_config)
        self.answer_box_objects[abox.xmlstr_just_code] = abox
        return abox.xmlstr

    filter_fix_abox_match_with_linenum = r'(?s)<abox (linenum="\d+" filename="[^>]+")>(.*?)</abox>'

    def filter_fix_abox_with_linenum(self, m):
        abox = AnswerBox(m.group(2), config=self.abox_config, context=m.group(1))
        self.answer_box_objects[abox.xmlstr_just_code] = abox
        return abox.xmlstr

    @staticmethod
    def fix_unicode(stxt):
        ucfixset = { '\u201d': '"',
                     '\u2014': '&#8212;',
                     '\u2013': '&#8211;',
                     '\u2019': "'",
                     }

        for pre, post in ucfixset.items():
            try:
                stxt = stxt.replace(pre, post)
            except Exception as err:
                print("Error in rendering (fix unicode): ", str(err)[:1000])
        return stxt

    def processFileContent(self, document, stxt):
        stxt = XHTML.Renderer.processFileContent(self, document, stxt)
        stxt = self.fix_unicode(stxt)

        for fmatch, filfun in self.filters.items():
            try:
                stxt = re.sub(fmatch, filfun, stxt)
            except Exception as err:
                print("Error in rendering %s: %s" % (str(filfun)[:1000], str(err)[:1000]))
                raise

        stxt = stxt.replace('<p>','<p>\n')
        stxt = stxt.replace('<li>','\n<li>')
        stxt = stxt.replace('&nbsp;','&#160;')

        stxt = stxt[stxt.index('<body>')+6:stxt.index('</body>')]

        XML_HEADER = '<document>'
        XML_TRAILER = '</document>'

        self.xhtml = XML_HEADER + stxt + XML_TRAILER
        return self.xhtml

    def cleanup(self, document, files, postProcess=None):
        res = _Renderer.cleanup(self, document, files, postProcess=postProcess)
        return res


class plastex2xhtml(object):
    '''
    Use plastex to convert .tex file to .xhtml, with special edX macros.

    This procecss requires the "render" directory, with its .zpts files, as well
    as the edXpsl.py file, with its plastex python macros.

    '''

    def __init__(self,
                 fn,
                 imdir="static/images",
                 imurl="",
                 fp=None,
                 extra_filters=None,
                 latex_string=None,
                 add_wrap=False,
                 fix_plastex_optarg_bug=True,
                 verbose=False):
        '''
        fn            = tex filename (should end in .tex)
        imdir         = directory where images are to be stored
        imurl         = web root for images
        fp            = file object (optional) - used instead of open(fn), if provided
        extra_filters = dict with key=regular exp, value=function for search-replace, for
                        post-processing of XHTML output
        latex_string  = latex string (overrides fp and fn)
        add_wrap      = if True, then assume latex is partial, and add preamble and postfix
        fix_plastex_optarg_bug = if True, then filter the input latex to fix the plastex bug 
                                 triggered e.g. by \begin{edXchapter} and \begin{edXsection}
                                 being placed with no empty newline inbetween
        verbose       = if True, then do verbose logging
        '''

        if fn.endswith('.tex'):
            ofn = fn[:-4]+'.xhtml'
        else:
            ofn = fn + ".xhtml"

        self.input_fn = fn
        self.output_fn = ofn
        self.fp = fp
        self.latex_string = latex_string
        self.add_wrap = add_wrap
        self.verbose = verbose
        self.renderer = MyRenderer(imdir, imurl, extra_filters)
        self.fix_plastex_optarg_bug = fix_plastex_optarg_bug

        # Instantiate a TeX processor and parse the input text
        tex = TeX()
        tex.ownerDocument.config['files']['split-level'] = -100
        tex.ownerDocument.config['files']['filename'] = self.output_fn
        tex.ownerDocument.config['general']['theme'] = 'plain'

        plasTeXconfig.add_section('logging')
        plasTeXconfig['logging'][''] = CRITICAL

        self.tex = tex
        if not self.verbose:
            tex.disableLogging()

    def convert(self):
        self.generate_xhtml()	# do conversion

    def generate_xhtml(self):

        if self.verbose:
            print("=============================================================================")
            print("Converting latex to XHTML using PlasTeX with custom edX macros")
            print("Source file: %s" % self.input_fn)
            print("=============================================================================")
    
        # set the zpts templates path
        mydir = os.path.dirname(__file__)
        zptspath = os.path.abspath(mydir + '/render')
        os.environ['XHTMLTEMPLATES'] = zptspath

        # print os.environ['XHTMLTEMPLATES']

        # add our python plastex package directory to python path
        plastexpydir = os.path.abspath(mydir + '/plastexpy')
        sys.path.append(plastexpydir)

        # get the input latex file
        if self.latex_string is None:
            if self.fp is None:
                self.fp = codecs.open(self.input_fn)
            self.latex_string = self.fp.read()
            self.latex_string = self.latex_string.replace('\r','\n') # convert from mac format EOL
        
        if self.fix_plastex_optarg_bug:
            if self.verbose:
                print("[latex2html.plastexit] fixing plastex optarg bug")
            self.latex_string = self.do_fix_plastex_optarg_bug(self.latex_string)

        # add preamble and postfix wrap?
        if self.add_wrap:
            PRE = """\\documentclass[12pt]{article}\n\\usepackage{edXpsl}\n\n\\begin{document}\n\n"""
            POST = "\n\n\\end{document}"
            self.latex_string = PRE + self.latex_string + POST
 
        source = StringIO(self.latex_string)
        source.name = self.input_fn
        self.tex.input(source)
        document = self.tex.parse()
        
        self.renderer.render(document)

        # print(self.renderer.xhtml) # DEBUG
        print("XHTML generated (%s): %d lines" % (self.output_fn, len(self.renderer.xhtml.split('\n'))))
        return self.renderer.xhtml

    @property
    def xhtml(self):
        return self.renderer.xhtml
    
    def do_fix_plastex_optarg_bug(self, texstring):
        '''
        PlasTeX processing appears to have a bug, 
        wherein if the tex document has two consecutive lines like this:

          \begin{edXchapter}{Basic examples}
          \begin{edXsection}{Basic example problems}

        then the \begin{edXsection} gets eaten up as an optional argument
        to \begin{edXchapter}.  This happens for all the Base.Environment
        objects defined in edXpsl.py with optional arguments.

        This can be fixed by introducing an extra newline, e.g.:

          \begin{edXchapter}{Basic examples}

          \begin{edXsection}{Basic example problems}

        or by adding a {} at the end:

          \begin{edXchapter}{Basic examples}{}
          \begin{edXsection}{Basic example problems}{}

        Here, we fix the problem by adding extra newlines after every \begin{*}
        where * is one of the known new environments with optional arguments.
        '''

        edXenvironments = ['edXcourse', 
                           'edXchapter', r'edXchapter*',
                           'edXsection', r'edXsection*',
                           'edXsequential', r'edXsequential*',
                           'edXvertical', r'edXvertical*',
                           'edXtext',
                           'edXproblem',
                           'edXsolution',
                           'edXshowhide',
                           'document',
                           ]

        newstring = []
        insert_nl = False
        nnl = 0

        for line in texstring.split('\n'):

            if insert_nl:
                # insert empty line if current line is not already empty line
                if not line=='':
                    newstring.append('')
                    nnl += 1
                insert_nl = False

            if not r'\begin' in line:
                newstring.append(line)
                continue

            newstring.append(line)
            for env in edXenvironments:
                if line.startswith('\\begin{%s}' % env):
                    # queue up newline insertion
                    insert_nl = True

        newstring = '\n'.join(newstring)
        if self.verbose:
            print("[latex2html.plastexit] added %d newlines to workaround plastex bug crashing when \\begin{edXchapter} and \\begin{edXsection} with no intermediate newline" % nnl)
        return newstring
