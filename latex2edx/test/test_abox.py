'''
Test various answer box types for proper XML rendering by `latex2edx/abox.py`
'''
import re
import json
import unittest
from lxml import etree
from latex2edx.abox import AnswerBox

class Test_Abox(unittest.TestCase):
    '''
    Class Test_Abox inherits the `unittest.TestCase` class and contains
    nine tests for the abox.py script
    '''

    def test_option1(self):
        '''
        Test dropdown option response
        '''
        abox = AnswerBox('type="option" expect="int" options="noneType","int","float"')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('''<optioninput options="('noneType','int','float')" '''
                      '''correct="int"/>''', xmlstr)

    def test_string1(self):
        '''
        Test a string response with default settings
        '''
        abox = AnswerBox('type="string" expect="Michigan" size="20"')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<textline size="20"/>', xmlstr)
        self.assertIn('<stringresponse answer="Michigan" type="">', xmlstr)

    def test_string2(self):
        '''
        Test a string response with additional options
        '''
        abox = AnswerBox('type="string" expect="Michigan" size="20" options="ci regexp"')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<stringresponse answer="Michigan" type="ci regexp">', xmlstr)

    def test_numerical1(self):
        '''
        Test numerical response type
        '''
        abox = AnswerBox('''expect="3.14159" type="numerical" tolerance='0.01' inline=1''')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<numericalresponse inline="1" answer="3.14159">', xmlstr)
        self.assertIn('<textline inline="1">', xmlstr)
        self.assertIn('<responseparam type="tolerance" default="0.01"/>', xmlstr)

    def test_numerical2(self):
        '''
        Test numerical response type with units (the weight of 1 kilogram)
        '''
        abox = AnswerBox('''expect="9.81" type="numerical" tolerance="0.2"
                         inline="1" trailing_text="N"''')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<numericalresponse inline="1" answer="9.81">', xmlstr)
        self.assertIn('<textline inline="1" trailing_text="N">', xmlstr)
        self.assertIn('<responseparam type="tolerance" default="0.2"/>', xmlstr)

    def test_formula1(self):
        '''
        Test formula response
        '''
        abox = AnswerBox("""expect="(-b + sqrt(b^2-4*a*c))/(2*a)" type="formula" """ +
                         """samples="a,b,c@1,16,1:3,20,3#50" size="60" tolerance='0.01' inline='1' """ +
                         """math="1" feqin="1" """)
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<formularesponse inline="1" type="cs" '
                      'samples="a,b,c@1,16,1:3,20,3#50" answer="(-b + '
                      'sqrt(b^2-4*a*c))/(2*a)">', xmlstr)
        self.assertIn('<formulaequationinput size="60" inline="1" math="1">', xmlstr)
        self.assertIn('<responseparam type="tolerance" default="0.01"/>', xmlstr)
        
    def test_oldmultichoice1(self):
        '''
        Test a multiple choice response requiring multiple selections
        '''
        abox = AnswerBox('type="oldmultichoice"  expect="Python","C++" options="Cobol","Pascal","Python","C++","Clu","Forth"')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<choiceresponse>', xmlstr)
        self.assertEqual(abox.xml.tag, 'choiceresponse')
        self.assertEqual(len(abox.xml.findall('.//choice')), 6)
        self.assertIn('<choice correct="true" name="3">', xmlstr)
        self.assertIn('<choice correct="true" name="4">', xmlstr)

    def test_custom1(self):
        '''
        Test a custom response refering to a `sumtest` python script
        '''
        abox = AnswerBox('''expect=""
        type="custom"
        answers="1","9"
        prompts="x = ","y = "
        cfn="sumtest"
        inline="1" ''')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<customresponse cfn="sumtest" inline="1" expect="">', xmlstr)
        self.assertIn('<p style="display:inline">x = <textline '
                      'correct_answer="1" inline="1"/></p>', xmlstr)
        self.assertIn('<p style="display:inline">y = <textline '
                      'correct_answer="9" inline="1"/></p>', xmlstr)
        self.assertIn('<br/>', xmlstr)

    def test_custom2(self):
        '''
        Test a custom response that uses javascript
        '''
        abox = AnswerBox('''expect="" type="jsinput" cfn="test_findep"
        width="650"
        height="555"
        gradefn="getinput"
        get_statefn="getstate"
        set_statefn="setstate"
        html_file="/static/html/ps3plot_btran1.html"''')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<customresponse cfn="test_findep" expect="">', xmlstr)
        self.assertIn('<jsinput width="650" height="555" gradefn="getinput" '
                      'get_statefn="getstate" set_statefn="setstate" '
                      'html_file="/static/html/ps3plot_btran1.html"/>', xmlstr)

    def test_custom3(self):
        '''
        Test a custom response with input formated as a code entry box
        '''
        abox = AnswerBox('''expect="test"
        rows=30 cols=80
        type="custom"
        cfn="sumtest"
        inline="1" ''')
        xmlstr = abox.xmlstr
        print(xmlstr)
        self.assertIn('<customresponse cfn="sumtest" inline="1" '
                      'expect="test">', xmlstr)
        self.assertIn('<textbox rows="30" cols="80" correct_answer="test" '
                      'inline="1"/>', xmlstr)

    def test_abox2_custom_config(self):
        config = {}
        ab = AnswerBox('type="config" for="custom" wrapclass=mywrap.wrap(debug=True) import=mywrap', config=config)
        print(ab.xmlstr)
        print("config=%s" % config)
        assert('''<span/>''' in ab.xmlstr)
        assert('customresponse' in config)
    
        ab = AnswerBox('type="custom" expect=10 cfn=mytest', config=config)
        print(ab.xmlstr)
        assert('''def cfn_wrap_''' in ab.xmlstr)
        assert "span" not in ab.xmlstr_just_code
        assert "span" in ab.xmlstr
    
        # unset defaults
        ab = AnswerBox('type="config" for="custom"', config=config)
        print(ab.xmlstr)
        print("config=%s" % config)
        assert('''<span/>''' in ab.xmlstr)
        assert('customresponse' in config)
    
        ab = AnswerBox('type="custom" expect=10 cfn=mytest', config=config)
        print(ab.xmlstr)
        assert('''def cfn_wrap_''' not in ab.xmlstr)
    
    def test_abox_unit_test1(self):
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10')
        assert(ab.tests[0]['responses']==['10'])
    
    def test_abox_unit_test2(self):
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10 test_fail=3')
        assert(len(ab.tests)==2)
        assert(ab.tests[0]['responses']==['10'])
    
    def test_abox_unit_test3(self):
        the_err = None
        try:
            ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10 test_fail=3 test_bad=5')
        except Exception as err:
            the_err = err
            assert "unknown test argument key" in str(the_err)
    
    def test_abox_unit_test4(self):
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10 test_fail=3 test_pass=11')
        print(ab.tests)
        assert(len(ab.tests)==3)
        assert(ab.tests[2]['responses']==['11'])
        assert(ab.tests[2]['expected']=='correct')
    
    def test_abox_unit_test5(self):
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_spec=12,incorrect')
        assert(ab.tests[0]['responses']==['12'])
        assert(ab.tests[0]['expected']==['incorrect'])
    
    def test_abox_unit_test6(self):
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_spec=12,10,incorrect,correct')
        assert(ab.tests[0]['responses']==['12',"10"])
        assert(ab.tests[0]['expected']==['incorrect',"correct"])
    
    def test_abox_mc_ut1(self):
        ab = AnswerBox('type="multichoice" options="green","blue","red" expect="blue"')
        print(ab.xmlstr)
        assert('choicegroup' in ab.xmlstr)
        assert(ab.tests[0]['responses']==['choice_2'])
        assert(ab.tests[0]['expected']=='correct')
    
    def test_abox_mc_ut2(self):
        ab = AnswerBox('type="oldmultichoice" options="green","blue","red" expect="blue","red"')
        print(ab.xmlstr)
        assert('checkboxgroup' in ab.xmlstr)
        assert(ab.tests[0]['responses']==['choice_2', 'choice_3'])
        assert(ab.tests[0]['expected']=='correct')
    
    def test_abox_option_ut1(self):
        ab = AnswerBox('type="option" options="green","blue","red" expect="blue"')
        print(ab.xmlstr)
        assert('optionresponse' in ab.xmlstr)
        assert(ab.tests[0]['responses']==['blue'])
        assert(ab.tests[0]['expected']==['correct'])
        
    def test_abox_option_ut2(self):
        the_err = None
        try:
            ab = AnswerBox('type="option" options="green","blue","red" expect="orange"')
        except Exception as err:
            the_err = err
            assert("orange is not one of the options" in str(the_err))
        
    def test_abox_custom_ut1(self):
        ab = AnswerBox('type="custom" expect="20" answers="11","9" prompts="Integer 1:","Integer 2:" inline="1" cfn="test_add"')
        assert('customresponse' in ab.xmlstr)
        assert(len(ab.tests)==1)
        assert(ab.tests[0]['responses']==['11', '9'])
        assert(ab.tests[0]['expected']==['correct', 'correct'])
    
    def test_abox_custom_ut2(self):
        ab = AnswerBox('type="custom" expect="20" answers="11","9" prompts="Integer 1:","Integer 2:" inline="1" '
                       'cfn="test_add" test_fail="11","8" test_pass="10","10" '
                       'test_spec="7","13","correct","correct" ')
        assert('customresponse' in ab.xmlstr)
        assert(len(ab.tests)==3)
        assert(ab.tests[0]['responses']==['11', '8'])
        assert(ab.tests[0]['expected']=='incorrect')
        assert(ab.tests[1]['responses']==['10', '10'])
        assert(ab.tests[1]['expected']=='correct')
        assert(ab.tests[2]['responses']==['7', '13'])
        assert(ab.tests[2]['expected']==['correct']*2)
        assert(ab.tests[0]['box_indexes'] == [(0,0), (0,1)])
    
    def check_payload_json(self, xmlstr, expect_dictstr):
        '''
        return True if expect_dict is in grader_payload
        '''
        m = re.search("<grader_payload>(.*)</grader_payload>", xmlstr)
        if not m:
            return False
        dstr = m.group(1)
        data = json.loads(dstr)
        expect = json.loads(expect_dictstr)
        shared_items = {k: data[k] for k in data if k in expect and data[k] == expect[k]}
        return len(shared_items)==len(expect)
    
    def test_multicoderesponse1(self):
        abstr = """\edXabox{expect="." queuename="test-6341" type="multicode" prompts="$\mathtt{numtaps} = $","$\mathtt{bands} = $","$\mathtt{amps} = $","$\mathtt{weights} = $"  answers=".",".",".","." cfn="designGrader" sizes="10","25","25","25" inline="1"}"""
        ab = AnswerBox(abstr)
        xmlstr = etree.tostring(ab.xml)
        print(xmlstr)
        assert ab.xml
        assert self.check_payload_json(ab.xmlstr, '{"debug": true, "grader": "designGrader", "queuename": "test-6341", "options": "", "expect": ""}')
        # assert b'<grader_payload>{"debug": true, "grader": "designGrader", "queuename": "test-6341", "options": "", "expect": ""}</grader_payload>' in xmlstr
        # assert '<grader_payload>{"debug": true, "grader": "designGrader", "options": "", "expect": ""}</grader_payload>' in xmlstr
        assert b'<p style="display:inline">$\mathtt{numtaps} = $<input size="10" style="display:inline" ' in xmlstr
    
    def test_multicoderesponse2(self):
        abstr = """\edXabox{expect="." queuename="test-6341" type="multicode" prompts="$\mathtt{numtaps} = $","$\mathtt{bands} = $","$\mathtt{amps} = $","$\mathtt{weights} = $"  answers=".",".",".","." cfn="designGrader" sizes="10","25","25","25" hidden="abc123" inline="1"}"""
        ab = AnswerBox(abstr)
        xmlstr = etree.tostring(ab.xml)
        print(xmlstr)
        assert ab.xml
        assert b'<span id="abc123"' in xmlstr

    def test_abox_skip_unit_test6(self):
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=""', verbose=True)
        print(ab.tests)
        assert(len(ab.tests)==0)
    
    def test_abox_coderesponse1(self):
        ab = AnswerBox('type="code" rows=30 cols=90 queuename="some_queue" mode="python" answer_display="see text" '
                       'cfn="qis_cfn" debug=1 options="test_opt" expect="test_expect"', verbose=True)
        print(ab.xmlstr)
        # assert """<grader_payload>{"debug": true, "grader": "qis_cfn", "options": "test_opt", "expect": "test_expect"}</grader_payload>""" in ab.xmlstr
        assert self.check_payload_json(ab.xmlstr, '{"debug": true, "grader": "qis_cfn", "options": "test_opt", "expect": "test_expect"}')

    def test_abox_coderesponse2(self):
        ab = AnswerBox('type="code" rows=30 cols=90 queuename="some_queue" mode="python" answer_display="see text" '
                       """grader_payload='{"a":2, "cfn":"test"}' """
                       'cfn="qis_cfn" debug=1 options="test_opt" expect="test_expect"', verbose=True)
        print(ab.xmlstr)
        assert """<grader_payload>{"debug": true, "grader": "qis_cfn", "options": "test_opt", "expect": "test_expect"}</grader_payload>""" not in ab.xmlstr
        assert """<grader_payload>{"a":2, "cfn":"test"}</grader_payload>""" in ab.xmlstr

    def test_abox_multichoice_indexes1(self):
        ab = AnswerBox('''inline=1 type='multichoice' expect="UL","DR" options="None","UL","UR","DL","DR"''')
        assert('choiceresponse' in ab.xmlstr)
        assert(len(ab.tests)==1)
        assert(ab.tests[0]['box_indexes'] == [[0,0], [0,0]])

if __name__ == '__main__':
    unittest.main()
