'''
Representation of unit tests for answer boxes in edX-platform courses, together with a
representation of a full set of such tests for a course.
'''

import yaml
import os

class AnswerBoxUnitTest(object):
    '''
    Representation of a single unit test for an answer box.
    '''
    SPEC_FIELDS = ['url_name', 'responses', 'expected']
    def __init__(self, test_spec=None, test_name=None):
        '''
        test_spec = dict giving url_name, responses, and expected.
        test_name = name of this test (or, e.g. at least a sequential index number for the test)

        responses   = ordered list of strings, specifying user input for each input in the answer box element
        expected    = either list or single string instance of "correct" or "incorrect" or "error"
        box_indexes = list of (x,y) integer pairs specifying index number of the answer box
                      entry.  This is used to construct the input box ID, which is of the form
                      input_<url_name>_<x>_<y>, where <x> indexes which \abox the input is, and 
                      <y> indexes which input element it is, within a given abox (for aboxes with
                      multiple input boxes).  This list should have the same length as the responses.
                      If box_indices is not provided, then it defaults to 
                                  zip(range(len(responses)), [0]*len(responses))
                      Note that the edX platform seems to start x from 2 (and not 1, or 0), and
                      y from 1.  We stick to the convention that x and y both start at 0, and leave
                      the offsets for edxapi.
        '''
        self.url_name = None
        self.responses = []
        self.expected = []
        self.name = test_name
        self.box_indexes = []
        if test_spec:
            for field in self.SPEC_FIELDS:
                if not field in test_spec:
                    print("Missing %s from test %s" % (field, test_name))
                else:
                    setattr(self, field, test_spec[field])
            self.box_indexes = test_spec.get('box_indexes', self.box_indexes)
        if not isinstance(self.responses, list):
            raise Exception("[AnswerBoxUnitTes] illegel responses=%s -- must be list" % self.responses)
        if isinstance(self.expected, list) and not len(self.expected)==len(self.responses):
            raise Exception("[AnswerBoxUnitTes] mismatched lengths responses=%s ; expected=%s" % (self.responses, self.expected))
        if not self.box_indexes:
            self.box_indexes = list(zip(list(range(len(self.responses))), [0]*len(self.responses)))
        if not len(self.box_indexes)==len(self.responses):
            raise Exception("[AnswerBoxUnitTes] mismatched lengths responses=%s ; box_indexes=%s" % (self.responses, self.box_indexes))

    def __unicode__(self):
        return "[AnswerBoxUnitTest] url_name=%s, responses=%s, expected=%s indexes=%s (%s)" % (self.url_name,
                                                                                               self.responses,
                                                                                               self.expected,
                                                                                               self.box_indexes,
                                                                                               self.name)

    __str__ = __unicode__

    @property
    def expected_as_list(self):
        if not isinstance(self.expected, list):
            return [self.expected] * len(self.responses)
        return self.expected

    def box_indexes_plus(self, offset=1):
        '''
        Return box indexes, with the <x> coordinate incremented by offset
        '''
        return [(x+offset, y) for (x,y) in self.box_indexes]

    @property
    def box_indexes_as_list(self):
        '''
        Return box indexes, as list of lists (instead of as list of tuples).
        Needed so YAML outputs correctly.
        '''
        return [list(x) for x in self.box_indexes]

    @property
    def max_box_x_index(self):
        '''
        Return largest x index of box indexes
        '''
        return max([x[0] for x in self.box_indexes])

    def __add__(self, other):
        assert self.url_name==other.url_name
        both_responses = self.responses + other.responses
        both_expected = self.expected_as_list + other.expected_as_list
        both_name = "combination of %s and %s" % (str(self.name), str(other.name))
        both_indexes = self.box_indexes + other.box_indexes_plus(offset=self.max_box_x_index+1)
        return AnswerBoxUnitTest(dict(url_name=self.url_name,
                                      responses=both_responses,
                                      expected=both_expected,
                                      box_indexes=both_indexes,
                                      name=both_name))

    def as_dict(self):
        '''
        Return dict representation of this AnswerBoxUnitTest object
        '''
        data = dict(url_name=self.url_name, responses=self.responses, expected=self.expected, 
                    box_indexes=self.box_indexes_as_list)
        if self.name:
            data['name'] = self.name
        return data
        

