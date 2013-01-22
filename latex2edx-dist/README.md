latex2edx_xserver
=================

latex2edx conversion xserver

22-Jan-13: updated to produce XML consistent with new edX course format; 
22-Jan-13: don't use edXsequential anymore; edXsection compiles into `<sequential>` now, by default.

For examples, run DOTEST

This command:

    python latex2edx.py -prefix "49_" test3.tex

should produce this content for 1.00x/course.xml:

    <?xml version="1.0"?>
    <course number="1.00x" url_name="1.00x Fall 2012">
      <chapter url_name="Unit 1">
        <sequential display_name="Introduction">
          <problem url_name="49_Problem_1"/>
          <problem url_name="49_Problem_2"/>
          <problem url_name="49_Problem_3"/>
          <vertical display_name="A sample vertical - multiple problems in one day">
            <problem url_name="49_Problem_3.5"/>
            <problem url_name="49_Problem_4"/>
          </vertical>
          <problem url_name="49_Problem_4"/>
        </sequential>
      </chapter>
    </course>

For images, make sure the directory path "static/html" exists.

