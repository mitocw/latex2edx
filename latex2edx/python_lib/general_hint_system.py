# 
# General hint system for edX
#
# Hints are specified by defining a list of hint dicts.
# Each hint dict should contain the following key/value pairs:
#
#    hint    - value = hint string to display if any matches found
#
#    string  - match on string present for in the student's answer
#    symbol  - match on math symbol in the answer
#    func    - match on math function in the answer
#    isnum   - match on answer being numerical (value ignored)
#    val     - match on numerical value of student's answer
#              value = number ...or
#              value = {'expect': number, 'tolerance': tolerance}
#    magdif  - match on difference in magnitude between given and expected numerical values being too large
#              value = expected number ...or
#              value = {'expect': number, 'max': maximum_magnitude_difference_in_log10}
#    range   - match on numerical answer being within a certain range
#              value = [min, max]
#    formula - match on formula equality (via numerical sampling);
#              value = as <expr>!<variables>@<lower_range>:<upper_range>#<num_samples>
#    parens  - match on un-balanced parentheses
#              value = ignored (anything ok)
#    eval    - match on evaluated expression, which may contain calls to other hint functions
#              value = expression to evaluate, e.g. "not string('*') and string('x')"
#
# Examples:
#
#         hints = [ {'parens': '', 'hint': 'Missing parenthesis?'},
#                   {'eval': 'not string("*")',
#                    'hint': 'Please indicate multiplication explicitly using *'},
#                   {'symbol': 'L', 'hint': 'Should your answer depend on L?'},
#                   {'string': 'D^2_eg', 'hint': 'Enter D_eg^2 and not D^2_eg'},
#                   {'symbol': 'D', 'hint': 'Enter D_eg and not D'},
#                   {'eval': 'not string("hbar")', 'hint': "Are your units correct?"},
#                   {'eval': 'string("-")', 'hint': "Are your sign(s) correct?"},
#                  ]
# 
#         ch0 = HintSystem(anum=0, hints=hints2).check_hint
#
#  <hintgroup hintfn="ch0"/>
#
# Usage:
#
# Simple case, for a single input field: define the global variable "hints" with list of hint dicts
# use "check_hint" as the hintfn in the edX capa problem.
#
# Advanced case: for multiple input fields
#
# Instantiate HintSystem with configuration parameters anum=answer number, hints = list of hint dicts
# 
#        ch1 = HintSystem(anum=0, hints=hints1).check_hint
#        ch2 = HintSystem(anum=1, hints=hints2).check_hint
#
# then use ch1 and ch2 as the hintfn in the edX capa problem.

import re
import numpy
import numbers
import random

from math import log10
from functools import partial

from calc import evaluator
from calc import ParseAugmenter

#-----------------------------------------------------------------------------
# provide compare_with_tolerance and formula_test (for equation property checking)

