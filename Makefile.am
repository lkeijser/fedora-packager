bin_SCRIPTS = fedora-cvs \
	fedora-packager-setup \
	fedoradev-pkgowners \
	fedora-cert \
	fedora-getsvn \
	fedora-hosted \
	rpmbuild-md5 \
	fedpkg
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = src/fedora-cvs.py \
	src/fedora-packager-setup.py \
	src/fedoradev-pkgowners \
	src/fedora-cert.py \
	src/fedora-getsvn \
	src/fedora-hosted.py \
	src/rpmbuild-md5 \
	src/fedpkg.py

fedora-cvs: $(srcdir)/src/fedora-cvs.py
	rm -f fedora-cvs
	install -p -m 755 -T $(srcdir)/src/fedora-cvs.py fedora-cvs

fedora-packager-setup: $(srcdir)/src/fedora-packager-setup.py
	rm -f fedora-packager-setup
	install -p -m 755 -T $(srcdir)/src/fedora-packager-setup.py fedora-packager-setup

fedoradev-pkgowners: $(srcdir)/src/fedoradev-pkgowners
	rm -f fedoradev-pkgowners
	install -p -m 755 -T $(srcdir)/src/fedoradev-pkgowners fedoradev-pkgowners

fedora-cert: $(srcdir)/src/fedora-cert.py
	rm -f fedora-cert
	install -p -m 755 -T $(srcdir)/src/fedora-cert.py fedora-cert

fedora-getsvn: $(srcdir)/src/fedora-getsvn
	rm -f fedora-getsvn
	install -p -m 755 -T $(srcdir)/src/fedora-getsvn fedora-getsvn

fedora-hosted: $(srcdir)/src/fedora-hosted.py
	rm -f fedora-hosted
	install -p -m 755 -T $(srcdir)/src/fedora-hosted.py fedora-hosted

rpmbuild-md5: $(srcdir)/src/rpmbuild-md5
	rm -f rpmbuild-md5
	install -p -m 755 -T $(srcdir)/src/rpmbuild-md5 rpmbuild-md5

fedpkg: $(srcdir)/src/fedpkg.py
	rm -f fedpkg
	install -p -m 755 -T $(srcdir)/src/fedpkg.py fedpkg

pyfedpkg_PYTHON = $(wildcard $(srcdir)/src/pyfedpkg/*.py)
fedora_cert_PYTHON = $(wildcard $(srcdir)/src/fedora_cert/*.py)

fedora_certdir = $(pythondir)/fedora_cert
pyfedpkgdir = $(pythondir)/pyfedpkg
