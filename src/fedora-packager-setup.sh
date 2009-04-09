#!/bin/bash

set -e

function check_wget() {
    if [ ! -f /usr/bin/wget ]; then
        echo "You must have wget installed to download the required CA certificates"
        echo "Please run \"yum install wget\" as root, and re-run this script"
        exit 1
    fi
}

echo "Setting up Koji client..."

if [ ! -f ~/.fedora.cert ]; then
    echo "You need a client certificate from the Fedora Account System"
    echo "Please download one from https://admin.fedoraproject.org/accounts/user/gencert"
    echo "Save it to ~/.fedora.cert and re-run this script"
    exit 1
fi

rm ~/.fedora-upload-ca.cert

if [ ! -f ~/.fedora-upload-ca.cert ]; then
    check_wget
    /usr/bin/wget -q "https://admin.fedoraproject.org/accounts/fedora-upload-ca.cert" -O ~/.fedora-upload-ca.cert
fi

rm ~/.fedora-server-ca.cert

if [ ! -f ~/.fedora-server-ca.cert ]; then
    check_wget
    /usr/bin/wget -q "https://admin.fedoraproject.org/accounts/fedora-server-ca.cert" -O ~/.fedora-server-ca.cert
fi

if [ ! -d ~/.koji ]; then
    mkdir  ~/.koji
fi


for arch in arm alpha ia64 sparc s390 parisc ;do 
rm -f ~/.koji/$arch-config
cat > ~/.koji/$arch-config <<EOF
[koji]

;configuration for koji cli tool

;url of XMLRPC server
server = http://$arch.koji.fedoraproject.org/kojihub

;url of web interface
weburl = http://$arch.koji.fedoraproject.org/koji

;url of package download site
pkgurl = http://$arch.koji.fedoraproject.org/packages

;path to the koji top directory
;topdir = /mnt/koji

;configuration for SSL athentication

;client certificate
cert = ~/.fedora.cert

;certificate of the CA that issued the client certificate
ca = ~/.fedora-upload-ca.cert

;certificate of the CA that issued the HTTP server certificate
serverca = ~/.fedora-server-ca.cert

EOF
echo "Wrote $arch koji config file"
done

cat > ~/.plague-client.cfg <<EOF
[Certs]
user-ca-cert = ~/.fedora-upload-ca.cert
server-ca-cert = ~/.fedora-server-ca.cert
user-cert = ~/.fedora.cert

[User]
email = $email

[Server]
use_ssl = yes
upload_user = me
allow_uploads = no
address = https://buildsys.fedoraproject.org:8887
EOF
echo "Wrote Plague Config file"

cat <<EOF
Creating an SSL certificate to import into your browser, to enable
user authentication at http://koji.fedoraproject.org/koji/
Choose your own passphrase, you will be prompted for this when importing the certificate.

EOF

if [ -f ~/fedora-browser-cert.p12 ]; then
    rm ~/fedora-browser-cert.p12
fi

/usr/bin/openssl pkcs12 -export -in ~/.fedora.cert -CAfile ~/.fedora-upload-ca.cert -out ~/fedora-browser-cert.p12

cat <<EOF

Browser certificate exported to ~/fedora-browser-cert.p12
To import the certificate into Firefox:

Edit -> Preferences -> Advanced
Click "View Certificates"
On "Your Certificates" tab, click "Import"
Select ~/fedora-browser-cert.p12
Type the export passphrase you chose earlier

Once imported, you should see a certificate named "Fedora Project".
Your username should appear underneath this.
 
You should now be able to click the "login" link at http://koji.fedoraproject.org/koji/ successfully.
EOF
