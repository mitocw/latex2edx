#!/usr/bin/env python
'''
The AnswerBox class provides an internal representation of the \edXabox{}
macro and <abox>...</abox> XML element, used for specifying a query for 
user input, and how the query should be evaluated for correctness, and 
for hints.
'''

import os
import sys
import string
import re
import json
import hashlib
import datetime

from lxml import etree

#-----------------------------------------------------------------------------
# javascript for multicoderesponse and multiexternalresponse

MULTICODE_JS_TEMPLATE = """
                         console.log("Code version %s");

            sync_multicoderesponse_inputs_%s = function(){
                var mcrspan = $("#span_%s");
                sync_multicoderesponse_inputs(mcrspan);
            }

            sync_multicoderesponse_inputs = function(mcrspan){
                console.log("%s mcrspan = ", mcrspan);
                var editor = mcrspan.parent().find(".CodeMirror")[0].CodeMirror;
                console.log("%s textbox editor = ", editor);
                var data = {};
                mcrspan.find(".input_%s").each(function(kidx, elem){
                    var cinput_name = elem.id;
                    var cinput_val = $(elem).val();
                    data[cinput_name] = cinput_val;
                });
                var datastr = JSON.stringify(data);
                editor.setValue(datastr);
                console.log("%s sync data: ", data);
            }

            $(".input_%s").change(sync_multicoderesponse_inputs_%s);

            set_mcr_inputs = function(mcrspan, data){    // for init - set multicoderesponse inputs
                // var mcrspan = $("#span_%s");
                var cnt = 1;
                data.forEach(function(x){
                    mcrspan.find('input.multicode_input_' + cnt).val(x);
                    cnt += 1
                });
                sync_multicoderesponse_inputs(mcrspan);
            }

            set_mcr_inputs_fromdict = function(mcrspan, data){    // for init - set multicoderesponse inputs
                mcrspan.find('input').each(function(k, elem){
                    var cinput_name = elem.id;
                    $(elem).val(data[cinput_name]);
                });
            }

            setup_initial_mcr_inputs_%s = function(){
                var mcrspan = $("#span_%s");
                try { var editor = mcrspan.parent().find(".CodeMirror")[0].CodeMirror; }
                catch (err){  
                    console.log("[setup_initial_mcr_inputs] no editor yet...", err);
                    setTimeout(setup_initial_mcr_inputs_%s, 500);
                    return;
                }
                %s
                if (editor.mcr_inputs_processed){
                    console.log("[setup_initial_mcr_inputs] inputs processed");
                    return;
                }
                var datastr = editor.getValue();
                try { var data = jQuery.parseJSON(datastr); }
                catch (err){
                    console.log("[setup_initial_mcr_inputs] codemirror text unparseable...", err);
                    // setTimeout(setup_initial_mcr_inputs_%s, 500);
                    return;
                }
                set_mcr_inputs_fromdict(mcrspan, data);
            }
        
            setTimeout(setup_initial_mcr_inputs_%s, 500);

            """

#-----------------------------------------------------------------------------

