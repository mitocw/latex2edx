import os
import sys

if len(sys.argv)>1:
    python="python "
    latex2edx="latex2edx.py "
    filename=sys.argv[1]
    cmd1=python+latex2edx+filename
    print cmd1
    os.system(cmd1)
    xmlfile=filename[:-3]+"xml"
    print xmlfile
    cmd2="cp 8.02x/problems/"+xmlfile+" ../problem"
    print cmd2
    os.system(cmd2)

