import codecs
from plasTeX import Command, Environment, CountCommand
from plasTeX.Logging import getLogger
from plasTeX import Base

log = getLogger()
status = getLogger('status')


def ProcessOptions(options, document):
    context = document.context
    context.newcounter('edXchapter', initial=0)
    context.newcounter('edXsequential', resetby='edXchapter', initial=0)
    context.newcounter('edXvertical', resetby='edXsequential', initial=0)


class MyBaseCommand(Base.Command):  # add filename and linenum attributes
    def invoke(self, tex):
        Command.invoke(self, tex)
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber


class MyBaseVerbatim(Base.verbatim):  # add filename and linenum attributes
    def invoke(self, tex):
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber
        return Base.verbatim.invoke(self, tex)


class MyBaseEnvironment(Base.Environment):  # add filename and linenum attributes
    def invoke(self, tex):
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber
        return Base.Environment.invoke(self, tex)


class edXcourse(Base.Environment):
    args = '{ number } { display_name } [ attrib_string:str ] self'


class EdXchapterStar(MyBaseEnvironment):
    macroName = 'edXchapter*'
    args = '{ display_name } [ attrib_string:str ] self'


class edXchapter(EdXchapterStar):
    macroName = 'edXchapter'
    counter = 'edXchapter'
    forcePars = True

    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return MyBaseEnvironment.invoke(self, tex)


class EdXsectionStar(MyBaseEnvironment):
    # turns into edXsequential
    macroName = 'edXsection*'
    args = '{ display_name } [ attrib_string:str ] self'


class edXsection(EdXsectionStar):
    # turns into edXsequential
    macroName = 'edXsection'
    counter = 'edXsequential'
    forcePars = True

    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return MyBaseEnvironment.invoke(self, tex)


class EdXsequentialStar(MyBaseEnvironment):
    macroName = 'edXsequential*'
    args = '{ display_name } [ attrib_string:str ] self'


class edXsequential(EdXsequentialStar):
    macroName = 'edXsequential'
    counter = 'edXsequential'
    forcePars = True

    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return MyBaseEnvironment.invoke(self, tex)


class EdXverticalStar(MyBaseEnvironment):
    macroName = 'edXvertical*'
    args = '{ display_name } [ attrib_string:str ] self'


class edXvertical(EdXverticalStar):
    macroName = 'edXvertical'
    counter = 'edXvertical'
    forcePars = True

    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return MyBaseEnvironment.invoke(self, tex)


class edXabox(MyBaseCommand):
    args = 'self'


class edXinline(Base.Command):
    args = 'self'


class edXbr(Base.Command):
    args = 'self'


class edXvideo(Base.Command):
    args = '{ display_name } { youtube } [ attrib_string ] self'
    # args = 'self'


class edXdiscussion(Base.Command):
    args = '{ display_name } { attrib_string } self'


class includegraphics(Base.Command):
    args = '[ width ] self'


class edXcite(Base.Command):  # tooltip citation (appears onmoseover, using <a title="self" href="#"><sup>[ref]</sup></a>)
    args = '[ ref ] self'


class edXinclude(MyBaseCommand):  # include external XML file
    args = 'self'


class edXincludepy(MyBaseCommand):  # include external python file (puts inside <script>)
    args = 'self'


class edXdndtex(MyBaseCommand):  # insert external drag-and-drop problem (should point to latex2dnd tex file)
    args = '[ attrib_string ] self'

    def invoke(self, tex):
        Command.invoke(self, tex)
        print "  --> edXdndtex in %s: dndtex=%s, line=%s" % (tex.filename, self.attributes['self'].source, tex.lineNumber)


class edXshowhide(Base.Environment):  # block of text to be hidden by default, but with clickable "show"
    args = ' { description } self'


class edXscript(MyBaseVerbatim):
    macroName = "edXscript"


class endedXscript(Base.endverbatim):
    macroName = "endedXscript"


class edXanswer(Base.verbatim):
    macroName = "edXanswer"


class endedXanswer(Base.endverbatim):
    macroName = "endedXanswer"


class edXjavascript(Base.verbatim):
    macroName = "edXjavascript"


class endedXjavascript(Base.endverbatim):
    macroName = "endedXjavascript"


class edXmath(Base.verbatim):
    macroName = "edXmath"


class endedXmath(Base.endverbatim):
    macroName = "endedXmath"


class edXxml(Base.Command):
    args = 'self'


class edXproblem(MyBaseEnvironment):
    args = '{ display_name } { attrib_string } self'


class edXtext(MyBaseEnvironment):  # indicates HTML file to be included (ie <html...> in course.xml)
    args = '{ display_name } [ attrib_string:str ] self'


class edXsolution(MyBaseEnvironment):
    args = 'self'
    # note: cannot have \[ immediately after \begin{edXsolution}


class section(Base.Command):
    args = '* self'


class subsection(Base.Command):
    args = '* self'


class subsubsection(Base.Command):
    args = '* self'


class label(Base.Command):
    args = 'self'


class ref(Base.Command):
    args = 'self'


class toclabel(Base.Command):
    args = 'self'


class tocref(Base.Command):
    args = 'self'


class index(Base.Command):
    args = 'self'


class href(Base.Command):
    args = '{ url } self'


class textwidth(Base.Command):
    args = ''


class edXaskta(Base.Command):
    # ask TA link
    args = 'self'


class input(Command):
    """ verbose version of \\input
    """
    args = 'name:str'

    def invoke(self, tex):
        a = self.parse(tex)
        # print "myinput a=%s, tex=%s" % (a,tex)
        try:
            path = tex.kpsewhich(a['name'])
        except Exception, msg:
            # print "myinput kpsewhich error=%s" % msg
            path = a['name']
            if not path.endswith('.tex'):
                path += '.tex'

        try:
            print "\n----------------------------------------------------------------------------- Input [%s]" % path
            status.info(' ( %s ' % path)
            encoding = self.config['files']['input-encoding']
            tex.input(codecs.open(path, 'r', encoding, 'replace'))
            status.info(' ) ')

        except (OSError, IOError), msg:
            print "myinput error=%s" % msg
            log.warning(msg)
            status.info(' ) ')


class edXgitlink(Command):
    '''
    Output link to github file with line number of specific place inside file
    '''
    args = '{url_root}{name}'

    def invoke(self, tex):
        Command.invoke(self, tex)
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber
        self.attributes['url'] = '%s/%s#L%s' % (self.attributes['url_root'].source, tex.filename, tex.lineNumber)
        # print "root=%s, name=%s" % (self.attributes['url_root'].source, self.attributes['name'].source)
        print "  --> edXgitlink: file=%s, line=%s, url=%s" % (tex.filename, tex.lineNumber, self.attributes['url'])
