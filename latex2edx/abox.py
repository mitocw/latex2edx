#!/usr/bin/env python
#
# Answer Box class
#
# object representation of abox, used in Tutor2, now generalized to latex and word input formats.
# 13-Aug-12 ichaung: merge in sari's changes
# 13-Aug-12 ichuang: cleaned up, does more error checking, includes stub for shortanswer
#                    note that shortanswer can be implemented right now using customresponse and textbox
# 04-Sep-12 ichuang: switch from shlex to FSM, merge in changes for math and inline from 8.21
# 13-Oct-12 ichuang: remove csv entirely, use FSM for splitting options instead
# 20-Jan-13 ichuang: add formularesponse
# 23-Jan-13 ichuang: add multiple-line customresponse, with proper inline and math handling

import os, sys, string, re
import hashlib	# for unique abox ID
# import shlex	# for split keeping quoted strings intact
# import csv	# for splitting quoted options

from lxml import etree


class AnswerBox(object):
    def __init__(self, aboxstr, config=None, context=None, verbose=False):
        '''
        Parse a TUT abox and produce edX XML for a problem responsetype.

        Examples:
        -----------------------------------------------------------------------------
        <abox type="option" expect="float" options=" ","noneType","int","float" />
        
        <optionresponse>
        <optioninput options="('noneType','int','float')"  correct="int">
        </optionresponse>
        
        -----------------------------------------------------------------------------
        <abox type="string" expect="Michigan" options="ci" />
        
        <stringresponse answer="Michigan" type="ci">
        <textline size="20" />
        </stringresponse>
        
        -----------------------------------------------------------------------------
        <abox type="custom" expect="(3 * 5) / (2 + 3)" cfn="eq" />
        
        <customresponse cfn="eq">
        <textline size="40" correct_answer="(3 * 5) / (2 + 3)"/><br/>
        </customresponse>
        
        -----------------------------------------------------------------------------
        <abox type="custom" expect="20" answers="11","9" prompts="Integer 1:","Integer 2:" inline="1" cfn="test_add" />

        <customresponse cfn="test_add" expect="20" inline="1">
            <p style="display:inline">Integer 1:<textline correct_answer="11" inline="1"/></p>
            <br/>
            <p style="display:inline">Integer 2:<textline correct_answer="9" inline="1"/></p>
        </customresponse>

        -----------------------------------------------------------------------------
        <abox type="jsinput" expect="(3 * 5) / (2 + 3)" cfn="eq" gradefn="gradefn" height="500"
               get_statefn="getstate" set_statefn="setstate" html_file="/static/jsinput.html"/>
        
        <customresponse cfn="eq" expect="(3 * 5) / (2 + 3)">
            <jsinput gradefn="gradefn"
                height="500"
                get_statefn="getstate"
                set_statefn="setstate"
                html_file="/static/jsinput.html"/>
        </customresponse>
        
        -----------------------------------------------------------------------------
        <abox type="numerical" expect="3.141" tolerance="5%" />
        
        <numericalresponse answer="5.0">
        <responseparam type="tolerance" default="5%" name="tol" description="Numerical Tolerance" />
        <textline />
        </numericalresponse>
        
        -----------------------------------------------------------------------------
    <abox type="multichoice" expect="Yellow" options="Red","Green","Yellow","Blue" />

        <multiplechoiceresponse direction="vertical" randomize="yes">
         <choicegroup type="MultipleChoice">
            <choice location="random" correct="false" name="red">Red</choice>
            <choice location="random" correct="true" name="green">Green</choice>
            <choice location="random" correct="false" name="yellow">Yellow</choice>
            <choice location="bottom" correct="false" name="blue">Blue</choice>
         </choicegroup>
        </multiplechoiceresponse>
        -----------------------------------------------------------------------------
    <abox type="oldmultichoice" expect="1","3" options="0","1","2","3","4" />

        <choiceresponse>
          <checkboxgroup>
            <choice correct="false"><text>0</text></choice>
            <choice correct="true"><text>1</text></choice>
            <choice correct="false"><text>2</text></choice>
            <choice correct="true"><text>3</text></choice>
            <choice correct="false"><text>4</text></choice>
          </checkboxgroup>
        </choiceresponse>
        -----------------------------------------------------------------------------
        <abox type="formula" expect="m*c^2" samples="m,c@1,2:3,4#10" intype="cs" size="40" math="1" tolerance="0.01" feqin="1" />

        format of samples:  <variables>@<lower_bounds>:<upper_bound>#<num_samples

        * variables    - a set of variables that are allowed as student input
        * lower_bounds - for every variable defined in variables, a lower
                         bound on the numerical tests to use for that variable
        * upper_bounds - for every variable defined in variables, an upper
                         bound on the numerical tests to use for that variable

        if feqin is given as an attribute, then a formulaequationinput is used instead
        of textline, for the input element.

        <formularesponse type="cs" samples="m,c@1,2:3,4#10" answer="m*c^2">
            <responseparam type="tolerance" default="0.01"/>
            <textline size="40" math="1" />
        </formularesponse>

        -----------------------------------------------------------------------------
        Adaptive hints:
        
        define the hints as a dict in an included python script, and give the name
        of that dict as the parameter "hints".  Works inside customresponse,
        optionresponse, and multiple choice problems, within latex2edx.
        
        latex2edx automatically translates <ed_general_hint_system/> into an import
        of the general_hint_system.py python code.

        Thus, this input:

        <abox type="custom" expect="(3 * 5) / (2 + 3)" cfn="eq" hints="hint1"/>
        
        produces:

        <edx_general_hint_system />

        <script type="text/python">
        do_hints_for_hint1 = HintSystem(hints=hint1).check_hint
        </script>

        <customresponse cfn="eq">
        <textline size="40" correct_answer="(3 * 5) / (2 + 3)"/><br/>
        <hintgroup hintfn="do_hints_for_hint1">
        </customresponse>

        -----------------------------------------------------------------------------
        Unit tests:

        Unit tests for answer boxes can be generated with latex2edx and aboxes, by using
        arguments test_pass, test_fail, and test_spec, e.g.

        \edXabox{type="custom" expect=10 cfn=mytest test_fail=12 test_pass=10}

        should generate two unit test caes for the answer box - one which is expected 
        to be graded "incorrect" (the test_fail case), and one which is expected
        to be graded "correct" (the test_pass case).

        -----------------------------------------------------------------------------

        context is used for error reporting, and provides context like the line number and
        filename where the abox is located.

        '''
        self.aboxstr = aboxstr
        self.context = context
        self.verbose = verbose
        self.tests = []
        self.has_test_pass = False
        if config is None:
            self.config = {}
        else:
            self.config = config
        self.xml = self.abox2xml(aboxstr)
        self.xmlstr_no_hints = etree.tostring(self.xml)
        self.xmlstr = self.hint_extras + self.xmlstr_no_hints
        self.xmlstr_no_hints = self.xmlstr_no_hints.strip()	# cannonicalize, since it's may be used as a key 
        
    def abox2xml(self, aboxstr):
        if aboxstr.startswith('abox '): aboxstr = aboxstr[5:]
        s = aboxstr
        s = s.replace(' in_check= ', ' ')

        # unique ID for this abox, using hash
        try:
            aboxid = hashlib.sha1(aboxstr).hexdigest()[:10]
        except Exception as err:
            aboxid = hashlib.sha1(aboxstr.encode('utf8')).hexdigest()[:10]

        # parse answer box arguments into dict
        abargs = self.abox_args(s)
        self.abargs = abargs

        type2response = {'custom': 'customresponse',
                         'external': 'externalresponse',
                         'code': 'coderesponse',
                         'oldmultichoice': 'choiceresponse',
                         'multichoice': 'multiplechoiceresponse',
                         'numerical': 'numericalresponse',
                         'option': 'optionresponse',
                         'formula': 'formularesponse',
                         'shortans': 'shortanswerresponse',
                         'shortanswer': 'shortanswerresponse',
                         'string': 'stringresponse',
                         'symbolic': 'symbolicresponse',
                         'image': 'imageresponse',
                         'jsinput': 'customresponse_jsinput',
                         'config': 'config',	# special for setting default config parameters
                         }

        if 'type' in abargs and abargs['type'] in type2response:
            abtype = type2response[abargs['type']]
        elif 'tests' in abargs:
            abtype = 'externalresponse'
        elif 'type' not in abargs and 'options' in abargs:
            abtype = 'optionresponse'
        elif 'cfn' in abargs:
            abtype = 'customresponse'
        else:
            abtype = 'symbolicresponse'  # default
        
        abxml = etree.Element(abtype)
        script_code = None

        # if config specifies default parameters for this type of answer box, then use them
        if abtype in self.config:
            for k,v in self.config[abtype].iteritems():
                if k not in self.abargs:
                    self.abargs[k] = v
            print "abargs = ", abargs

        if abtype == 'optionresponse':
            self.require_args(['expect'])
            oi = etree.Element('optioninput')
            optionstr, options = self.get_options(abargs)
            expected = self.stripquotes(abargs['expect'])
            oi.set('options', optionstr)
            oi.set('correct', expected)
            abxml.append(oi)
            self.copy_attrib(abargs, 'inline', abxml)
            self.copy_attrib(abargs, 'inline', oi)
            try:
                expect_idx = options.index(expected)
            except Exception as err:
                raise Exception("[abox] Error: expected=%s is not one of the options=%s for aboxstr=%s" % (expected, options, aboxstr))
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': [expected],
                                   'expected': ['correct'],
                                   })
            
        if abtype == 'multiplechoiceresponse':
            self.require_args(['expect', 'options'])
            cg = etree.SubElement(abxml, 'choicegroup')
            cg.set('direction', 'vertical')
            optionstr, options = self.get_options(abargs)
            expectstr, expectset = self.get_options(abargs, arg='expect')
            cnt = 1
            correctset = []
            for op in options:
                choice = etree.SubElement(cg, 'choice')
                choice.set('correct', 'true' if op in expectset else 'false')
                choice.set('name', str(cnt))
                choice.append(etree.XML("<text> %s</text>" % op))
                if op in expectset:
                    correctset.append(cnt)
                cnt += 1
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': ["choice_%d" % x for x in correctset],
                                   'expected': ['correct'] * len(correctset),
                                   })
            
        if abtype == 'choiceresponse':
            self.require_args(['expect', 'options'])
            cg = etree.SubElement(abxml, 'checkboxgroup')
            optionstr, options = self.get_options(abargs)
            expectstr, expects = self.get_options(abargs, 'expect')
            cnt = 1
            correctset = []
            if self.verbose:
                print "[abox.py] oldmultichoice: options=/%s/, expects=/%s/" % (options, expects)
            for op in options:
                choice = etree.SubElement(cg, 'choice')
                choice.set('correct', 'true' if (op in expects) else 'false')
                choice.set('name', str(cnt))
                choice.append(etree.XML("<text>%s</text>" % op))
                if op in expects:
                    correctset.append(cnt)
                cnt += 1
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': ["choice_%d" % x for x in correctset],
                                   'expected': ['correct'] * len(correctset),
                                   })

        elif abtype == 'shortanswerresponse':
            print "[latex2html.abox] Warning - short answer response quite yet implemented in edX!"
            if 1:
                tb = etree.Element('textbox')
                self.copy_attrib(abargs, 'rows', tb)
                self.copy_attrib(abargs, 'cols', tb)
                abxml.append(tb)
                abxml.tag = 'customresponse'
                self.require_args(['expect', 'cfn'])
                abxml.set('cfn', self.stripquotes(abargs['cfn']))
                self.copy_attrib(abargs, 'expect', abxml)
                
            else:
                abxml.tag = 'stringresponse'    # change to stringresponse for now (FIXME)
                tl = etree.Element('textline')
                if 'size' in abargs:
                    tl.set('size', self.stripquotes(abargs['size']))
                else:
                    tl.set('size', '80')
                self.copy_attrib(abargs, 'trailing_text', tl)
                abxml.append(tl)
                abxml.set('answer', 'unknown')
                self.copy_attrib(abargs, 'inline', tl)
                self.copy_attrib(abargs, 'inline', abxml)
            
        elif abtype == 'stringresponse':
            self.require_args(['expect'])
            tl = etree.Element('textline')
            if 'size' in abargs:
                tl.set('size', self.stripquotes(abargs['size']))
            self.copy_attrib(abargs, 'trailing_text', tl)
            abxml.append(tl)
            answer = self.stripquotes(abargs['expect'])
            abxml.set('answer', answer)
            if 'options' in abargs:
                abxml.set('type', self.stripquotes(abargs['options']))
            else:
                abxml.set('type', '')
            self.copy_attrib(abargs, 'inline', tl)
            self.copy_attrib(abargs, 'inline', abxml)
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': [answer],
                                   'expected': ['correct'],
                                   })

        elif abtype == 'customresponse':
            self.require_args(['expect', 'cfn'])
            abxml.set('cfn', self.stripquotes(abargs['cfn']))
            self.copy_attrib(abargs, 'inline', abxml)
            self.copy_attrib(abargs, 'expect', abxml)
            self.copy_attrib(abargs, 'options', abxml)
            if abxml.get('options', ''):
                abxml.set('cfn_extra_args', 'options')  # tells sandbox to include 'options' in cfn call arguments
            if 'answers' not in abargs:
                answers = [self.stripquotes(abargs['expect'])]
            else:   # multiple inputs for this customresponse
                ansstr, answers = self.get_options(abargs, 'answers')
            if 'prompts' in abargs:
                promptstr, prompts = self.get_options(abargs, 'prompts')
            else:
                prompts = ['']
            if not len(prompts) == len(answers):
                msg = "Error: number of answers and prompts must match in:"
                msg += aboxstr
                msg += "\nabox located: %s\n" % self.context
                raise Exception(msg)
                # sys.exit(-1)

            # if wrapclass defined, then use that class to transform "expect" and "ans"
            # before it is processed by cfn
            wrapclass = abargs.get('wrapclass', '')
            if wrapclass:
                code_lines = []
                wid = "wrap_%s" % (aboxid)
                the_import = abargs.get("import", "")
                if the_import:
                    code_lines.append("import %s" % the_import)
                code_lines.append("%s = %s" % (wid, wrapclass))
                orig_answers = answers[:]	# copy of answers
                new_answers = []
                acnt = 0
                # wrap displayed answers
                for ans in answers:
                    acnt += 1
                    aid = "ans_%s_%d" % (aboxid, acnt)
                    code_lines.append("%s = %s.answer('''%s''')" % (aid, wid,ans))
                    new_answers.append("$%s" % aid)
                answers = new_answers

                # wrap expected answer
                expect = abxml.get("expect")
                code_lines.append("expect_%s = %s.answer('''%s''')" % (wid, wid, expect))
                abxml.set("expect", "$expect_%s" % wid)

                # wrap the check function
                code_lines.append("")
                code_lines.append("@%s.grader" % wid)
                code_lines.append("def cfn_%s(expect, ans, **kwargs):" % wid)
                code_lines.append("    return %s(expect, ans, **kwargs)" % abxml.get('cfn'))
                abxml.set("cfn", "cfn_%s" % wid)	# use wrapped check function

                script_code = '\n'.join(code_lines)

            cnt = 0
            for ans, prompt in zip(answers, prompts):
                if 'rows' in abargs:
                    tl = etree.Element('textbox')
                    self.copy_attrib(abargs, 'rows', tl)
                    self.copy_attrib(abargs, 'cols', tl)
                else:
                    tl = etree.Element('textline')
                    self.copy_attrib(abargs, 'size', tl)
                tl.set('correct_answer', ans)
                self.copy_attrib(abargs, 'trailing_text', tl)
                self.copy_attrib(abargs, 'inline', tl)
                self.copy_attrib(abargs, 'math', tl)
                self.copy_attrib(abargs, 'preprocessorClassName', tl)
                self.copy_attrib(abargs, 'preprocessorSrc', tl)
                if prompt:
                    elem = etree.Element('p')
                    if 'inline' in abargs:
                        elem.set('style', 'display:inline')
                    elem.text = prompt + " "
                    elem.append(tl)
                else:
                    elem = tl
                if cnt > 0:
                    abxml.append(etree.Element('br'))   # linebreak between boxes if multiple
                abxml.append(elem)
                cnt += 1

            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': answers,
                                   'expected': ['correct'] * len(answers),
                                   'box_indexes': zip([0]*len(answers), range(len(answers))),
                                   })
                    
        elif abtype == 'customresponse_jsinput':
            abxml.tag = 'customresponse'
            self.require_args(['expect', 'cfn'])
            abxml.set('cfn', self.stripquotes(abargs['cfn']))
            self.copy_attrib(abargs, 'expect', abxml)
            self.copy_attrib(abargs, 'options', abxml)
            if abxml.get('options', ''):
                abxml.set('cfn_extra_args', 'options')  # tells sandbox to include 'options' in cfn call arguments

            js = etree.Element('jsinput')
            jsattribs = ['width', 'height', 'gradefn', 'get_statefn', 'set_statefn', 'html_file', 'sop']
            for jsa in jsattribs:
                self.copy_attrib(abargs, jsa, js)
            abxml.append(js)
                    
        elif abtype == 'externalresponse' or abtype == 'coderesponse':
            if 'url' in abargs:
                self.copy_attrib(abargs, 'url', abxml)
            tb = etree.Element('textbox')
            self.copy_attrib(abargs, 'rows', tb)
            self.copy_attrib(abargs, 'cols', tb)
            self.copy_attrib(abargs, 'mode', tb)
            self.copy_attrib(abargs, 'tabsize', tb)
            self.copy_attrib(abargs, 'tests', abxml)
            self.copy_attrib(abargs, 'queuename', abxml)
            abxml.append(tb)
            if abtype=="coderesponse":
                #
                # sample coderesponse:
                #   <coderesponse queuename="MITx-42.01x">
                #       <textbox rows="10" cols="80" mode="python" tabsize="4"/>
                #       <codeparam>
                #           <initial_display>
                #             # students please write your program here
                #             print ""
                #           </initial_display>
                #           <answer_display>
                #             print "hello world"
                #           </answer_display>
                #           <grader_payload>
                #           {"output": "hello world", "max_length": 2}
                #           </grader_payload>
                #       </codeparam>
                #   </coderesponse>
                #
                cp = etree.SubElement(abxml, "codeparam")
                cp_id = etree.SubElement(cp, "initial_display")
                cp_id.text = abargs.get("initial_display", "")
                cp_ad = etree.SubElement(cp, "answer_display")
                cp_ad.text = abargs.get("answer_display", "")
                cp_gp = etree.SubElement(cp, "grader_payload")
                cp_gp.text = abargs.get("grader_payload", "")
            # turn script to <answer> later

        elif abtype == 'numericalresponse':
            self.require_args(['expect'])
            self.copy_attrib(abargs, 'inline', abxml)
            tl = etree.Element('textline')
            self.copy_attrib(abargs, 'size', tl)
            self.copy_attrib(abargs, 'inline', tl)
            self.copy_attrib(abargs, 'math', tl)
            self.copy_attrib(abargs, 'trailing_text', tl)
            abxml.append(tl)
            self.copy_attrib(abargs, 'options', abxml)
            answer = self.stripquotes(abargs['expect'])
            # NOTE: The edX platform now allows mathematical expressions
            #       and constants in the expect field.
            # try:
            #     x = float(answer)
            # except Exception as err:
            #     if not answer[0] == '$':    # may also be a string variable (starts with $)
            #         print "Error - numericalresponse expects numerical expect value, for %s" % s
            #         raise
            abxml.set('answer', answer)
            rp = etree.SubElement(tl, "responseparam")
            rp.attrib['type'] = "tolerance"
            rp.attrib['default'] = abargs.get('tolerance') or "0.00001"
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': [answer],
                                   'expected': ['correct'],
                                   })
        
        elif abtype == 'formularesponse':
            self.require_args(['expect', 'samples'])
            self.copy_attrib(abargs, 'inline', abxml)

            intype = self.stripquotes(abargs.get('intype', 'cs'))
            abxml.set('type', intype)

            self.copy_attrib(abargs, 'samples', abxml)
            
            if abargs.get('feqin'):
                tl = etree.Element('formulaequationinput')
            else:
                tl = etree.Element('textline')
            self.copy_attrib(abargs, 'trailing_text', tl)
            self.copy_attrib(abargs, 'size', tl)
            self.copy_attrib(abargs, 'inline', tl)
            self.copy_attrib(abargs, 'math', tl)
            self.copy_attrib(abargs, 'preprocessorClassName', tl)
            self.copy_attrib(abargs, 'preprocessorSrc', tl)
            abxml.append(tl)
            answer = self.stripquotes(abargs['expect'])
            abxml.set('answer', answer)
            rp = etree.SubElement(tl, "responseparam")
            rp.attrib['type'] = "tolerance"
            rp.attrib['default'] = abargs.get('tolerance') or "0.00001"
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': [answer],
                                   'expected': ['correct'],
                                   })

        elif abtype == 'symbolicresponse':
            self.require_args(['expect'])
            self.copy_attrib(abargs, 'expect', abxml)
            self.copy_attrib(abargs, 'debug', abxml)
            self.copy_attrib(abargs, 'options', abxml)
            tl = etree.Element('textline')
            self.copy_attrib(abargs, 'inline', tl)
            self.copy_attrib(abargs, 'size', tl)
            self.copy_attrib(abargs, 'preprocessorClassName', tl)
            self.copy_attrib(abargs, 'preprocessorSrc', tl)
            self.copy_attrib(abargs, 'trailing_text', tl)
            abxml.append(tl)
            self.copy_attrib(abargs, 'inline', abxml)
            if 'correct_answer' in abargs:
                answer = self.stripquotes(abargs['correct_answer'])
            else:
                answer = self.stripquotes(abargs['expect'])
            tl.set('correct_answer', answer)
            tl.set('math', '1')  # use dynamath
            if not self.has_test_pass:		# generate unit test if no explicit tests specified in abox arguments
                self.tests.append({'responses': [answer],
                                   'expected': ['correct'],
                                   })
            
        elif abtype == 'imageresponse':
            self.require_args(['src', 'width', 'height', 'rectangle'])
            rect = abargs.get('rectangle')
            if re.match('\(\d+\,\d+\)\-\(\d+,\d+\)', rect) is None:  # check for rectangle syntax
                msg = "[abox.py] ERROR: imageresponse rectancle %s has wrong syntax\n" % rect
                msg += "Answer box string is \"%s\"\n" % self.aboxstr
                msg += "abox located: %s\n" % self.context
                raise Exception(msg)
                # sys.exit(-1)
            ii = etree.Element('imageinput')
            self.copy_attrib(abargs, 'src', ii)
            self.copy_attrib(abargs, 'width', ii)
            self.copy_attrib(abargs, 'height', ii)
            self.copy_attrib(abargs, 'rectangle', ii)
            abxml.append(ii)

        elif abtype=="config":
            '''
            Special case, used to set default configuration parameters.  Usage:

            \edXabox{type='config' for="custom" wrapclass="my_wrapper"}
            '''
            abxml = etree.Element("span")	# make this empty
            cfor = abargs.get('for')
            if cfor and cfor in type2response:
                params = abargs.copy()
                params.pop('type')
                params.pop('for')
                self.config[type2response[cfor]] = params
                print "[abox.py] Setting default parameters for %s to %s" % (cfor, params)
 
        # has hint function?
        if 'hintfn' in abargs:
            hintfn = self.stripquotes(abargs['hintfn'])
            hintgroup = etree.SubElement(abxml, 'hintgroup')
            hintgroup.set('hintfn', hintfn)

        # has hint?
        hint_extras = ''
        if 'hints' in abargs:
            hints = self.stripquotes(abargs['hints'])
            hintfn = "do_hints_for_%s" % hints
            hintgroup = etree.SubElement(abxml, 'hintgroup')
            hintgroup.set('hintfn', hintfn)
            hint_extras = "<edx_general_hint_system />\n"
            hint_extras += '<script type="text/python">\n%s = HintSystem(hints=%s).check_hint\n</script>\n' % (hintfn, hints)
        self.hint_extras = hint_extras

        xml_str = etree.tostring(abxml, pretty_print=True)
        xml_str = re.sub('(?ms)<html>(.*)</html>', '\\1', xml_str)
        # print s

        if script_code:
            code_str = '<script type="text/python" system_path="python_lib">\n'
            code_str += "<![CDATA[\n"
            code_str += script_code
            code_str += "\n]]>\n</script>\n"
            xml_str = "<span>%s\n%s</span>" % (xml_str, code_str)
            print "script code!"
            print xml_str

        the_xml = etree.XML(xml_str)

        return the_xml

    def get_options(self, abargs, arg='options'):
        optstr = abargs[arg]			# should be double quoted strings, comma delimited
        # EVH 01-22-2015: Inserting quotes around single option for proper
        # parsing of choices containing commas
        if not optstr.startswith('"') and not optstr.startswith("'"):
            optraw = repr(optstr)
            optstr = optraw[0] + optstr + optraw[0]
        options = split_args_with_quoted_strings(optstr, lambda(x): x == ',')		# turn into list of strings
        options = map(self.stripquotes, options)
        options = [x.strip() for x in options]		# strip strings
        if "" in options: options.remove("")
        optionstr = ','.join(["'%s'" % x for x in options])  # string of single quoted strings
        optionstr = "(%s)" % optionstr				# enclose in parens
        return optionstr, options
    
    def require_args(self, argnames):
        for argname in argnames:
            if argname not in self.abargs:
                msg = "============================================================\n"
                msg += "Error - abox requires %s argument\n" % argname
                msg += "Answer box string is \"%s\"\n" % self.aboxstr
                msg += "abox located: %s\n" % self.context
                # raise Exception, "Bad abox"
                raise Exception(msg)
                # sys.exit(-1)
            
    def process_test_arg(self, key, val):
        '''
        Record a unit test case.  These are specified by arguments like test_pass=...
        test_fail=..., test_spec=...
        '''
        test_args = map(self.stripquotes, split_args_with_quoted_strings(val, lambda(x): x == ','))
        test_args = map(self.unescape, test_args)
        if key=="test_spec":
            nargs = len(test_args)
            if not (nargs&1==0):
                raise Exception("[abox] test_spec must be given with an even number of subarguments, specifying equal number of responses and expected grader outputs")
            responses = test_args[:nargs/2]
            expected = test_args[nargs/2:]
            if 'correct' in expected:
                self.has_test_pass = True
        elif key=="test_pass":
            responses = test_args
            expected = "correct"
            self.has_test_pass = True
        elif key=="test_fail":
            responses = test_args
            expected = "incorrect"
        else:
            raise Exception("[abox] unknown test argument key %s" % key)
        test = {'responses': responses, 
                'expected': expected,
                'box_indexes': zip([0]*len(responses), range(len(responses))),
        }
        self.tests.append(test)

    def unescape(self, str):
        '''
        Unescape string which has been escaped for XML attribute encoding.
        Specifically, 
            &amp; -> &      &gt; -> >      &lt; -> <    
        '''
        return str.replace('&amp;', '&').replace('&gt;', '>').replace('&lt;', '<')

    def abox_args(self, s):
        '''
        Parse arguments of abox.  Splits by space delimitation.

        Test-spec argument keys are handled specially: test_*=...
        Arguments with those keys are stored in self.tests ; they may be used
        by the caller to construct answer box unit tests and course unit tests.
        '''
        s = s.replace(u'\u2019', "'")
        try:
            s = str(s)
        except Exception, err:
            print "Error %s in obtaining string form of abox argument %s" % (err, s)
            return {}
        try:
            # abargstxt = shlex.split(s)
            abargstxt = split_args_with_quoted_strings(s)
        except Exception, err:
            print "Error %s in parsing abox argument %s" % (err, s)
            return {}

        if '' in abargstxt:
            abargstxt.remove('')

        abargs = {}
        try:
            for key, val in [x.split('=', 1) for x in abargstxt]:
                if key.startswith("test_"):
                    self.process_test_arg(key, val)
                else:
                    abargs[key] = val
        except Exception, err:
            print "Error %s" % err
            print "Failed in parsing args = %s" % s
            print "abargstxt = %s" % abargstxt
            raise

        for arg in abargs:
            abargs[arg] = self.stripquotes(abargs[arg], checkinternal=True)

        return abargs

    def stripquotes(self, x, checkinternal=False):
        if x.startswith('"') and x.endswith('"'):
            if checkinternal and '"' in x[1:-1]:
                return x
            return x[1:-1]
        if x.startswith("'") and x.endswith("'"):
            return x[1:-1]
        return x

    def copy_attrib(self, abargs, aname, xml):
        if aname in abargs:
            xml.set(aname, self.stripquotes(abargs[aname]))

        
