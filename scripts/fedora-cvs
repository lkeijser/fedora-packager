#!/usr/bin/python

import os
import string
import sys
import commands

def readUser():
    ''' samle line "Subject: C=US, ST=North Carolina, O=Fedora Project, OU=Dennis Gilmore, CN=ausil/emailAddress=dennis@ausil.us" '''
    userCert = ""
    if os.access(os.path.join(os.path.expanduser('~'),".fedora.cert"), os.R_OK):
            userCert = open(os.path.join(os.path.expanduser('~'),".fedora.cert"), "r").read()
    else:
        print "!!!    cannot read your ~/.fedora.cert file   !!!"
        print "!!! Ensure the file is readable and try again !!!"
        os.exit(1)
    for certLine in  userCert.split("\n"):
        if not len(certLine):
            continue
        stripCertLine = certLine.strip()
        if stripCertLine.startswith("Subject: "):
            subjectLine = certLine.split("CN=")
            name = subjectLine[1].split("/")
            return name[0]
      

def cvsco(user, module):
    '''CVSROOT=:ext:ausil@cvs.fedoraproject.org:/cvs/extras/'''
    (s, o) = commands.getstatusoutput("CVSROOT=:ext:%s@cvs.fedoraproject.org:/cvs/extras/ CVS_RSH=ssh cvs co %s" % (user, module))
    if s != 0:
        print "Error: %s" % o
    else:
        print o


def main(pkg):
    userName = readUser()
    cvsco(userName, pkg)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "you need to specify the module to checkout of cvs"
        sys.exit(1)

    #the package we want to pull from cvs 
    pkg = sys.argv[1]

    main(pkg)

