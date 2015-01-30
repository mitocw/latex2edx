'''
Test various answer box types for proper XML rendering by `latex2edx/abox.py`
'''
from latex2edx.abox import AnswerBox
import unittest


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
        print xmlstr
        self.assertIn('''<optioninput options="('noneType','int','float')" '''
                      '''correct="int"/>''', xmlstr)

    def test_string1(self):
        '''
        Test a string response with default settings
        '''
        abox = AnswerBox('type="string" expect="Michigan" size="20"')
        xmlstr = abox.xmlstr
        print xmlstr
        self.assertIn('<textline size="20"/>', xmlstr)
        self.assertIn('<stringresponse answer="Michigan" type="">', xmlstr)

    def test_string2(self):
        '''
        Test a string response with additional options
        '''
        abox = AnswerBox('type="string" expect="Michigan" size="20" options="ci regexp"')
        xmlstr = abox.xmlstr
        print xmlstr
        self.assertIn('<stringresponse answer="Michigan" type="ci regexp">', xmlstr)

    def test_numerical1(self):
        '''
        Test numerical response type
        '''
        abox = AnswerBox('''expect="3.14159" type="numerical" tolerance='0.01' inline=1''')
        xmlstr = abox.xmlstr
        print xmlstr
        self.assertIn('<numericalresponse inline="1" answer="3.14159">', xmlstr)
        self.assertIn('<textline inline="1">', xmlstr)
        self.assertIn('<responseparam type="tolerance" default="0.01"/>', xmlstr)

    def test_formula1(self):
        '''
        Test formula response
        '''
        abox = AnswerBox("""expect="(-b + sqrt(b^2-4*a*c))/(2*a)" type="formula" """ +
                         """samples="a,b,c@1,16,1:3,20,3#50" size="60" tolerance='0.01' inline='1' """ +
                         """math="1" feqin="1" """)
        xmlstr = abox.xmlstr
        print xmlstr
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
        print xmlstr
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
        print xmlstr
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
        print xmlstr
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
        print xmlstr
        self.assertIn('<customresponse cfn="sumtest" inline="1" '
                      'expect="test">', xmlstr)
        self.assertIn('<textbox rows="30" cols="80" correct_answer="test" '
                      'inline="1"/>', xmlstr)

if __name__ == '__main__':
    unittest.main()
