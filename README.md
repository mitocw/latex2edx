latex2edx
=========

This is version 1.3 of the open-source latex2edx compiler for
generating interactive MITx / edX courses from LaTeX

![latex2edx logo](https://raw.github.com/mitocw/latex2edx/master/docs/images/latex2edx-logo.png)

This system is particularly useful for producing interactive course
content where the expressive power of LaTeX is helpful, e.g. with
math, physics, CS content. latex2edx provides interactivity via the
introduction of a basic new macro, the "answer box" \edXabox, which
defines a mechanism for student input, as well as how that input is to
be graded. Also introduced are structural macros for defining course
structure.

Version 1.2 provides, in addition, structured access to the adaptive hint 
system built into the edX platform, via a generalized hints system. 
This system allows hints to be provided for custom, multiple-choice,
option, and numerical response problems, based on student responses.  
The hint system provided by latex2edx allows authors to specify hints
via pattern matching, based on matching strings, numerical value ranges,
mathematical symbols and functions, and arbitrary boolean combinations of
patterns.

Version 1.3 adds documentation, and the edXvideo and edXdiscussion macros.

See project homepage: 

   https://people.csail.mit.edu/ichuang/edx/latex2edx

and detailed documentation:

   http://mitocw.github.io/latex2edx/html/index.html


Requirements
============

* python 2.7
* python-lxml
* beautifulsoup

Installation
============

Install using this command:

    pip install -e git+https://github.com/mitocw/latex2edx.git#egg=latex2edx

Note that xmllint and lxml are required; for ubuntu, this may work:

    apt-get install libxml2-utils python-lxml

PlasTeX (http://plastex.sourceforge.net/) is also required, but should
be installed automatically by the pip install.

Usage
=====

```
latex2edx -h                                                                                                                                       15:30:51
Usage: latex2edx [options] filename.tex

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -v, --verbose         verbose error messages
  -o OUTPUT_FN, --output-xbundle=OUTPUT_FN
                        Filename for output xbundle file
  -d OUTPUT_DIR, --output-directory=OUTPUT_DIR
                        Directory name for output course XML files
  -c CONFIG_FILE, --config-file=CONFIG_FILE
                        configuration file to load
  -m, --merge-chapters  merge chapters into existing course directory
  -P, --update-policy-file
                        update policy.json from settings in latex file
  --suppress-policy-settings
                        suppress policy settings from XML files
  --suppress-verticals  do not automatically add extra verticals needed for
                        Studio compatibility
  -S, --section-only    export only edXsections (sequentials) -- no course or
                        chapters
  -x, --xml-only        export only xbundle xml file -- no separate course
                        content
  --units-only          export only units, including problem, html -- no
                        course, chapter, section
```

Example
=======

See live demo course: https://edge.edx.org/courses/MITx/MIT.latex2edx/2014_Spring/about

The source code for the demo course is here: https://github.com/mitocw/content-mit-latex2edx-demo

Here is an annotated input tex file which generates the source for an edX course:

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    \documentclass[12pt]{article}
    
    \usepackage{edXpsl}	% edX "problem specification language"
    
    \begin{document}
    
    % edXcourse: {course_number}{course display_name}[optional arguments like semester]
    \begin{edXcourse}{MIT.latex2edx}{latex2edx demo course}[semester="2014 Spring"]
    
    % edXchapter: {chapter display_name}[optional arguments like url_name]
    \begin{edXchapter}{Basic examples}
    
    % edXsection: {section display_name}[optional arguments like url_name]
    % this turns into a <sequential> in the XML
    \begin{edXsection}{Basic example problems}
    
    % edXvertical: {vertical display_name}[optional arguments like url_name]
    \begin{edXvertical}
    
    % edXproblem: {problem display_name}{attributes: url_name, weight, attempts}
    \begin{edXproblem}{Numerical response}{attempts=10}
    
    What is the numerical value of $\pi$?

    % \edXabox: answer box, specifying question type and expected response
    \edXabox{expect="3.14159" type="numerical" tolerance='0.01' }
    
    \end{edXproblem}
    \end{edXvertical}
    \end{edXsection}
    \end{edXchapter}
    \end{edXcourse}
    \end{document}
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

History
=======

* v1.0: python package; unit tests; xbundle and modular code
* v1.1.0: Support for jsinput, custom mathjax filtering, formularesponse
*     .1: Fix optargs bug with plastex
*     .2: Allow spaces in semester; give example in README
*     .3: Fix bug in eqnarray table widths
*     .4: Fix showhide to work under firefox
*     .5: Allow multiple correct answers in multichoice
*     .6: Add \edXgitlink for link to specific line in source file
*     .7: Add \edXaskta for "Ask TA!" buttons
*     .8: bugfix for edxxml
*     .9: Allow \edXtext to have attributes option, eg \begin{edXtext}{My Name}[url_name=text_url_name]
*    .10: check imported python scripts for syntax errors
* v1.2.0: General hint system for problems
*     .1: All python scripts syntax checked
*     .2: New option -P for generating policy.json from tex; handles, e.g. start, end, due, graded
* v1.3.0: Add documentation, abox unit tests, edXvideo, edXdiscussion
*     .1: Add regexp mapping to hints; add \edXdndtex command; allow texbox for customresponse
*     .2: Fix edXmath environment to use verbatim
*     .3: Ensure edXinclude doesn't leave contents within a p; nicer error messages for include, with linenum
*     .4: Include linenum, filename in more error msgs; add --section-only, --xml-only, --units-only output fmts
* v1.4.0: Enable cross-referencing with \ref and \label; add --popups output fmt for eqns and figs; add ToC generation with \tocref and \toclabel
