import codecs
from plasTeX import Command, Environment, CountCommand
from plasTeX.Logging import getLogger
from plasTeX import Base

log = getLogger()
status = getLogger('status')

class MyBaseCommand(Base.Command):
    def invoke(self,tex):
        Command.invoke(self,tex)
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber

class MyBaseVerbatim(Base.verbatim):
    def invoke(self,tex):
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber
        return Base.verbatim.invoke(self,tex)

class MyBaseEnvironment(Base.Environment):
    def invoke(self,tex):
        self.attributes['filename'] = tex.filename
        self.attributes['linenum'] = tex.lineNumber
        return Base.Environment.invoke(self,tex)

class edXcourse(Base.Environment):
    args = '{ number } { display_name } [ attrib_string:str ] self'

class EdXchapterStar(MyBaseEnvironment):
    macroName = 'edXchapter*'
    args = '{ display_name } [ attrib_string:str ] self'

class edXchapter(EdXchapterStar):
    macroName = 'edXchapter'
    counter = 'chapter'
    position = 0
    forcePars = True
    args = '{ display_name } [ attrib_string:str ] self'
    def invoke(self,tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self,tex)

class EdXsectionStar(MyBaseEnvironment):
    macroName = 'edXsection*'
    args = '{ display_name } [ attrib_string:str ] self'

class edXsection(EdXsectionStar):
    macroName = 'edXsection'
    counter = 'section'
    position = 0
    forcePars = True
    args = '{ display_name } [ attrib_string:str ] self'
    def invoke(self,tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self,tex)

class EdXsequentialStar(MyBaseEnvironment):
    macroName = 'edXsequential*'
    args = '{ display_name } [ attrib_string:str ] self'

class edXsequential(EdXsequentialStar):
    macroName = 'edXsequential'
    counter = 'section'
    position = 0
    forcePars = True
    args = '{ display_name } [ attrib_string:str ] self'
    def invoke(self,tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self,tex)

class EdXverticalStar(MyBaseEnvironment):
    macroName = 'edXvertical*'
    args = '{ display_name } [ attrib_string:str ] self'

class edXvertical(EdXverticalStar):
    macroName = 'edXvertical'
    counter = 'subsection'
    position = 0
    forcePars = True
    args = '{ display_name } [ attrib_string:str ] self'
    def invoke(self,tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self,tex)

class edXabox(MyBaseCommand):
    args = 'self'

class edXinlinevideo(Base.Command):
    args = 'self'

class edXinline(Base.Command):
    args = 'self'

class edXvideo(Base.Command):
    args = 'self'

class includegraphics(Base.Command):
    args = '[ width ] self'

class edXinclude(Base.Command):		# include external file
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

class edXproblem(MyBaseEnvironment):
    args = '{ display_name } { attrib_string } self'

class edXtext(MyBaseEnvironment):	# indicates HTML file to be included (ie <html...> in course.xml)
    args = '{ display_name } [ attrib_string:str ] self'

class edXsolution(MyBaseEnvironment):
    args = 'self'

class section(Base.Command):
    args = 'self'

class subsection(Base.Command):
    args = 'self'

class label(Base.Command):
    args = 'self'

class ref(Base.Command):
    args = 'self'

class toclabel(Base.Command):
    args = 'self'

class tocref(Base.Command):
    args = 'self'

class href(Base.Command):
    args = 'self'
