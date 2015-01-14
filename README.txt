=========
latex2edx
=========

Converts latex to edX XML format.

Uses plasTeX

Detailed documentation:

   http://mitocw.github.io/latex2edx/html/index.html

Project homepage: 

   https://people.csail.mit.edu/ichuang/edx/latex2edx

Installation
============

    pip install -e git+https://github.com/mitocw/latex2edx.git#egg=latex2edx

Note that xmllint and lxml are required; for ubuntu, this may work:

    apt-get install libxml2-utils python-lxml

Usage
=====

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
*     .3: Ensure edXinclude doesn't leave contents within a <p>; nicer error messages for include, with linenum
*     .4: Include linenum, filename in more error msgs; add --section-only, --xml-only, --units-only output fmts
* v1.4.0: Enable cross-referencing with \ref and \label; add --popups output fmt for eqns and figs; add ToC generation with \tocref and \toclabel
