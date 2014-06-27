from general_hint_system import *

#-----------------------------------------------------------------------------
# py.test unit tests
    
class TestClass(object):

    class correct_map(object):
        def __init__(self):
            self.hints = {}
            return
        def set_hint_and_mode(self, aid, the_hint, mode):
            self.hints[aid] = the_hint
            self.mode = mode

    hfc = HintFormulaCheck()

    def test_hint_string_and_eval(self):
        hints = [  {'string': 'H', 
                    'hint': 'Your answer should not have H'
                },
                   {'eval': "not string('*')", 
                    'hint': 'Remember to explicitly indicate multiplication with *'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert('should not have H' in ncmap.hints[0])
        assert('explicitly indicate' not in ncmap.hints[0])

        answers = ['ab+cd']
        check_hint(aids, answers, ncmap, ocmap)
        assert('explicitly indicate' in ncmap.hints[0])

    def test_formula_test(self):
        expect, samples = 'x+2!x@1:10#20'.split('!')
        options = "samples='%s'" % samples
        ans = 'x+2'
        ret = self.hfc.check_formula(expect, ans, options=options)
        if not ret['ok']:
            print ret
        assert(ret['ok'])

    def test_check_formula(self):
        HS = HintSystem()
        term = 'x+2!x@1:10#20'
        ans = 'x+2'
        ret = HS.hint_check_formula(ans, term)
        assert(ret)

    def test_hint_formula(self):
        hints = [  {'formula': 'x+2!x@1:10#20', 
                    'hint': 'missing two?'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['x+2']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('missing two' in ncmap.hints[0])

        answers = ['-(x+2-2*x)+4']	# still x+2
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('missing two' in ncmap.hints[0])

    def test_hint_val(self):
        hints = [  {'val': {'expect': '12', 'tolerance': '5%'}, 
                    'hint': 'a hint'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['12*1.04']
        check_hint(aids, answers, ncmap, ocmap)
        print ncmap.hints
        assert('a hint' in ncmap.hints[0])

    def test_hint_string2(self):
        hints = [  {'string': {'regexp': 'ab.*cd'}, 'hint': 'a hint' },
                   {'string': {'nospaces': 'xyz'}, 'hint': 'another hint' },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['cxab syy cd13']
        check_hint(aids, answers, ncmap, ocmap)
        print ncmap.hints
        assert('a hint' in ncmap.hints[0])

        answers = ['asdx y  zbb']
        check_hint(aids, answers, ncmap, ocmap)
        print ncmap.hints
        assert('another hint' in ncmap.hints[0])

    def test_hint_val2(self):
        anum0 = 1/((2*16.3)**2)

        hints = [
            {'parens': '', 'hint': 'Missing parenthesis?'},
            {'val': {'expect': anum0*4, 'tolerance': '10%'}, 'hint': 'Off by factor of two somewhere?'},
            {'magdif': anum0, 'hint': 'You are off by more than two orders of magnitude'},
            ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['1/(16.3*16.3)']
        check_hint(aids, answers, ncmap, ocmap)
        print ncmap.hints
        assert('factor of two' in ncmap.hints[0])

    def test_hint_symbol(self):
        hints = [  {'symbol': 'hbar', 
                    'hint': 'missing hbar'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['x+2']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['2+hbar/3']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('missing hbar' in ncmap.hints[0])

        answers = ['2+hbar_3/3']
        ncmap = self.correct_map()
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

    def test_hint_function(self):
        hints = [  {'symbol': 'hbar', 
                    'hint': 'missing hbar'
                },
                {'func': 'cos', 'hint': 'oscillates'},
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['y + sqrt(cos(x))']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('oscillates' in ncmap.hints[0])

    def test_hint_magdif(self):
        hints = [  {'magdif': {'expect': 3.141, 'max': 2}, 
                    'hint': 'You are more than two orders of magnitude off'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['3e8']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('two orders' in ncmap.hints[0])

    def test_hint_range(self):
        hints = [  {'range': [4, 9],
                    'hint': 'You are out of range'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['3e8']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['5']
        HS.verbose_fail = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('out of range' in ncmap.hints[0])

    def test_hint_parens(self):
        hints = [  {'parens': '',
                    'hint': 'Missing parenthesis?'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['(a+23']
        HS.verbose_fail = True
        HS.do_not_catch_exceptions = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('Missing' in ncmap.hints[0])

        answers = ['2+(3*2+(a+x)']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert('Missing' in ncmap.hints[0])

    def test_hint_isnum(self):
        hints = [  {'isnum': '',
                    'hint': 'not numerical'
                },
               ]
        HS = HintSystem(hints=hints)
        check_hint = HS.check_hint
        HS.verbose_fail = False
        aids = [0]
        answers = ['Hello']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        check_hint(aids, answers, ncmap, ocmap)
        assert(len(ncmap.hints)==0)

        answers = ['23']
        HS.verbose_fail = True
        HS.do_not_catch_exceptions = True
        check_hint(aids, answers, ncmap, ocmap)
        assert('numerical' in ncmap.hints[0])

    def test_hint_symbol2(self):
        '''
        different hints for two different answer boxes
        '''
        hints1 = [  {'string': 'hbar', 'hint': 'why hbar'}, ]
        hints2 = [  {'string': 'hbar', 'hint': 'hello hbar'}, ]
        aids = [0, 1]
        answers = ['Hello hbar', 'world hbar']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        ch1 = HintSystem(anum=0, hints=hints1).check_hint
        ch2 = HintSystem(anum=1, hints=hints2).check_hint
        ch1(aids, answers, ncmap, ocmap)
        print ncmap.hints
        assert('why' in ncmap.hints[0])

        ncmap = self.correct_map()
        ocmap = self.correct_map()
        ch2(aids, answers, ncmap, ocmap)
        assert('hello' in ncmap.hints[1])

    def test_complex_hint1(self):
        '''
        sequence of hints
        '''
        hints2 = [ {'parens': '', 'hint': 'Missing parenthesis?'},
                   {'eval': 'not string("*")',
                    'hint': 'Please indicate multiplication explicitly using *'},
                    {'symbol': 'L', 'hint': 'Should your answer depend on L?'},
                    {'string': 'D^2_eg', 'hint': 'Enter D_eg^2 and not D^2_eg'},
                    {'symbol': 'D', 'hint': 'Enter D_eg and not D'},
                    {'eval': 'not string("hbar")', 'hint': "Are your units correct?"},
                    {'eval': 'string("-")', 'hint': "Are your sign(s) correct?"},
                    ]
        ch2 = HintSystem(anum=0, hints=hints2).check_hint
        aids = [0]
        answers = ['E_0^2*D_eg^2/(2*Delta)']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        ch2(aids, answers, ncmap, ocmap)
        print ncmap.hints[0]
        assert('units correct' in ncmap.hints[0])
        
    def test_multiple_hints1(self):
        '''
        different hints for two different answer boxes, with one hints dict
        '''
        my_hints = {0: [  {'string': 'hbar', 'hint': 'why hbar'}, ],
                    1: [  {'string': 'quux', 'hint': 'hello quux'}, ],
                    }
        aids = [0, 1]
        answers = ['Hello hbar', 'world quux']
        ncmap = self.correct_map()
        ocmap = self.correct_map()
        ch = HintSystem(hints=my_hints).check_hint
        ch(aids, answers, ncmap, ocmap)
        print ncmap.hints
        assert('why' in ncmap.hints[0])
        assert('hello' in ncmap.hints[1])