class CourseUnitTestSet(object):
    '''
    Set of tests (AnswerBoxUnitTest objecs), for an edX-platform course.
    '''
    def __init__(self, fn=None, verbose=True, yaml_string=None):
        '''
        fn = name of file to load course unit tests from (defaults to looking for YAML)
        '''
        self.config = {}
        self.tests = []
        self.verbose = verbose
        if fn or yaml_string:
            self.load_tests_from_file(fn=fn, yaml_string=yaml_string)

    def add_tests(self, tests):
        '''
        tests - list of AnswerBoxUnitTest objects
        '''
        for test in tests:
            self.add_test(test)

    def add_test(self, test):
        '''
        test - AnswerBoxUnitTest object
        '''
        if not isinstance(test, AnswerBoxUnitTest):
            raise Exception("[CourseUnitTestSet] add_test: test must be an instance of AnswerBoxUnitTest")
        self.tests.append(test)

    def output_to_file(self, ofn):
        '''
        Write test set to output file in YAML format.
        '''
        cut_spec = {'config': self.config, 'tests': [x.as_dict() for x in self.tests]}
        open(ofn, 'w').write(yaml.dump(cut_spec))

    def load_tests_from_file(self, fn=None, yaml_string=None):
        if fn:
            if not os.path.exists(fn):
                raise Exception("[CourseUnitTestSet] Expecting course unit test config file - but no such file %s" % fn)
            yaml_string = open(fn).read()
        if not yaml_string:
            raise Exception("[CourseUnitTestSet] empty YAML string %s" % yaml_string)
        cut_specs = yaml.load(yaml_string)
        if 'config' in cut_specs:
            self.config = cut_specs['config']
            # self.__dict__.update(cut_specs['config'])
        self.cut_specs = cut_specs
        cnt = 0
        for test in cut_specs.get('tests', []):
            cnt += 1
            abutest = AnswerBoxUnitTest(test, cnt)
            self.tests.append(abutest)
        self.ntests = len(self.tests)
        if self.verbose:
            print("[CourseUnitTestSet] Loaded %s answer box unit tests from %s" % (self.ntests, fn))
            
#-----------------------------------------------------------------------------
# unit tests

def test_abut1():
    abut1 = AnswerBoxUnitTest(dict(responses=["1"], expected="correct", url_name="x"))
    abut2 = AnswerBoxUnitTest(dict(responses=["2"], expected="incorrect", url_name="x"))
    abut3 = abut1 + abut2
    assert abut3.url_name=="x"
    assert abut3.expected==["correct", "incorrect"]
    assert abut3.responses==["1", "2"]

def test_cutset1():
    yaml = """config: {a: 2}
tests:
- expected: [correct]
  name: A problem/test_1
  responses: [red]
  url_name: a_problem
    """
    cutset = CourseUnitTestSet(yaml_string=yaml)
    assert len(cutset.tests)==1
    assert cutset.config['a']==2
    assert cutset.tests[0].expected==['correct']
    assert cutset.tests[0].responses==['red']
    assert cutset.tests[0].url_name=="a_problem"

    abut2 = AnswerBoxUnitTest(dict(responses=["2"], expected="incorrect", url_name="x"))
    cutset.add_tests([abut2])
    assert len(cutset.tests)==2
    
def test_cutset2():
    yaml = """config: {a: 2}
tests:
- expected: [correct]
  name: A problem/test_1
  responses: [red]
  url_name: a_problem
    """
    cutset = CourseUnitTestSet(yaml_string=yaml)
    
    cfn = "/tmp/tmp_cutset.yaml"
    cutset.output_to_file(cfn)

    cutset2 = CourseUnitTestSet(cfn)
    assert len(cutset2.tests)==1
    assert cutset2.config['a']==2
    assert cutset2.tests[0].expected==['correct']
    assert cutset2.tests[0].responses==['red']
    assert cutset2.tests[0].url_name=="a_problem"

    