class AnswerBox(object):
    def __init__(self, aboxstr, config=None, context=None, verbose=False):
        '''
        The AnswerBox class provides an internal representation of the \edXabox{}
        macro and <abox>...</abox> XML element, used for specifying a query for 
        user input, and how the query should be evaluated for correctness, and 
        for hints.

        This class ingests the abox aguments, and produces edX XML as output.
        The edX XML representation uses different "capa" problem "response" types,
        to represent various answer box types.  This includes option, numerical, 
        formula, custom, and many other response types.

        This class can also generate data to produce unit tests for the answer 
        boxes, to be used with the edxcut (edX Course Unit Test) package.

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
        multicoderesponse for xqueue problems

        Some custom response problems require longer python code execution time than
        is feasible for a live running open edX instance, within a codejail.  It is 
        therefore desirable to be able to easily convert a custom response problem, and
        its python code, into an asynchronously graded "xqueue" problem.

        This can be accomplished by turning the "custom" abox into a "multicode" 
        problem, and adding some additional metadata, e.g. to specify the queue name.
        This causes the problem to use the edX "coderesponse" box, which sends the
        user input to be graded asynchronously by an "xqueue" grader.  When done, the
        grader's response is then presented to the learner.  Grading can take
        an arbitrarily long time (even days, so in principle it could involve manual
        intervention).

        A coderesponse object has a textarea, though, versus customresponse, which 
        uses textline inputs.  Some HTML and javascript must thus be injected, to 
        present input fields, and to synchronize those fields with its JSON encoded 
        equivalent, in the textarea.  The textarea is hidden from the user.
        
        -----------------------------------------------------------------------------
        multiexternalresponse for externalresponse using multiple input fields

        multiexternalresponse provides for externalresponse what multicoderesponse
        provides for coderesponse.
        
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
        self.xml_just_code = self.xml
        if (self.xml.tag=="span") and len(self.xml)>1:	# xml has script code, and abtype is not config
            self.xml_just_code = self.xml[0]
            
        self.xmlstr = self.hint_extras + etree.tostring(self.xml).decode()
        self.xmlstr_just_code = etree.tostring(self.xml_just_code).strip().decode()
        
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
                         'multicode': 'multicoderesponse',
                         'multiexternal': 'multiexternalresponse',
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
            for k,v in self.config[abtype].items():
                if k not in self.abargs:
                    self.abargs[k] = v
            print("abargs = ", abargs)

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
            self.make_default_test_pass(["choice_%d" % x for x in correctset],
                                        expected="correct",
                                        box_indexes=[[0,0]]*len(correctset))
            
        if abtype == 'choiceresponse':
            self.require_args(['expect', 'options'])
            cg = etree.SubElement(abxml, 'checkboxgroup')
            optionstr, options = self.get_options(abargs)
            expectstr, expects = self.get_options(abargs, 'expect')
            cnt = 1
            correctset = []
            if self.verbose:
                print("[abox.py] oldmultichoice: options=/%s/, expects=/%s/" % (options, expects))
            for op in options:
                choice = etree.SubElement(cg, 'choice')
                choice.set('correct', 'true' if (op in expects) else 'false')
                choice.set('name', str(cnt))
                choice.append(etree.XML("<text>%s</text>" % op))
                if op in expects:
                    correctset.append(cnt)
                cnt += 1
            self.make_default_test_pass(["choice_%d" % x for x in correctset],
                                        expected="correct",
                                        box_indexes=[[0,0]]*len(correctset))

        elif abtype == 'shortanswerresponse':
            print("[latex2html.abox] Warning - short answer response quite yet implemented in edX!")
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
            self.make_default_test_pass([answer])

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
            orig_answers = answers[:]	# copy of answers (answers may be changed, if wrapped)
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

            self.make_default_test_pass(orig_answers, None,
                                        list(zip([0]*len(orig_answers), list(range(len(orig_answers))))))
                    
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
                    
        # -----------------------------------------------------------------------------

        elif abtype in ['multicoderesponse', 'multiexternalresponse']:
            #
            # cfn is taken to set the "grader" parameter in graer_payload
            # 
            # requires queuename to be specified
            # for multiple instances of the same grader, in one vertical, be sure to
            # set "index" to different values.
            # 
            # The optional "debug" argument can be set to 1 (to show debug) or 0 
            # (to suppress debug output, and to hide the textboxinput).  Debug defaults
            # to True.
            #
            # For multiexternalresponse, the grader parameters are encoded in a
            # <script type="text/python">...</script> stanza.

            tags = {'multicoderesponse': "coderesponse",
                    'multiexternalresponse': "externalresponse"
                    }
            
            abxml.tag = tags[abtype]
            self.require_args(['cfn'])		# for externalresponse, thesse are put into a script stanza

            cfn = self.stripquotes(abargs['cfn'])
            index = self.stripquotes(abargs.get('index', "")) or "1"
            debug = abargs.get("debug", True) in [True, '1', 1]

            tb = etree.Element('textbox')
            tb.set('rows', abargs.get('rows', "5"))
            tb.set('cols', abargs.get('cols', "80"))
            tb.set("mode", "python")
            if not debug:
                tb.set('hidden', '1') 		# edX-platform not hiding textbox despite hidden=1?
            abxml.append(tb)

            # setup grader payload options json
            options = abargs.get('options', '')
            expect = abargs.get('expect', '')
            gp_json = json.dumps({"grader": cfn,		# xqueue config payload, sent to grader
                                  'debug': debug,
                                  'options': self.unescape(options),
                                  'expect': self.unescape(expect),
                                  'queuename': abargs.get("queuename"),
            })

            if abtype in ['multicoderesponse']:
                self.require_args(['queuename'])
                self.copy_attrib(abargs,'queuename', abxml)
                cp = etree.SubElement(abxml, "codeparam")
                ide = etree.SubElement(cp, "initial_display");
                ad = etree.SubElement(cp,"answer_display")
                ad.text = "see text"
                gp = etree.SubElement(cp, "grader_payload")
                gp.text = gp_json

            elif abtype in ['multiexternalresponse']:
                stext = "\ngrader_payload = '%s'\n" % gp_json
                api_key = abargs.get("api_key")
                if api_key:
                    stext = '\nAPI_KEY="%s"' % api_key + stext
                self.require_args(['url'])
                self.copy_attrib(abargs, 'url', abxml)
                script_elem = etree.Element("script")
                script_elem.set("type", "text/python")
                script_elem.text = stext

            # now construct input elements for each prompt
            mcrid = "%s_%s" % (cfn, index)
            ispan = etree.Element("span")
            ispan.set("id", "span_" + mcrid)
            ispan.set("class", "multicoderesponse")

            if 'prompts' in abargs:
                promptstr, prompts = self.get_options(abargs,'prompts')
            elif 'prompt' in abargs:
                prompts = [self.stripquotes(abargs['prompt'])]
            else:
                prompts = ['']

            numRepeatSizes = len(prompts)
            if numRepeatSizes < 1:
                numRepeatSizes = 1

            if not 'sizes' in abargs:
                if 'size' in abargs:
                    sizes = [self.stripquotes(abargs['size'])] * numRepeatSizes
                else:
                    sizes = [''] * numRepeatSizes
            else:
                szstr, sizes = self.get_options(abargs,'sizes')

            do_inline = abargs.get('inline')

            if not len(prompts)==len(sizes):
                print("Error: number of sizes and prompts must match in:")
                print(aboxstr)
                sys.exit(-1)

            cnt = 0
            for prompt, sz in zip(prompts,sizes):	# note - no answers, for multicoderesponse
                # goal: end up with elements like this:
                # <p style="display:inline">[mathjaxinline]\tt b=[/mathjaxinline]
                #    <input size="25" id="cinput1" correct_answer="." class="inline" /></p>

                pe = etree.SubElement(ispan, 'p')
                if do_inline:
                    pe.set('style','display:inline')
                pe.text = prompt
                ie = etree.SubElement(pe, "input")
                if sz != '':
                    ie.set('size', sz)
                if do_inline:
                    ie.set('style','display:inline')
                ie.set('id', "input_%s_%d" % (mcrid, cnt+1))
                ie.set('class', 'input_%s multicode_input_%d' % (mcrid, cnt+1))
                etree.SubElement(ispan, 'br')
                cnt += 1

            # if hidden is a string, then create an empty span with that as the ID.
            # For anchor to find correct codemirror.
            hidden_arg = self.stripquotes(abargs.get("hidden", ""))
            if hidden_arg:
                hs = etree.SubElement(ispan, "span")
                hs.set("id", hidden_arg)
                hs.set("name", "hidden_arg")
                hs.set("data-mcrid", mcrid)

            # javascript for combining inputs and serializing into the textbox input of the coderesponse
            js_extra = ""
            if not debug:
                js_extra = '$("#span_%s").parent().find(".CodeMirror").hide();' % (mcrid)	# hide textbox if not debugging

            dtstr = datetime.datetime.now()

            jscode = MULTICODE_JS_TEMPLATE % (dtstr, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, mcrid, js_extra, mcrid, mcrid)

            jse = etree.Element("script")
            jse.text = jscode
            jse.set("type", "text/javascript")

            # now assemble all the elements: put into a big span
            aspan = etree.Element("span")
            aspan.set("id", "bigspan_%s" % mcrid)
            aspan.append(abxml)
            aspan.append(ispan)
            aspan.append(jse)

            if abtype in ['multiexternalresponse']:
                aspan.append(script_elem)
                atext = abargs.get("answer", "")
                if atext:
                    answer = etree.SubElement(abxml, "answer")
                    answer.text = atext
                tests = etree.SubElement(abxml, "tests")
                tests.text = abargs.get("tests", "")

            abxml = aspan	# use assembled span for the abox XML

        elif abtype == 'externalresponse' or abtype == 'coderesponse':
            if 'url' in abargs:
                self.copy_attrib(abargs, 'url', abxml)
            tb = etree.Element('textbox')
            self.copy_attrib(abargs, 'rows', tb)
            self.copy_attrib(abargs, 'cols', tb)
            self.copy_attrib(abargs, 'mode', tb)
            self.copy_attrib(abargs, 'tabsize', tb)
            self.copy_attrib(abargs, 'queuename', abxml)
            abxml.append(tb)

            if abtype=="externalresponse":
                atext = abargs.get("answer", "")
                if atext:
                    answer = etree.SubElement(abxml, "answer")
                    answer.text = atext
                tests = etree.SubElement(abxml, "tests")
                tests.text = abargs.get("tests", "")
            
            elif abtype=="coderesponse":
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
                gp = abargs.get("grader_payload", "")
                if not gp:
                    cfn = self.stripquotes(abargs.get('cfn', ''))
                    debug = abargs.get("debug", True) in [True, '1', 1]
                    options = abargs.get('options', '')
                    expect = abargs.get('expect', '')
                    gp = json.dumps({"grader": cfn,		# xqueue config payload, sent to grader
                                     'debug': debug,
                                     'options': self.unescape(options),
                                     'expect': self.unescape(expect),
                    })
                cp_gp.text = gp
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
            self.make_default_test_pass([answer])
        
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
            self.make_default_test_pass([answer])

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
            self.make_default_test_pass([answer])
            
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
                print("[abox.py] Setting default parameters for %s to %s" % (cfor, params))
 
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

        xml_str = etree.tostring(abxml, pretty_print=True).decode()
        xml_str = re.sub('(?ms)<html>(.*)</html>', '\\1', xml_str)

        if script_code:
            code_str = '<script type="text/python" system_path="python_lib">\n'
            code_str += "<![CDATA[\n"
            code_str += script_code
            code_str += "\n]]>\n</script>\n"
            xml_str = "<span>%s\n%s</span>" % (xml_str, code_str)
            if self.verbose:
                print("script code!")
                print(xml_str)

        the_xml = etree.XML(xml_str)

        return the_xml

    def make_default_test_pass(self, responses, expected=None, box_indexes=None):
        '''
        Add a test if there isn't an explicit test_pass defined.
        Called by the various response constructions.
        '''
        if self.has_test_pass:
            return
        # default box indexes increment "y" but not "x"
        box_indexes = box_indexes or list(zip([0]*len(responses), list(range(len(responses)))))
        # generate unit test if no explicit tests specified in abox arguments
        self.tests.append({'responses': list(map(self.unescape, responses)),
                           'expected': expected or ['correct'] * len(responses),
                           'box_indexes': box_indexes,
        })

    def get_options(self, abargs, arg='options'):
        optstr = abargs[arg]			# should be double quoted strings, comma delimited
        # EVH 01-22-2015: Inserting quotes around single option for proper
        # parsing of choices containing commas
        if not optstr.startswith('"') and not optstr.startswith("'"):
            optraw = repr(optstr)
            optstr = optraw[0] + optstr + optraw[0]
        options = split_args_with_quoted_strings(optstr, lambda x: x == ',')		# turn into list of strings
        options = list(map(self.stripquotes, options))
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
        test_args = list(map(self.stripquotes, split_args_with_quoted_strings(val, lambda x: x == ',')))
        test_args = list(map(self.unescape, test_args))
        if key=="test_spec":
            nargs = len(test_args)
            if not (nargs&1==0):
                raise Exception("[abox] test_spec must be given with an even number of subarguments, specifying equal number of responses and expected grader outputs")
            responses = test_args[:nargs//2]
            expected = test_args[nargs//2:]
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
        if responses and (not responses[0]==''):
            test = {'responses': responses, 
                    'expected': expected,
                    'box_indexes': list(zip([0]*len(responses), list(range(len(responses))))),
            }
            self.tests.append(test)
        elif self.verbose:
            print('[abox] Warning: empty test_pass="" in %s' % self.aboxstr)

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
        s = s.replace('\u2019', "'")
        try:
            s = str(s)
        except Exception as err:
            print("Error %s in obtaining string form of abox argument %s" % (err, s))
            return {}
        try:
            # abargstxt = shlex.split(s)
            abargstxt = split_args_with_quoted_strings(s)
        except Exception as err:
            print("Error %s in parsing abox argument %s" % (err, s))
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
        except Exception as err:
            print("Error %s" % err)
            print("Failed in parsing args = %s" % s)
            print("abargstxt = %s" % abargstxt)
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
    print(ab.xmlstr)
    assert('''<optioninput options="('noneType','int','float')" correct="float"/>''' in ab.xmlstr)

def test_abox2_custom_config():
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
    print(ab.tests)
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
    print(ab.xmlstr)
    assert('choicegroup' in ab.xmlstr)
    assert(ab.tests[0]['responses']==['choice_2'])
    assert(ab.tests[0]['expected']=='correct')

def test_abox_mc_ut2():
    ab = AnswerBox('type="oldmultichoice" options="green","blue","red" expect="blue","red"')
    print(ab.xmlstr)
    assert('checkboxgroup' in ab.xmlstr)
    assert(ab.tests[0]['responses']==['choice_2', 'choice_3'])
    assert(ab.tests[0]['expected']=='correct')

def test_abox_option_ut1():
    ab = AnswerBox('type="option" options="green","blue","red" expect="blue"')
    print(ab.xmlstr)
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

def test_multicoderesponse1():
    abstr = """\edXabox{expect="." queuename="test-6341" type="multicode" prompts="$\mathtt{numtaps} = $","$\mathtt{bands} = $","$\mathtt{amps} = $","$\mathtt{weights} = $"  answers=".",".",".","." cfn="designGrader" sizes="10","25","25","25" inline="1"}"""
    ab = AnswerBox(abstr)
    xmlstr = etree.tostring(ab.xml).decode()
    print(xmlstr)
    assert ab.xml
    assert '<grader_payload>{"debug": true, "grader": "designGrader", "options": "", "expect": ""}</grader_payload>' in xmlstr
    assert '<p style="display:inline">$\mathtt{numtaps} = $<input size="10" style="display:inline" ' in xmlstr

def test_multicoderesponse2():
    abstr = """\edXabox{expect="." queuename="test-6341" type="multicode" prompts="$\mathtt{numtaps} = $","$\mathtt{bands} = $","$\mathtt{amps} = $","$\mathtt{weights} = $"  answers=".",".",".","." cfn="designGrader" sizes="10","25","25","25" hidden="abc123" inline="1"}"""
    ab = AnswerBox(abstr)
    xmlstr = etree.tostring(ab.xml).decode()
    print(xmlstr)
    assert ab.xml
    assert '<span id="abc123"' in xmlstr

def test_abox_skip_unit_test6():
    ab = AnswerBox('type="custom" expect=10 cfn=mytest test_pass=""', verbose=True)
    print(ab.tests)
    assert(len(ab.tests)==0)

def test_abox_coderesponse1():
    ab = AnswerBox('type="code" rows=30 cols=90 queuename="some_queue" mode="python" answer_display="see text" '
                   'cfn="qis_cfn" debug=1 options="test_opt" expect="test_expect"', verbose=True)
    print(ab.xmlstr)
    assert """<grader_payload>{"debug": true, "grader": "qis_cfn", "options": "test_opt", "expect": "test_expect"}</grader_payload>""" in ab.xmlstr

def test_abox_coderesponse2():
    ab = AnswerBox('type="code" rows=30 cols=90 queuename="some_queue" mode="python" answer_display="see text" '
                   """grader_payload='{"a":2, "cfn":"test"}' """
                   'cfn="qis_cfn" debug=1 options="test_opt" expect="test_expect"', verbose=True)
    print(ab.xmlstr)
    assert ("""<grader_payload>{"debug": true, "grader": "qis_cfn", """
            """options": "test_opt", "expect": "test_expect"}</grader_payload>""" not in ab.xmlstr)
    assert """<grader_payload>{"a":2, "cfn":"test"}</grader_payload>""" in ab.xmlstr

def test_abox_multichoice_indexes1():
    ab = AnswerBox('''inline=1 type='multichoice' expect="UL","DR" options="None","UL","UR","DL","DR"''')
    assert('choiceresponse' in ab.xmlstr)
    assert(len(ab.tests)==1)
    assert(ab.tests[0]['box_indexes'] == [[0,0], [0,0]])

def test_multiexternalresponse1():
    abstr = """\edXabox{expect="." url="https://localhost/test/6341" type="multiexternal" prompts="$\mathtt{numtaps} = $","$\mathtt{bands} = $","$\mathtt{amps} = $","$\mathtt{weights} = $"  answers=".",".",".","." cfn="designGrader" sizes="10","25","25","25" hidden="abc123" inline="1"}"""
    ab = AnswerBox(abstr)
    xmlstr = etree.tostring(ab.xml).decode()
    print(xmlstr)
    assert ab.xml is not None
    assert '<span id="abc123"' in xmlstr
    m = re.search('<script type="text/python">(.*)</script>', xmlstr, flags=re.M+re.S)
    sc = m.group(1)
    context = {}
    exec(sc, globals(), context)
    print(context)
    gp = json.loads(context['grader_payload'])
    assert gp['grader']=="designGrader"

def test_multiexternalresponse2():
    abstr = """\edXabox{type="multiexternal" 
  url="http://localhost:9091/grade"
  size=70
  debug=0
  hidden="parity_circuit"
  prompts="circuit = "
  expect="[]"
  options="nqubits=5"
  cfn=qis_qcircuit
  inline="1"
}
"""
    abstr = abstr.replace('\n', ' ')
    # abstr = """\edXabox{expect="." url="https://localhost/test/6341" type="multiexternal" prompts="$\mathtt{numtaps} = $","$\mathtt{bands} = $","$\mathtt{amps} = $","$\mathtt{weights} = $"  answers=".",".",".","." cfn="designGrader" sizes="10","25","25","25" hidden="abc123" inline="1"}"""
    abstr = """type="multiexternal" api_key="secret_key" url="http://localhost:9091/grade"  size=70  debug=0  hidden="parity_circuit"  prompts="circuit = "  expect="[]"  options="nqubits=5"  cfn=qis_qcircuit  inline="1" """
    ab = AnswerBox(abstr)
    xmlstr = etree.tostring(ab.xml).decode()
    print(xmlstr)
    assert "<answer" not in xmlstr
    m = re.search('<script type="text/python">(.*)</script>', xmlstr, flags=re.M+re.S)
    sc = m.group(1)
    assert 'API_KEY="secret_key"' in sc
    
