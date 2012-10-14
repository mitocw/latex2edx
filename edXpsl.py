from plasTeX import Base

class edXcourse(Base.Environment):
    args = '{ number } { name } self'

class edXchapter(Base.Environment):
    args = '{ name } self'

class edXsection(Base.Environment):
    args = '{ name } self'

class edXsequential(Base.Environment):
    args = 'self'

class edXabox(Base.Command):
    args = 'self'

class edXinline(Base.Command):
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

class edXproblem(Base.Environment):
    args = '{ name } { points } self'

class edXtext(Base.Environment):	# indicates HTML file to be included (ie <html...> in course.xml)
    args = '{ name } self'

class edXsolution(Base.Environment):
    args = 'self'

class section(Base.Command):
    args = 'self'

class subsection(Base.Command):
    args = 'self'
