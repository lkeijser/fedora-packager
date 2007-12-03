tarball:
	tar -cjvf fedora-packager.tar.bz2 

install:
	install -p -m 755 scripts/fedora-packager-setup.sh /usr/bin/fedora-packager-setup.sh
	install -p -m 755 scripts/fedora-cvs.py /usr/bin/fedora-cvs

