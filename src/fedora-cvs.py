#!/usr/bin/python

import os
import string
import sys
import commands
from OpenSSL import crypto

def readUser():
    ''' sample line "Subject: C=US, ST=North Carolina, O=Fedora Project, OU=Dennis Gilmore, CN=ausil/emailAddress=dennis@ausil.us" '''
    userCert = ""
    if os.access(os.path.join(os.path.expanduser('~'),".fedora.cert"), os.R_OK):
            userCert = open(os.path.join(os.path.expanduser('~'),".fedora.cert"), "r").read()
    else:
        print "!!!    cannot read your ~/.fedora.cert file   !!!"
        print "!!! Ensure the file is readable and try again !!!"
        sys.exit(1)
    myCert = crypto.load_certificate(1, userCert)
    if myCert.has_expired():
        print "Certificate expired please get a new one"
        sys.exit(1)
    subject = str(myCert.get_subject())
    subjectLine = subject.split("CN=")
    name = subjectLine[1].split("/")
    return name[0]
      

def cvsco(user, module):
    '''CVSROOT=:ext:ausil@cvs.fedoraproject.org:/cvs/extras/'''
    print "Checking out %s from fedora cvs:" % module
    (s, o) = commands.getstatusoutput("CVSROOT=:ext:%s@cvs.fedoraproject.org:/cvs/pkgs/ CVS_RSH=ssh cvs co %s" % (user, module))
    if s != 0:
        print "Error: %s" % o
    else:
        print o

def usage():
    print """
    add the modules you wish to check out from cvs
    example fedora-cvs konversation mysql cvs mercurial
    """

def main(pkg):
    userName = readUser()
    for Item in pkg:
        cvsco(userName, Item)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    #the package we want to pull from cvs 
    pkg = sys.argv
    pkg.remove(sys.argv[0])

    main(pkg)

