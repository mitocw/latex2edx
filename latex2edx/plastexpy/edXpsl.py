import codecs
from plasTeX import Command, Environment, CountCommand
from plasTeX.Logging import getLogger
from plasTeX import Base

log = getLogger()
status = getLogger('status')

class edXcourse(Base.Environment):
    args = '{ number } { display_name } [ attrib_string:str ] self'

class edXchapter(Base.Environment):
    args = '{ display_name } [ attrib_string:str ] self'

class edXsection(Base.Environment):
    # turns into edXsequential
    args = '{ display_name } [ attrib_string:str ] self'

class edXsequential(Base.Environment):
    args = '{ display_name } [ attrib_string:str ] self'

class edXvertical(Base.Environment):
    args = '{ display_name } [ attrib_string:str ] self'

class edXabox(Base.Command):
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

class edXcite(Base.Command):	# tooltip citation (appears onmoseover, using <a title="self" href="#"><sup>[ref]</sup></a>)
    args = '[ ref ] self'

class edXinclude(Base.Command):		# include external XML file
    args = 'self'

class edXincludepy(Base.Command):		# include external python file (puts inside <script>)
    args = 'self'

class edXshowhide(Base.Environment):	# block of text to be hidden by default, but with clickable "show"
    args = ' { id } { description } self'

class edXscript(Base.verbatim):
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

class edXmath(Base.Environment):
    args = 'self'

class edXxml(Base.Command):
    args = 'self'

class edXproblem(Base.Environment):
    args = '{ display_name } { attrib_string } self'

class edXtext(Base.Environment):	# indicates HTML file to be included (ie <html...> in course.xml)
    args = '{ display_name } [ attrib_string:str ] self'

class edXsolution(Base.Environment):
    args = 'self'
    # note: cannot have \[ immediately after \begin{edXsolution}

class section(Base.Command):
    args = 'self'

class subsection(Base.Command):
    args = 'self'

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

    
