#!/usr/bin/python
import optparse
import os
import sys
import getpass
from fedora.accounts.fas2 import AccountSystem
from fedora.accounts.fas2 import CLAError
from fedora.tg.client import AuthError, ServerError
from OpenSSL import crypto

def read_cert_user():
    """
    Figure out the Fedora user name from ~/.fedora.cert

    """
    # Make sure we can even read the thing.
    cert_file = os.path.join(os.path.expanduser('~'), ".fedora.cert")
    if not os.access(cert_file, os.R_OK):
        print "!!!    cannot read your ~/.fedora.cert file   !!!"
        print "!!! Ensure the file is readable and try again !!!"
        sys.exit(1)
    FILE = open(cert_file)
    my_buf = FILE.read()
    FILE.close()
    my_cert = crypto.load_certificate(crypto.FILETYPE_PEM, my_buf)

    subject = str(my_cert.get_subject())
    subject_line = subject.split("CN=")
    cn_parts = subject_line[1].split("/")
    username = cn_parts[0]

    if my_cert.has_expired():
        print "Certificate expired; Lets get a new one."
        create_user_cert(username)

    return username


def create_user_cert(username):
    if not username is None:
        username = raw_input('FAS Username: ')
    password = getpass.getpass('FAS Password: ')
    try:
        fas = AccountSystem('https://admin.fedoraproject.org/', username, password)
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
    if not os.access(cert_file, os.W_OK):
        print "Can not open cert file for writing"
        print cert
        sys.exit(1)
    else:
        FILE = open(cert_file,"w")
        FILE.write(cert)
        FILE.close()

def main(opts):
    # lets read in the existing cert if it exists.
    # gets us existing acc info
    if not opts.username:
        try:
            username = read_user_cert()
        except :
            print "Can't determine fas name, lets get a new cert"
            create_user_cert(None)
            sys.exit(0)
    else:
        username = opts.username
    #has cert expired? do we force a new cert? get a new one
    if opts.new_cert:
        print "Getting a new User Certificate"
        create_user_cert(username)
        sys.exit(0)
    if certificate_expired():
        print "Certificate has expired, getting a new one"
        create_user_cert(username)
        sys.exit(0)
    if opts.verify-cert:
        print "Verifying Certificate"

     
if __name__ == '__main__':
    opt_p = optparse.OptionParser(usage="%prog [OPTIONS] ")
    opt_p.add_option('-u', '--username', action='store_true', dest='username',
                     help="FAS Username.")
    opt_p.add_option('-n', '--new-cert', action='store_true', dest='newcert',
                     help="Generate a new Fedora Certificate.")
    opt_p.add_option('-v', '--verify-cert', action='store_true', dest='verifycert',
                     help="Verify Certificate.")

    opts = opt_p.parse_args()

    main(opts)
