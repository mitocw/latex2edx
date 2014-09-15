from plasTeX import Base

class edXcourse(Base.Environment):
    args = '{ number } { url_name } { attrib_string } self'

class EdXchapterStar(Base.Environment):
    macroName = 'edXchapter*'
    args = '{ display_name } self'

class edXchapter(EdXchapterStar):
    macroName = 'edXchapter'
    counter = 'chapter'
    position = 0
    forcePars = True
    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self, tex)

class EdXsectionStar(Base.Environment):
    macroName = 'edXsection*'
    args = '{ url_name } self'

class edXsection(EdXsectionStar):
    macroName = 'edXsection'
    counter = 'section'
    position = 0
    forcePars = True
    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self, tex)

class EdXsequentialStar(Base.Environment):
    macroName = 'edXsequential*'
    args = 'self'

class edXsequential(EdXsequentialStar):
    macroName = 'edXsequential'
    counter = 'section'
    position = 0
    forcePars = True
    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self, tex)

class EdXverticalStar(Base.Environment):
    macroName = 'edXvertical*'
    args = '{ display_name } self'

class edXvertical(EdXverticalStar):
    macroName = 'edXvertical'
    counter = 'subsection'
    position = 0
    forcePars = True
    def invoke(self, tex):
        self.position = self.ownerDocument.context.counters[self.counter].value + 1
        return Base.Environment.invoke(self, tex)

class edXabox(Base.Command):
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

class edXproblem(Base.Environment):
    args = '{ url_name } { attrib_string } self'

class edXtext(Base.Environment):	# indicates HTML file to be included (ie <html...> in course.xml)
    args = '{ url_name } self'

class edXsolution(Base.Environment):
    args = 'self'

class section(Base.Command):
    args = 'self'

class subsection(Base.Command):
    args = 'self'

class label(Base.Command):
    args = 'self'

class ref(Base.Command):
    args = 'self'

