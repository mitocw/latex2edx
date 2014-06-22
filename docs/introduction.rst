Introduction
============

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
mathametical symbols and functions, and arbitrary boolean combinations of
patterns.

Version 1.3 adds documentation, and the edXvideo and edXdiscussion macros.

See project homepage: 

   https://people.csail.mit.edu/ichuang/edx/latex2edx

Usage
-----

Usage: latex2edx [options] filename.tex

Options::

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

Quick Example
-------------

See live demo course: https://edge.edx.org/courses/MITx/MIT.latex2edx/2014_Spring/about

The source code for the demo course is here: https://github.com/mitocw/content-mit-latex2edx-demo

Here is an annotated input tex file which generates the source for an edX course::

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

