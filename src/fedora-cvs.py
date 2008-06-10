#!/usr/bin/python

import commands
import optparse
import os
import sys

from OpenSSL import crypto

PKG_ROOT = 'cvs.fedoraproject.org:/cvs/pkgs'


def read_cert_user():
    """Figure out the Fedora user name from ~/.fedora.cert.  Sample line:

        Subject: C=US, ST=North Carolina, O=Fedora Project, OU=Dennis Gilmore, CN=ausil/emailAddress=dennis@ausil.us
    """

    # Mak sure we can even read the thing.
    cert_file = os.path.join(os.path.expanduser('~'), ".fedora.cert")
    if not os.access(cert_file, os.R_OK):
        print "!!!    cannot read your ~/.fedora.cert file   !!!"
        print "!!! Ensure the file is readable and try again !!!"
        sys.exit(1)

    user_cert = open(cert_file, "r").read()
    my_cert = crypto.load_certificate(crypto.FILETYPE_PEM, user_cert)

    if my_cert.has_expired():
        print "Certificate expired; please get a new one."
        sys.exit(1)

    subject = str(my_cert.get_subject())
    subject_line = subject.split("CN=")
    cn_parts = subject_line[1].split("/")

    return cn_parts[0]


def main(user, pkg_list):
    if user is not None:
        cvs_env = "CVSROOT=:ext:%s@%s CVS_RSH=ssh" % (user, PKG_ROOT)
    else:
        cvs_env = "CVSROOT=:pserver:anonymous@" + PKG_ROOT

    for module in pkg_list:
        print "Checking out %s from fedora CVS as %s:" % \
            (module, user or "anonymous")

        retcode, output = commands.getstatusoutput("%s cvs co %s" %
                                                   (cvs_env, module))

        if retcode != 0:
            print "Error: %s" % (output,)
        else:
            print output


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
        user = read_cert_user()

    main(user, pkgs)
