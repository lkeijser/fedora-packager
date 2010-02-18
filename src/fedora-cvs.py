#!/usr/bin/python

import commands
import optparse
import os
import sys
import fedora_cert
from subprocess import *

PKG_ROOT = 'cvs.fedoraproject.org:/cvs/pkgs'


def main(user, pkg_list):
    if user is not None:
        cvs_env = "CVSROOT=:ext:%s@%s CVS_RSH=ssh" % (user, PKG_ROOT)
    else:
        cvs_env = "CVSROOT=:pserver:anonymous@" + PKG_ROOT

    for module in pkg_list:
        print "Checking out %s from fedora CVS as %s:" % \
            (module, user or "anonymous")
        try:
            retcode = call("%s /usr/bin/cvs co %s" % (cvs_env, module), shell=True)
            if retcode < 0:
                print >>sys.stderr, "CVS Checkout failed Error:", -retcode
        except OSError, e:
            print >>sys.stderr, "Execution failed:", e



if __name__ == '__main__':
    opt_p = optparse.OptionParser(usage="%prog [OPTIONS] module ...")

    opt_p.add_option('-a', '--anonymous', action='store_true', dest='anon',
                     help="Use anonymous CVS.")

    opts, pkgs = opt_p.parse_args()

    if len(pkgs) < 1:
        opt_p.error("You must specify at least one module to check out.")

    # Determine user name, if any
    if opts.anon:
        user = None
    else:
        user = fedora_cert.read_user_cert()

    main(user, pkgs)
