from plasTeX import Base

class edXcourse(Base.Environment):
    args = '{ number } { url_name } { attrib_string } self'

class edXchapter(Base.Environment):
    args = '{ display_name } self'

class edXsection(Base.Environment):
    args = '{ url_name } self'

class edXsequential(Base.Environment):
    args = 'self'

class edXvertical(Base.Environment):
    args = '{ display_name } self'

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

class ref(Base.Command):
    args = 'self'