class HintFormulaCheck(object):

    default_tolerance = '0.01%'

    def __init__(self, tolerance=None, evalfun=None):
        if tolerance is not None:
            self.default_tolerance = tolerance
        self.evalfun = evalfun or evaluator
        return
    
    def compare_with_tolerance(self, complex1, complex2, tolerance=None, relative_tolerance=False):
        """
        Compare complex1 to complex2 with maximum tolerance tol.
    
        If tolerance is type string, then it is counted as relative if it ends in %; otherwise, it is absolute.
    
         - complex1    :  student result (float complex number)
         - complex2    :  instructor result (float complex number)
         - tolerance   :  string representing a number or float
         - relative_tolerance: bool, used when`tolerance` is float to explicitly use passed tolerance as relative.
    
         Default tolerance of 1e-3% is added to compare two floats for
         near-equality (to handle machine representation errors).
         Default tolerance is relative, as the acceptable difference between two
         floats depends on the magnitude of the floats.
         (http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/)
         Examples:
            In [183]: 0.000016 - 1.6*10**-5
            Out[183]: -3.3881317890172014e-21
            In [212]: 1.9e24 - 1.9*10**24
            Out[212]: 268435456.0
        """
        if tolerance is None:
            tolerance = self.default_tolerance

        def myabs(elem):
            if isinstance(elem, numpy.matrix):
                return numpy.sum(abs(elem))
            return abs(elem)
    
        if isinstance(tolerance, numbers.Number):
            tolerance = str(tolerance)
        if relative_tolerance:
            tolerance = tolerance * max(myabs(complex1), myabs(complex2))
        elif tolerance.endswith('%'):
            tolerance = self.evalfun(dict(), dict(), tolerance[:-1]) * 0.01
            tolerance = tolerance * max(myabs(complex1), myabs(complex2))
        else:
            tolerance = self.evalfun(dict(), dict(), tolerance)
    
        try:
            if numpy.isinf(complex1).any() or numpy.isinf(complex2).any():
                # If an input is infinite, we can end up with `abs(complex1-complex2)` and
                # `tolerance` both equal to infinity. Then, below we would have
                # `inf <= inf` which is a fail. Instead, compare directly.
                cmp = (complex1 == complex2)
                if isinstance(cmp, numpy.matrix):
                    return cmp.all()
                return cmp
            else:
                # v1 and v2 are, in general, complex numbers:
                # there are some notes about backward compatibility issue: see responsetypes.get_staff_ans()).
                # return abs(complex1 - complex2) <= tolerance
                #
                # sum() used to handle matrix comparisons
                return numpy.sum(abs(complex1 - complex2)) <= tolerance
        except Exception as err:
            print("failure in comparison, complex1=%s, complex2=%s" % (complex1, complex2))
            print("err = ", err)
            raise
    
    def is_formula_equal(self, expected, given, samples, cs=True, tolerance='0.01', evalfun=None,
                         cmpfun=None, debug=False):
        '''
        expected = expression expected by instructor
        given = expression entered by student
        samples = sample string for numerical checking (see below)
        cs = case_sensitive flag
        tolerance = tolerance specification string
        evalfun = function for doing evaluation (defaults to using self.evalfun from calc2)
        cmpfun = comparison function for testing equality (defaults to compare_with_tolerance)
        debug = flag for verbosity of debugging output
    
        samples examples:
    
        samples="m_I,m_J,I_z,J_z@1,1,1,1:20,20,20,20#50"
        samples="J,m,Delta,a,h,x,mu_0,g_I,B_z@0.5,1,1,1,1,1,1,1,1:0.5,20,20,20,20,20,20,20,20#50" 
    
        matrix sampling:
    
        samples="x,y@[1|2;3|4],[0|2;4|6]:[5|5;5|5],[8|8;8|8]#50"
    
        complex numbers:
    
        "x,y,i@[1|2;3|4],[0|2;4|6],0+1j:[5|5;5|5],[8|8;8|8],0+1j#50"
        '''
        
        if evalfun is None:
            evalfun = self.evalfun
        if cmpfun is None:
            def cmpfun(a, b, tol):
                return self.compare_with_tolerance(a, b, tol)
            
        variables = samples.split('@')[0].split(',')
        numsamples = int(samples.split('@')[1].split('#')[1])
    
        def to_math_atom(sstr):
            '''
            Convert sample range atom to float or to matrix
            '''
            if '[' in sstr:
                return numpy.matrix(sstr.replace('|',' '))
            elif 'j' in sstr:
                return complex(sstr)
            else:
                return float(sstr)
    
        sranges = list(zip(*[list(map(to_math_atom, x.split(","))) for x in samples.split('@')[1].split('#')[0].split(':')]))
        ranges = dict(list(zip(variables, sranges)))
    
        if debug:
            print("ranges = ", ranges)
    
        for i in range(numsamples):
            vvariables = {}
            for var in ranges:
                value = random.uniform(*ranges[var])
                vvariables[str(var)] = value
            if debug:
                print("vvariables = ", vvariables)
            try:
                instructor_result = evalfun(vvariables, dict(), expected, case_sensitive=cs)
            except Exception as err:
                #raise Exception("is_formula_eq: vvariables=%s, err=%s" % (vvariables, str(err)))
                #raise Exception("-- %s " % str(err))
                raise Exception("Error evaluating instructor result, expected=%s, vv=%s -- %s " % (expected, vvariables, str(err)))
            try:
                student_result = evalfun(vvariables, dict(), given, case_sensitive=cs)
            except Exception as err:
                #raise Exception("is_formula_eq: vvariables=%s, err=%s" % (vvariables, str(err)))
                raise Exception("-- %s " % str(err))
                # raise Exception("Error evaluating your input, given=%s, vv=%s -- %s " % (given, vvariables, str(err)))
            #print "instructor=%s, student=%s" % (instructor_result, student_result)
            cfret = cmpfun(instructor_result, student_result, tolerance)
            if debug:
                print("comparison result = %s" % cfret)
            if not cfret:
                return False
        return True
    
    def check_formula(self, expect, ans, options=None):
        '''
        expect and ans are math expression strings.
        Check for equality using random sampling.
        options should be like samples="m_I,m_J,I_z,J_z@1,1,1,1:20,20,20,20#50"!tolerance=0.3
        i.e. a sampling range for the equality testing, in the same
        format as used in formularesponse.
    
        options may also include altanswer, an alternate acceptable answer.  Example:
    
        options="samples='X,Y,i@[1|2;3|4],[0|2;4|6],0+1j:[5|5;5|5],[8|8;8|8],0+1j#50'!altanswer='-Y*X'"
    
        note that the different parts of the options string are to be spearated by a bang (!).
        '''
        #'''
        samples = None
        tolerance = '0.1%'
        acceptable_answers = [expect]
        for optstr in options.split('!'):
            if 'samples=' in optstr:
                samples = eval(optstr.split('samples=')[1])
            elif 'tolerance=' in optstr:
                tolerance = eval(optstr.split('tolerance=')[1])
            elif 'altanswer=' in optstr:
                altanswer = eval(optstr.split('altanswer=')[1])
                acceptable_answers.append(altanswer)
        if samples is None:
            return {'ok': False, 'msg': 'Oops, problem authoring error, samples=None'}
    
        # for debugging
        # return {'ok': False, 'msg': 'altanswer=%s' % altanswer}
    
        # filter the answer if the global function "ans_filter" is defined
        if 'ans_filter' in globals() or 'ans_filter' in locals():
            try:
                global ans_filter
                ans = ans_filter(ans)
            except Exception as err:
                #raise
                pass
    
        # for debuging
        # return {'ok': False, 'msg': 'ans=%s' % ans}
    
        for acceptable in acceptable_answers:
            try:
                ok = self.is_formula_equal(acceptable, ans, samples, cs=True, tolerance=tolerance,
                                           evalfun=self.evalfun, debug=False)
            except Exception as err:
                return {'ok': False, 'msg': "Sorry, could not evaluate your expression.  Error %s" % str(err)}
            if ok:
                return {'ok':True, 'msg': ''}
    
        return {'ok':ok, 'msg': ''}
    
