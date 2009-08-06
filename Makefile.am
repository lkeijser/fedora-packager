bin_SCRIPTS = fedora-cvs fedora-packager-setup fedoradev-pkgowners fedora-cert fedora-getsvn fedora-hosted rpmbuild-md5
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = src/fedora-cvs.py src/fedora-packager-setup.py src/fedoradev-pkgowners src/fedora-cert.py src/fedora-getsvn src/fedora-hosted.py src/rpmbuild-md5

fedora-cvs: $(srcdir)/src/fedora-cvs.py
	rm -f fedora-cvs
	cp -p $(srcdir)/src/fedora-cvs.py fedora-cvs
	chmod ugo+x fedora-cvs

fedora-packager-setup: $(srcdir)/src/fedora-packager-setup.py
	rm -f fedora-packager-setup
	cp -p $(srcdir)/src/fedora-packager-setup.py fedora-packager-setup
	chmod ugo+x fedora-packager-setup

fedoradev-pkgowners: $(srcdir)/src/fedoradev-pkgowners
	rm -f fedoradev-pkgowners
	cp -p $(srcdir)/src/fedoradev-pkgowners fedoradev-pkgowners
	chmod ugo+x fedoradev-pkgowners

fedora-cert: $(srcdir)/src/fedora-cert.py
	rm -f fedora-cert
	cp -p $(srcdir)/src/fedora-cert.py fedora-cert
	chmod ugo+x fedora-cert

fedora-getsvn: $(srcdir)/src/fedora-getsvn
	rm -f fedora-getsvn
	cp -p $(srcdir)/src/fedora-getsvn fedora-getsvn
	chmod ugo+x fedora-getsvn

fedora-hosted: $(srcdir)/src/fedora-hosted.py
	rm -f fedora-hosted
	cp -p $(srcdir)/src/fedora-hosted.py fedora-hosted
	chmod ugo+x fedora-hosted

rpmbuild-md5: $(srcdir)/src/rpmbuild-md5
	rm -f rpmbuild-md5
	cp -p $(srcdir)/src/rpmbuild-md5 rpmbuild-md5
	chmod ugo+x rpmbuild-md5