def split_args_with_quoted_strings(command_line, checkfn=None):
    """from pexpect.py
    This splits a command line into a list of arguments. It splits arguments
    on spaces, but handles embedded quotes, doublequotes, and escaped
    characters. It's impossible to do this with a regular expression, so I
    wrote a little state machine to parse the command line. """

    arg_list = []
    arg = ''

    if checkfn is None:
        def checkfn(c):
            return c.isspace()

    # Constants to name the states we can be in.
    state_basic = 0
    state_esc = 1
    state_singlequote = 2
    state_doublequote = 3
    # The state when consuming whitespace between commands.
    state_whitespace = 4
    state = state_basic

    for c in command_line:
        if state == state_basic or state == state_whitespace:
            if c == '\\':
                # Escape the next character
                state = state_esc
            elif c == r"'":
                # Handle single quote
                arg = arg + c
                state = state_singlequote
            elif c == r'"':
                # Handle double quote
                arg = arg + c
                state = state_doublequote
            elif checkfn(c):                  # OLD: c.isspace():
                # Add arg to arg_list if we aren't in the middle of whitespace.
                if state == state_whitespace:
                    # Do nothing.
                    None
                else:
                    arg_list.append(arg)
                    arg = ''
                    state = state_whitespace
            else:
                arg = arg + c
                state = state_basic
        elif state == state_esc:
            arg = arg + c
            state = state_basic
        elif state == state_singlequote:
            if c == r"'":
                arg = arg + c
                state = state_basic
            else:
                arg = arg + c
        elif state == state_doublequote:
            if c == r'"':
                arg = arg + c
                state = state_basic
            else:
                arg = arg + c

    if arg != '':
        arg_list.append(arg)
    return arg_list

