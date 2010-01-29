# fedora-cert - a Python library for Managing fedora SSL Certificates
#
# Copyright (C) 2009-2010 Red Hat Inc.
# Author(s):  Dennis Gilmore <dennis@ausil.us>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import os
import sys
import getpass
from fedora.client.fas2 import AccountSystem
from fedora.client.fas2 import CLAError
from fedora.client import AuthError, ServerError
from OpenSSL import crypto
import urlgrabber


def _open_cert():
    """
    Read in the certificate so we dont duplicate the code 
    """
     # Make sure we can even read the thing.
    cert_file = os.path.join(os.path.expanduser('~'), ".fedora.cert")
    if not os.access(cert_file, os.R_OK):
        print "!!!    cannot read your ~/.fedora.cert file   !!!"
        print "!!! Ensure the file is readable and try again !!!"
        sys.exit(1)
    raw_cert = open(cert_file).read()
    my_cert = crypto.load_certificate(crypto.FILETYPE_PEM, raw_cert)
    return my_cert

def verify_cert():
    """
    Check that the user cert is valid. 
    things to check/return
    not revoked
    Expiry time warn if less than 21 days
    """
    my_cert = _open_cert()
    serial_no = my_cert.get_serial_number()
    valid_until = my_cert.get_notAfter()
    crl = urlgrabber.urlread("https://admin.fedoraproject.org/ca/crl.pem")


def certificate_expired():
    """
    Check to see if ~/.fedora.cert is expired
    Returns True or False

    """
    my_cert = _open_cert()

    if my_cert.has_expired():
        return True
    else:
        return False

def read_user_cert():
    """
    Figure out the Fedora user name from ~/.fedora.cert

    """
    my_cert = _open_cert()

    subject = str(my_cert.get_subject())
    subject_line = subject.split("CN=")
    cn_parts = subject_line[1].split("/")
    username = cn_parts[0]
    return username

def create_user_cert(username=None):
    if not username:
        username = raw_input('FAS Username: ')
    password = getpass.getpass('FAS Password: ')
    try:
        fas = AccountSystem('https://admin.fedoraproject.org/accounts/', username=username, password=password)
    except AuthError:
        print "Invalid username/password."
        sys.exit(1)

    try:
        cert = fas.user_gencert()
        fas.logout()
    except CLAError:
        print "You must sign the CLA before you can generate your certificate.\n" \
            "To do this, go to https://admin.fedoraproject.org/accounts/cla/"
        fas.logout()
        sys.exit(1)
    cert_file = os.path.join(os.path.expanduser('~'), ".fedora.cert")
    try:
        FILE = open(cert_file,"w")
        FILE.write(cert)
        FILE.close()
    except:
        print """Can not open cert file for writing.
Please paste certificate into ~/.fedora.cert"""
       
        print cert
        sys.exit(1)

