import os
import unittest
from io import StringIO

from latex2edx.main import latex2edx
from latex2edx.test.util import make_temp_directory
from latex2edx.course_tests import AnswerBoxUnitTest, CourseUnitTestSet

class TestCourseUnitTests(unittest.TestCase):

    def test_latex2edx_cutset1(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''\begin{edXproblem}{A problem}{url_name="a_problem"}
    
                   \edXabox{type="option" options="red","green","blue" expect="red"}
    
                   \end{edXproblem}'''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xhtml = l2e.xhtml
            assert('<optionresponse' in  xhtml)
    
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 1)
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(cutset.tests[0].responses, ["red"])
            self.assertEqual(cutset.tests[0].expected, ["correct"])

    def test_latex2edx_cutset1a(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''\begin{edXproblem}{A problem}{url_name="a_problem"}
    
                   \edXabox{type="option" options="red","green","blue" expect="red" test_fail="green"}
    
                   \end{edXproblem}'''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xhtml = l2e.xhtml
            assert('<optionresponse' in  xhtml)
    
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 2)
            self.assertEqual(cutset.tests[1].url_name, "a_problem")
            self.assertEqual(cutset.tests[1].responses, ["red"])
            self.assertEqual(cutset.tests[1].expected, ["correct"])
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(cutset.tests[0].responses, ["green"])
            self.assertEqual(cutset.tests[0].expected, "incorrect")

    def test_latex2edx_cutset1b(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''\begin{edXproblem}{A problem}{url_name="a_problem"}
    
                   \edXabox{type="option" options="<red>","green","blue" expect="<red>" 
                            test_pass="<ruby>" test_fail="<green>"}
    
                   \end{edXproblem}'''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 2)
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(cutset.tests[0].responses, ["<ruby>"])
            self.assertEqual(cutset.tests[0].expected, "correct")

    def test_latex2edx_cutset2(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''
                   \begin{edXproblem}{A problem}{url_name="a_problem"}

                   \edXabox{type="option" options="red","green","blue" expect="red"}
                   \end{edXproblem}

                   \begin{edXproblem}{A problem 2}{url_name="a_problem2"}

                   \edXabox{type="custom" expect="red" cfn="mytest"}
                   \end{edXproblem}
            '''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xhtml = l2e.xhtml
            assert('<optionresponse' in  xhtml)
    
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 2)
            self.assertEqual(cutset.tests[1].url_name, "a_problem2")
            self.assertEqual(cutset.tests[1].responses, ["red"])
            self.assertEqual(cutset.tests[1].expected, ["correct"])

    def test_latex2edx_cutset3(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''
                   \begin{edXproblem}{A problem with two aboxes}{url_name="a_problem"}

                   \edXabox{type="option" options="red","green","blue" expect="red"}

                   \edXabox{type="custom" expect="42" cfn="mytest"}
                   \end{edXproblem}
            '''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xhtml = l2e.xhtml
            assert('<optionresponse' in  xhtml)
    
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 1)
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(cutset.tests[0].responses, ["red", "42"])
            self.assertEqual(cutset.tests[0].expected, ["correct", "correct"])

    def test_latex2edx_cutset4(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''
                   \begin{edXproblem}{A problem with two aboxes}{url_name="a_problem"}

                   \edXabox{type="option" options="red","green","blue" expect="red" test_pass="red" test_fail="green"}

                   \edXabox{type="custom" expect="42" cfn="mytest" test_fail="11" test_pass="42"}
                   \end{edXproblem}
            '''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xhtml = l2e.xhtml
            assert('<optionresponse' in  xhtml)
    
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 4)
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(cutset.tests[0].responses, ["red", "11"])
            self.assertEqual(cutset.tests[0].expected, ["correct", "incorrect"])

    def test_latex2edx_cutset5(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''\begin{edXproblem}{A problem}{url_name="a_problem"}
    
                   \edXabox{type="option" options="red","green","blue" expect="red"}
    
            \edXinline{What is $n$ for $C^\perp$?~} \edXabox{type=symbolic size=10 expect="3"  inline="1"}

            \edXinline{$d(C) = $} \edXabox{type=numerical size=10 expect="5" inline="1"}

            \edXinline{$\Delta t = $} \edXabox{type="custom" expect="pi" cfn=sympy_formula_check inline="1"}

            \edXinline{$\Delta t = $} \edXabox{type="formula" expect="pi" inline="1" samples='pi@1:10#10'}

                   \end{edXproblem}'''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 1)
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(len(cutset.tests[0].responses), 5)

    def test_latex2edx_cutset_wrap1(self):
        with make_temp_directory() as tmdir:
            os.chdir(tmdir)
            ofn = "testcuts.yaml"
            tex = r'''
                   \begin{edXproblem}{A problem with wrapped abox}{url_name="a_problem"}

\edXinline{$C(ZX) =$} \edXabox{type="custom" size=60 
  expect="[H(1),CNOT(2,1)]" options="nqubits=3" 
  cfn=check_clifford_circuit_eq inline="1"
  wrapclass=subtext2.Subtext(debug=True,sanitize_allow_lists=False) import=subtext2
}
                   \end{edXproblem}
            '''
            l2e = latex2edx(tmdir + '/test.tex', latex_string=tex, add_wrap=True,
                            do_images=False, output_dir=tmdir, output_cutset=ofn)
            xmlstr = l2e.xml
            cutset = CourseUnitTestSet(fn=ofn)
            self.assertEqual(len(cutset.tests), 1)
            self.assertEqual(cutset.tests[0].url_name, "a_problem")
            self.assertEqual(cutset.tests[0].responses, ["[H(1),CNOT(2,1)]"])
            self.assertEqual(cutset.tests[0].expected, ["correct"])

if __name__ == '__main__':
    unittest.main()