#-----------------------------------------------------------------------------

def test_abox1():
    ab = AnswerBox('type="option" expect="float" options=" ","noneType","int","float"')
    print ab.xmlstr
    assert('''<optioninput options="('noneType','int','float')" correct="float"/>''' in ab.xmlstr)

def test_abox2():
    config = {}
    ab = AnswerBox('type="config" for="custom" wrapclass=mywrap.wrap(debug=True) import=mywrap', config=config)
    print ab.xmlstr
    print "config=%s" % config
    assert('''<span/>''' in ab.xmlstr)
    assert('customresponse' in config)

    ab = AnswerBox('type="custom" expect=10 cfn=mytest', config=config)
    print ab.xmlstr
    assert('''def cfn_wrap_''' in ab.xmlstr)

    # unset defaults
    ab = AnswerBox('type="config" for="custom"', config=config)
    print ab.xmlstr
    print "config=%s" % config
    assert('''<span/>''' in ab.xmlstr)
    assert('customresponse' in config)

    ab = AnswerBox('type="custom" expect=10 cfn=mytest', config=config)
    print ab.xmlstr
    assert('''def cfn_wrap_''' not in ab.xmlstr)

def test_abox_unit_test1():
    ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10')
    assert(ab.tests[0]['responses']==['10'])

def test_abox_unit_test2():
    ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10 test_fail=3')
    assert(len(ab.tests)==2)
    assert(ab.tests[0]['responses']==['10'])

