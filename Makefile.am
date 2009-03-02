bin_SCRIPTS = fedora-cvs fedora-packager-setup
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = src/fedora-cvs.py src/fedora-packager-setup.py

fedora-cvs: $(srcdir)/src/fedora-cvs.py
	rm -f fedora-cvs
	cp -p $(srcdir)/src/fedora-cvs.py fedora-cvs
	chmod ugo+x fedora-cvs

fedora-packager-setup: $(srcdir)/src/fedora-packager-setup.py
	rm -f fedora-packager-setup
	cp -p $(srcdir)/src/fedora-packager-setup.py fedora-packager-setup
	chmod ugo+x fedora-packager-setup
