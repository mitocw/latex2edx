#!/usr/bin/python
#
# File:   latex2edx_xserver.py
# Date:   13-Oct-12
# Author: I. Chuang <ichuang@mit.edu>
#
# web server which provides latex2edx service for edX CMS instance
# uses wsgi

import sys, string, re, time, os
import json
from path import path
import tempfile
import urllib
import base64
import gzip
from StringIO import StringIO

from cgi import parse_qs, escape

#-----------------------------------------------------------------------------
# config

PORT = 8103
MYDIR = path(__file__).abspath().dirname()
TMPDIR = MYDIR / 'tmp'

#-----------------------------------------------------------------------------

LOGFILE = "latex2edx_xserver.log"
PIDFILE = "latex2edx_xerver.pid"

open(PIDFILE,'w').write(str(os.getpid()))

def LOG(x):
    fp = open(LOGFILE,'a')
    if type(x)==dict:
        for k in x:
            if not k:
                continue
            s = '  %s : %s' % (k,x[k])
            fp.write(s)
            print s
    #if type(x)==type('str'):
    else:
        fp.write(x)
        fp.write('\n')
        print x

    sys.stdout.flush()
    fp.flush()
    fp.close()

#-----------------------------------------------------------------------------

def do_latex2edx(latexin):
    tmpfn_tex = tempfile.NamedTemporaryFile(dir=TMPDIR, delete=False, suffix='.tex', mode='w')
    tmpfn_xml = tmpfn_tex.name[:-4] + '.xml'

    if 'begin{document}' not in latexin:
        latex = r'''\documentclass[12pt]{article}
        \usepackage{edXpsl}
        
        \begin{document}
        
        \begin{edXproblem}{lec1_Q2}{10}
        
        %s
        
        \end{edXproblem}
        
        \end{document}    
        ''' % latexin
    else:
        latex = latexin

    tmpfn_tex.write(latex)
    tmpfn_tex.close()
    cmd = 'python latex2edx.py -single %s %s' % (tmpfn_xml, tmpfn_tex.name)
    print cmd
    LOG(cmd)
    errors = os.popen(cmd).read()
    if os.path.exists(tmpfn_xml):
        xml = open(tmpfn_xml).read()
    else:
        xml = ''
    return xml, errors

#-----------------------------------------------------------------------------

def get_client_address(environ):
    try:
        return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
    except KeyError:
        return environ.get('HTTP_HOSTIP',environ.get('REMOTE_ADDR',''))

#-----------------------------------------------------------------------------

def do_latex2edx_xserver(environ, start_response):

    LOG('-----------------------------------------------------------------------------')
    LOG('connect from %s at %s' % (get_client_address(environ), time.ctime(time.time())))
    LOG('referer: %s' % environ.get('HTTP_REFERER',''))
    # LOG(str(environ))

    qs = environ.get('QUERY_STRING', '')
    parameters = parse_qs(qs)

    if 'callback' in parameters:	# ajax / jsonp call?
        mode = 'jsonp'
        callback = parameters['callback'][0]
        print "callback = %s" % callback
        # /latex2edx?callback=jQuery17203719855370000005_1350160239730&%7B%22latexin%22%3A%22%5C%5Cbegin%7Bdocument%7D%5Cn%5C%5Csection%7BExample%3A%20Option%20Response%20Problem%20in%20Latex%7D%5CnWhere%20is%20the%20earth%3F%5Cn%5C%5CedXabox%7Boptions%3D%27up%27%2C%27down%27%20expect%3D%27down%27%7D%5Cn%5C%5Cend%7Bdocument%7D%5Cn%22%7D&_=1350160244502
        m = re.search('callback=%s&([^&]+)&' % callback, qs)
        if m:
            js = urllib.unquote(m.group(1))
            data = json.loads(js)
            print js
            print data
            print "ok"
        else:
            print "ERROR! no JSON data found in %s" % qs

    elif 'raw' in parameters:	# ajax POST
        LOG('raw')
        data = {'latexin': environ['wsgi.input'].read()}
        LOG("data=%s" % data)
        mode = 'post'

    else:
        data = parameters
        mode = 'html'
        
    latexin = data.get('latexin','')
    if type(latexin)==list:
        latexin = latexin[0]
    LOG("latexin = %s" % latexin)

    html = '''<html><form><h2>Latex input:</h2>'''
    html += '''<textarea name="latexin" rows="10" cols="50">%s</textarea>''' % (latexin[0] if latexin else '')
    html += '''<input type="submit" name="Convert"></form>'''

    xml = ''
    errors = ''

    if latexin:
        xml, errors = do_latex2edx(latexin)

        html += '<h2>edX XML:</h2>'
        html += '<div style="background:#ECF7D3"><pre>%s</pre></div>' % xml.replace('<','&lt;')
        html += '<h2>Messages:</h2>'
        html += '<div style="background:#F7ECD3"><pre>%s</pre></div>' % errors.replace('<','&lt;')
        html += '<edxxml>%s</edxxml>' % xml
        
    if mode=='html':
        start_response('200 OK', [('Content-Type', 'text/html')])
        return [html]
    elif mode=='post':
        start_response('200 OK', [('Content-Type', "text/json")])
        jsondat = json.dumps({'xml': xml, 'message': errors, 'images': ''})
        LOG("Return: %s" % jsondat)
        return [jsondat]
    else:
        start_response('200 OK', [('Content-Type', "application/json")])
        jsondat = json.dumps({'xml': xml, 'message': errors})
        # jsondat = json.dumps({'foo':'hello'})
        ret = "%s(%s);" % (callback, jsondat)
        print "Return: ", ret
        return ret

#-----------------------------------------------------------------------------

if __name__ == '__main__':
    LOG('========> started at %s' % time.ctime(time.time()))
    from wsgiref.simple_server import make_server
    import socket
    host = socket.gethostname()
    srv = make_server(host, PORT, do_latex2edx_xserver)
    srv.serve_forever()
    