def test_abox_unit_test3():
    the_err = None
    try:
        ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10 test_fail=3 test_bad=5')
    except Exception as err:
        the_err = err
    assert "unknown test argument key" in str(the_err)

def test_abox_unit_test4():
    ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=10 test_fail=3 test_pass=11')
    print ab.tests
    assert(len(ab.tests)==3)
    assert(ab.tests[2]['responses']==['11'])
    assert(ab.tests[2]['expected']=='correct')

def test_abox_unit_test5():
    ab = AnswerBox('type="custom" expect=10 cfn=mytest test_spec=12,incorrect')
    assert(ab.tests[0]['responses']==['12'])
    assert(ab.tests[0]['expected']==['incorrect'])

def test_abox_unit_test6():
    ab = AnswerBox('type="custom" expect=10 cfn=mytest test_spec=12,10,incorrect,correct')
    assert(ab.tests[0]['responses']==['12',"10"])
    assert(ab.tests[0]['expected']==['incorrect',"correct"])

def test_abox_mc_ut1():
    ab = AnswerBox('type="multichoice" options="green","blue","red" expect="blue"')
    print ab.xmlstr
    assert('choicegroup' in ab.xmlstr)
    assert(ab.tests[0]['responses']==['choice_2'])
    assert(ab.tests[0]['expected']==['correct'])

