Release History
===============

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