#-----------------------------------------------------------------------------

class HintSystem(object):

    def __init__(self, anum=0, hints=None, verbose_fail=False, 
                 extra_hint_functions=None, color="orange",
                 do_not_catch_exceptions=False,
                 tolerance=None,
                 evalfun=None,
                 ):
        '''
        anum = answer_id index number, to base hint off of
        verbose_fail = flag for verbose error messages (bool)
        extra_hint_functions = None, or dict of extra hint functions and hint types
        the_hints = hints to use (defaults to global variable "hints")
        color = color to use for hints
        '''
        
        self.anum = anum
        self.verbose_fail = verbose_fail
        self.extra_hint_functions = extra_hint_functions
        self.hints = hints
        self.color = color
        self.do_not_catch_exceptions = do_not_catch_exceptions
        self.hfc = HintFormulaCheck(tolerance=tolerance, evalfun=evalfun)

    @staticmethod
    def hint_check_unbalanced_parens(ans, term):
        '''
        ans = student answer
        term = ignored
    
        Returns True if parentheses are unbalanced
        '''
        stack = []
        pushChars, popChars = "({[", ")}]"
        for c in ans :
            if c in pushChars :
                stack.append(c)
            elif c in popChars :
                if not len(stack) :
                    return True
                else:
                    stackTop = stack.pop()
                    balancingBracket = pushChars[popChars.index(c)]
                    if stackTop != balancingBracket:
                        return True
        return len(stack)>0
    
    def hint_check_formula(self, ans, term):
        '''
        ans = student answer
        term = formula to check equality with, as <expr>!<variables>@<lower_range>:<upper_range>#<num_samples>
    
        Returns True if answer equals formula
        '''
        expect, samples = term.split('!')
        options = "samples='%s'" % samples
        ret = self.hfc.check_formula(expect, ans, options=options)
        return ret['ok']
    
    @staticmethod
    def hint_check_numerical(ans, term):
        '''
        return True if ans is numerical
        '''
        try:
            x = float(ans)
            return True
        except Exception as err:
            return False
        return False

    def hint_check_val(self, ans, term):
        '''
        ans = student answer
        term = search term to look for
    
        val: check for numerical value of answer matching "term"
    
        do not worry about errors: those are caught by the caller
        '''
        if isinstance(term, dict):
            expect = term['expect']
            tolerance = term['tolerance']
        else:
            expect = term
            tolerance = '5%'
        if not type(expect)==float:
            expect = float(eval(expect))
    
        nans = float(eval(ans))
        ok = self.hfc.compare_with_tolerance(expect, nans, tolerance=tolerance)
        if ok:
            return True
        return False
    
    
    @staticmethod
    def hint_check_magdif(ans, term):
        # compute difference of ans and expected, in terms of order of magnitude
        if isinstance(term, dict):
            expect = term['expect']
            max_magdif = term['max']
        else:
            expect = term
            max_magdif = 2
        try:
            magdif = abs( log10(abs(float(ans)))-log10(abs(expect)) )
        except Exception as err:
            return False
        if magdif > max_magdif:
            return True
        return False
    
    
    @staticmethod
    def hint_check_string(ans, term):
        '''
        string: search for string in ans

        ans = student answer
        term = search term to look for

        if term is a dict, it can contain these keys:
           
           - regexp: value = regular expression to match
           - nospaces: value = string to look for in answer (after all spaces removed from ans)
    
        don't worry about errors: those are caught by the caller
        '''
        if isinstance(term, dict):
            if 'regexp' in term:
                return (re.search(term['regexp'], ans) is not None)
            elif 'nospaces' in term:
                return (term['nospaces'] in ans.replace(' ',''))
        return ans.count(term)
    
    
    @staticmethod
    def hint_check_symbol(ans, term):
        '''
        ans = student answer
        term = search term to look for
    
        sym: search for math symbol in ans
    
        don't worry about errors: those are caught by the caller
        '''
        case_sensitive = True
        # parse expression
        math_interpreter = ParseAugmenter(ans, case_sensitive)
        math_interpreter.parse_algebra()
        found = term in math_interpreter.variables_used
        # for debugging
        # print 'for %s, found=%s, variables = %s' % (ans, found, math_interpreter.variables_used)
        return found
        
    
    @staticmethod
    def hint_check_function_used(ans, term):
        '''
        ans = student answer
        term = search term to look for
    
        search for function used in ans
    
        don not worry about errors: those are caught by the caller
        '''
        case_sensitive = True
        # parse expression
        math_interpreter = ParseAugmenter(ans, case_sensitive)
        math_interpreter.parse_algebra()
        found = term in math_interpreter.functions_used
        # for debugging
        # print 'for %s, found=%s, variables = %s' % (ans, found, math_interpreter.variables_used)
        return found
        
    
    @staticmethod
    def hint_check_range(ans, term):
        '''
        ans = student answer
        term = list [bot, top] giving numerical range to check to see if answer is within
        '''
        nans = float(eval(ans))
        [bot, top] = term
        if nans < bot:
            return False
        if nans > top:
            return False
        return True
    
    
    def check_hint(self, answer_ids, student_answers, new_cmap, old_cmap, anum=None, the_hints=None):
        '''
        answer_ids = list of indexes into student_answers
        student_answers = dict of student answers
        new_cmap = new correct_map object (see capa package)
        old_cmap = old correct_map object (see capa package)
        '''
    
        if the_hints is None:
            if self.hints is None:
                global hints
                the_hints = hints
            else:
                the_hints = self.hints
    
        # hints should be a list of dicts.  If it's a dict, then the keys give the answer number
        # and each of those dict elements should be called one at a time.
        if isinstance(the_hints, dict):
            for anum, hint in list(the_hints.items()):
                self.check_hint(answer_ids, student_answers, new_cmap, old_cmap, anum=anum, the_hints=hint)
                # print "--> anum=%s, hint=%s, ncm=%s" % (anum, hint, new_cmap.hints)	# for debugging
            return

        if anum is None:
            anum = self.anum
        try:
            aid = answer_ids[anum]
        except Exception as err:
            raise Exception('cannot get answer_ids[%d], answer_ids=%s, new_cmap=%s, err=%s' % (self.anum, answer_ids, new_cmap, err))
    
        ans = student_answers[aid]
    
        # for debugging
        #new_cmap.set_hint_and_mode(aid, "hello world", 'always')
        #return
    
        htypes = {'val': partial(self.hint_check_val, ans),
                  'range': partial(self.hint_check_range, ans),
                  'magdif': partial(self.hint_check_magdif, ans),
                  'string': partial(self.hint_check_string, ans),
                  'symbol': partial(self.hint_check_symbol, ans),
                  'func': partial(self.hint_check_function_used, ans),
                  'formula': partial(self.hint_check_formula, ans),
                  'parens': partial(self.hint_check_unbalanced_parens, ans),
                  'isnum': partial(self.hint_check_numerical, ans),
                  'debug': None,
                  'eval': None,
              }
        if self.extra_hint_functions is not None:
            for key, ehf in list(self.extra_hint_functions.items()):
                htypes[key] = partial(ehf, ans)
    
        # print "using the_hints = %s" % the_hints
        the_hint = None
        for hintinfo in the_hints:
            for htype, hfun in list(htypes.items()):
                if htype in hintinfo:
                    try:
                        term = hintinfo[htype]
                        if htype=='eval':
                            ret = eval(term, htypes)	# evaluate the expression - can have function calls in it!
                        elif htype=='debug':
                            ret = True
                        else:
                            ret = hfun(term)
                        if htype=='debug':
                            hintinfo['hint'] = "Answer submitted=%s" % ans
                        if ret:
                            the_hint = hintinfo['hint']
                            if '<font' not in the_hint:
                                the_hint = ('<font color="%s">' % self.color) + the_hint + '</font>'
                            # return on first matching hint
                            new_cmap.set_hint_and_mode(aid, the_hint, 'always')
                            return
                    except Exception as err:
                        if self.do_not_catch_exceptions:
                            raise
                        if self.verbose_fail:
                            raise Exception("Error %s checking hint %s ans=%s, term=%s" % (err, htype, ans, term))