def test_abox_mc_ut2():
    ab = AnswerBox('type="oldmultichoice" options="green","blue","red" expect="blue","red"')
    print ab.xmlstr
    assert('checkboxgroup' in ab.xmlstr)
    assert(ab.tests[0]['responses']==['choice_2', 'choice_3'])
    assert(ab.tests[0]['expected']==['correct', 'correct'])

def test_abox_option_ut1():
    ab = AnswerBox('type="option" options="green","blue","red" expect="blue"')
    print ab.xmlstr
    assert('optionresponse' in ab.xmlstr)
    assert(ab.tests[0]['responses']==['blue'])
    assert(ab.tests[0]['expected']==['correct'])
    
def test_abox_option_ut2():
    the_err = None
    try:
        ab = AnswerBox('type="option" options="green","blue","red" expect="orange"')
    except Exception as err:
        the_err = err
    assert("orange is not one of the options" in str(the_err))
    
def test_abox_custom_ut1():
    ab = AnswerBox('type="custom" expect="20" answers="11","9" prompts="Integer 1:","Integer 2:" inline="1" cfn="test_add"')
    assert('customresponse' in ab.xmlstr)
    assert(len(ab.tests)==1)
    assert(ab.tests[0]['responses']==['11', '9'])
    assert(ab.tests[0]['expected']==['correct', 'correct'])

def test_abox_custom_ut2():
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

    
