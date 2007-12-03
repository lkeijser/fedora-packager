bin_SCRIPTS = fedora-cvs fedora-packager-setup.sh
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = src/fedora-cvs.py src/fedora-packager-setup.sh

fedora-cvs: $(srcdir)/src/fedora-cvs.py
	rm -f fedora-cvs
	cp -p $(srcdir)/src/fedora-cvs.py fedora-cvs
	chmod ugo+x fedora-cvs

fedora-packager-setup.sh: $(srcdir)/src/fedora-packager-setup.sh
	rm -f fedora-packager-setup.sh
	cp -p $(srcdir)/src/fedora-packager-setup.sh fedora-packager-setup.sh
	chmod ugo+x fedora-packager-setup.sh
