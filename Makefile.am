bin_SCRIPTS = fedora-cvs fedora-packager-setup.sh
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = fedora-cvs fedora-packager-setup.sh

fedora-cvs: $(srcdir)/fedora-cvs.py
      rm -f fedora-cvs
      chmod ugo+x fedora-cvs

fedora-packager-setup.sh: $(srcdir)/fedora-packager-setup.sh
      rm -f fedora-packager-setup.sh
      chmod ugo+x fedora-packager-setup.sh
