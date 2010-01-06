# fedpkg - a Python library for Fedora Packagers
#
# Copyright (C) 2009 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import os
#import pycurl
import subprocess
import hashlib
import koji
import rpm
import logging

# Define some global variables, put them here to make it easy to change
LOOKASIDE = 'http://cvs.fedoraproject.org/repo/pkgs'
LOOKASIDEHASH = 'md5'
GITBASEURL = 'ssh://%(user)s@pkgs.stg.fedoraproject.org/%(module)s'

# Define our own error class
class FedpkgError(Exception):
    pass

# Setup our logger
# Null logger to avoid spurrious messages, add a handler in app code
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
# This is our log object, clients of this library can use this object to
# define their own logging needs
log = logging.getLogger("fedpkg")
# Add the null handler
log.addHandler(h)

# Define some helper functions, they start with _
def _hash_file(file, hashtype):
    """Return the hash of a file given a hash type"""

    try:
        sum = hashlib.new(hashtype)
    except ValueError:
        raise FedpkgError('Invalid hash type: %s' % hashtype)

    input = open(file, 'rb')
    # Loop through the file reading chunks at a time as to not
    # put the entire file in memory.  That would suck for DVDs
    while True:
        chunk = input.read(8192) # magic number!  Taking suggestions
        if not chunk:
            break # we're done with the file
        sum.update(chunk)
    input.close()
    return sum.hexdigest()

def _verify_file(file, hash, hashtype):
    """Given a file, a hash of that file, and a hashtype, verify.

    Returns True if the file verifies, False otherwise

    """

    # get the hash
    sum = _hash_file(file, hashtype)
    # now do the comparison
    if sum == hash:
        return True
    return False

def _get_build_arches_from_srpm(srpm, arches):
    """Given the path to an srpm, determine the possible build arches

    Use supplied arches as a filter, only return compatible arches

    """

    archlist = arches
    hdr = koji.get_rpm_header(srpm)
    if hdr[rpm.RPMTAG_SOURCEPACKAGE] != 1:
        raise FedpkgError('%s is not a source package.' % srpm)
    buildarchs = hdr[rpm.RPMTAG_BUILDARCHS]
    exclusivearch = hdr[rpm.RPMTAG_EXCLUSIVEARCH]
    excludearch = hdr[rpm.RPMTAG_EXCLUDEARCH]
    # Reduce by buildarchs
    if buildarchs:
        archlist = [a for a in archlist if a in buildarchs]
    # Reduce by exclusive arches
    if exclusivearch:
        archlist = [a for a in archlist if a in exclusivearch]
    # Reduce by exclude arch
    if excludearch:
        archlist = [a for a in archlist if a not in excludearch]
    # do the noarch thing
    if 'noarch' not in excludearch and ('noarch' in buildarchs or \
                                        'noarch' in exclusivearch):
        archlist.append('noarch')
    # See if we have anything compatible.  Should we raise here?
    if not archlist:
        raise FedpkgError('No compatible build arches found in %s' % srpm)
    return archlist

def clean(dry=False, useignore=True):
    """Clean a module checkout of untracked files.

    Can optionally perform a dry-run

    Can optionally not use the ignore rules

    Returns output

    """

    # setup the command, this could probably be done with some python api...
    cmd = ['git', 'clean', '-f', '-d']
    if dry:
        cmd.append('--dry-run')
    if not useignore:
        cmd.append('-x')
    # Run it!
    try:
        proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE)
        output = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    # See if we exited cleanly
    if proc.returncode:
        raise FedpkgError('%s returned %s: %s' %
                          (subprocess.list2cmdline(cmd),
                           proc.returncode, output[0]))
    return output[0]

def clone(module, user, branch=None):
    """Clone a repo, optionally check out a specific branch.

    module is the name of the module to clone

    branch is the name of a branch to checkout instead of origin/master

    gitargs is an optional list of arguments to git clone

    """

    # not implemented yet
    # construct the git url
    giturl = GITBASEURL % {'user': user, 'module': module}
    cmd = ['git', 'clone']
    if branch:
        cmd.extend(['--branch', branch])
    cmd.append(giturl)
    print('Would have ran %s' % subprocess.list2cmdline(cmd))
    return

def clone_with_dirs(module, user):
    """Clone a repo old style with subdirs for each branch.

    module is the name of the module to clone

    gitargs is an option list of arguments to git clone

    """

    # not implemented yet
    print('would have cloned %s with dirs as user %s' % 
          (module, user))
    return

# Create a class for package module
class PackageModule:
    def _findbranch(self):
        """Find the branch we're on"""

        if not os.path.exists(os.path.join(self.path, 'branch')):
            return 'devel'
        branch = open(os.path.join(self.path, 'branch'), 'r').read().strip()
        return branch

    def _getlocalarch(self):
        """Get the local arch as defined by rpm"""
        
        return subprocess.Popen(['rpm --eval %{_arch}'], shell=True,
                        stdout=subprocess.PIPE).communicate()[0].strip('\n')

    def __init__(self, path=os.getcwd()):
        # Initiate a PackageModule object in a given path
        # Set some global variables used throughout
        self.path = path
        self.lookaside = LOOKASIDE
        self.lookasidehash = LOOKASIDEHASH
        self.spec = self.gimmespec()
        self.module = self.spec.split('.spec')[0]
        # Find the branch and set things based from that
        # Still requires a 'branch' file in each branch
        self.branch = self._findbranch()
        if self.branch.startswith('F-'):
            self.distval = self.branch.split('-')[1]
            self.distvar = 'fedora'
            self.dist = '.fc%s' % self.distval
        elif self.branch.startswith('EL-'):
            self.distval = self.branch.split('-')[1]
            self.distvar = 'epel'
            self.dist = '.el%s' % self.distval
        elif self.branch.startswith('OLPC-'):
            self.distval = self.branch.split('-')[1]
            self.distvar = 'olpc'
            self.dist = '.olpc%s' % self.distval
        # Need to do something about no branch here
        elif self.branch == 'devel':
            self.distval = '13' # this is hardset for now, which is bad
            self.distvar = 'fedora'
            self.dist = '.fc%s' % self.distval
        self.rpmdefines = ["--define '_sourcedir %s'" % path,
                           "--define '_specdir %s'" % path,
                           "--define '_builddir %s'" % path,
                           "--define '_srcrpmdir %s'" % path,
                           "--define '_rpmdir %s'" % path,
                           "--define 'dist %s'" % self.dist,
                           "--define '%s %s'" % (self.distvar, self.distval),
                           "--define '%s 1'" % self.distvar]
        self.ver = self.getver()
        self.rel = self.getrel()
        self.localarch = self._getlocalarch()

    def compile(self, arch=None, short=False):
        """Run rpm -bc on a module

        optionally for a specific arch, or short-circuit it

        Returns the output"""

        # Get the sources
        self.sources()
        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if arch:
            cmd.extend(['--target', arch])
        if short:
            cmd.append('--short-circuit')
        cmd.extend(['-bc', os.path.join(self.path, self.spec)])
        # Run the command and capture output
        try:
            proc = subprocess.Popen(' '.join(cmd), stderr=subprocess.STDOUT,
                                    stdout=subprocess.PIPE, shell=True)
            output = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        # See if we exited cleanly
        if proc.returncode:
            raise FedpkgError('%s returned %s: %s' %
                              (subprocess.list2cmdline(cmd),
                               proc.returncode, output[0]))
        return output[0]

    def getver(self):
        """Return the version-release of a package module."""

        cmd = ['rpm']
        cmd.extend(self.rpmdefines)
        cmd.extend(['-q', '--qf', '%{VERSION}', '--specfile',
                    os.path.join(self.path, self.spec)])
        try:
            output = subprocess.Popen(' '.join(cmd), shell=True,
                                      stdout=subprocess.PIPE).communicate()
        except subprocess.CalledProcessError, e:
            raise FedpkgError('Could not get version of %s: %s' % (self.module, e))
        return output[0]

    def getrel(self):
        """Return the version-release of a package module."""

        cmd = ['rpm']
        cmd.extend(self.rpmdefines)
        cmd.extend(['-q', '--qf', '%{RELEASE}', '--specfile',
                    os.path.join(self.path, self.spec)])
        try:
            output = subprocess.Popen(' '.join(cmd), shell=True,
                                      stdout=subprocess.PIPE).communicate()
        except subprocess.CalledProcessError, e:
            raise FedpkgError('Could not get release of %s: %s' % (self.module, e))
        return output[0]

    def gimmespec(self):
        """Print the name of a specfile within a package module"""
    
        # Get a list of files in the path we're looking at
        files = os.listdir(self.path)
        # Search the files for the first one that ends with ".spec"
        for f in files:
            if f.endswith('.spec'):
                return f
        raise FedpkgError('No spec file found.')

    def install(self, arch=None, short=False):
        """Run rpm -bi on a module

        optionally for a specific arch, or short-circuit it

        Returns the output"""

        # Get the sources
        self.sources()
        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if arch:
            cmd.extend(['--target', arch])
        if short:
            cmd.append('--short-circuit')
        cmd.extend(['-bi', os.path.join(self.path, self.spec)])
        # Run the command and capture output
        try:
            proc = subprocess.Popen(' '.join(cmd), stderr=subprocess.STDOUT,
                                    stdout=subprocess.PIPE, shell=True)
            output = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        # See if we exited cleanly
        if proc.returncode:
            raise FedpkgError('%s returned %s: %s' %
                              (subprocess.list2cmdline(cmd),
                               proc.returncode, output[0]))
        return output[0]

    def lint(self):
        """Run rpmlint over a built srpm"""

        # Make sure we have rpms to run on
        srpm = "%s-%s-%s.src.rpm" % (self.module, self.ver, self.rel)
        if not os.path.exists(os.path.join(self.path, srpm)):
            raise FedpkgError('Need to build srpm and rpm first')
        # Get the possible built arches
        arches = _get_build_arches_from_srpm(os.path.join(self.path, srpm),
                                             [self.localarch])
        rpms = []
        for arch in arches:
            rpms.extend([os.path.join(self.path, arch, file) for file in
                         os.listdir(os.path.join(self.path, arch))
                         if file.endswith('.rpm')])
        cmd = ['rpmlint', os.path.join(self.path, srpm)]
        cmd.extend(rpms)
        try:
            output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
        except subprocess.CalledProcessError, e:
            raise FedpkgError(e)
        return output[0]

    def local(self, arch=None, hashtype='sha256'):
        """rpmbuild locally for given arch.

        Takes arch to build for, and hashtype to build with.

        Writes output to a log file and returns output from build.

        """

        # This could really use a list of arches to build for and loop over
        # Get the sources
        self.sources()
        # Determine arch to build for
        if not arch:
            arch = self.localarch
        # build up the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        # This may need to get updated if we ever change our checksum default
        if not hashtype == 'sha256':
            cmd.extend(["--define '_source_filedigest_algorithm %s'" % hashtype,
                        "--define '_binary_filedigest_algorithm %s'" % hashtype])
        cmd.extend(['--target', arch, '-ba',
                    os.path.join(self.path, self.spec)])
        try:
            proc = subprocess.Popen(' '.join(cmd), stderr=subprocess.STDOUT,
                                    stdout=subprocess.PIPE, shell=True)
            output = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        outfile = open(os.path.join(self.path, '.build-%s-%s.log' % (self.ver,
                       self.rel)), 'w')
        outfile.writelines(output[0])
        outfile.close()
        # See if we had a good return or not, raise accordingly
        if proc.returncode:
            raise FedpkgError('%s returned %s: %s' %
                              (subprocess.list2cmdline(cmd),
                               proc.returncode, output[0]))
        return output[0]

    def new_sources(self, files):
        """Replace source file(s) in the lookaside cache"""
    
        # Not fully implimented yet
        for file in files:
            hash = _hash_file(file, self.lookasidehash)
            print "Would upload %s:%s" % (hash, file)
        return

    def prep(self, arch=None):
        """Run rpm -bp on a module

        optionally for a specific arch

        Logs the output and returns the returncode from the prep call"""

        # Get the sources
        self.sources()
        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if arch:
            cmd.extend(['--target', arch])
        cmd.extend(['--nodeps', '-bp', os.path.join(self.path, self.spec)])
        # Run the command and capture output
        log.debug('Running: %s' % ' '.join(cmd))
        try:
            proc = subprocess.Popen(' '.join(cmd), stderr=subprocess.STDOUT,
                                    stdout=subprocess.PIPE, shell=True)
            output = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        log.info(output[0])
        return(proc.returncode)
               
    def sources(self, outdir=None):
        """Download source files"""
    
        archives = open(os.path.join(self.path, 'sources'),
                        'r').readlines()
        # Default to putting the files where the module is
        if not outdir:
            outdir = self.path
        for archive in archives:
            csum, file = archive.split()
            # See if we already have a valid copy downloaded
            outfile = os.path.join(outdir, file)
            if os.path.exists(outfile):
                if _verify_file(outfile, csum, self.lookasidehash):
                    continue
            url = '%s/%s/%s/%s/%s' % (self.lookaside, self.module, file, csum,
                                      file)
            # There is some code here for using pycurl, but for now,
            # just use subprocess
            #output = open(file, 'wb')
            #curl = pycurl.Curl()
            #curl.setopt(pycurl.URL, url)
            #curl.setopt(pycurl.FOLLOWLOCATION, 1)
            #curl.setopt(pycurl.MAXREDIRS, 5)
            #curl.setopt(pycurl.CONNECTTIMEOUT, 30)
            #curl.setopt(pycurl.TIMEOUT, 300)
            #curl.setopt(pycurl.WRITEDATA, output)
            #try:
            #    curl.perform()
            #except:
            #    print "Problems downloading %s" % url
            #    curl.close()
            #    output.close()
            #    return 1
            #curl.close()
            #output.close()
            # These options came from Makefile.common.
            # Probably need to support wget too
            command = ['curl', '-H',  'Pragma:', '-O', '-R', '-S',  '--fail',
                       '--show-error', url]
            try:
                subprocess.check_call(command, cwd=outdir)
            except subprocess.CalledProcessError, e:
                raise FedpkgError('Could not download %s: %s' % (url, e))
            if not _verify_file(outfile, csum, self.lookasidehash):
                raise FedpkgError('%s failed checksum' % file)
        return

    def srpm(self, hashtype='sha256'):
        """Create an srpm using hashtype from content in the module
    
        Requires sources already downloaded.
    
        """

        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        # This may need to get updated if we ever change our checksum default
        if not hashtype == 'sha256':
            cmd.extend(["--define '_source_filedigest_algorithm %s'" % hashtype,
                    "--define '_binary_filedigest_algorithm %s'" % hashtype])
        cmd.extend(['--nodeps', '-bs', os.path.join(self.path, self.spec)])
        try:
            subprocess.check_call(' '.join(cmd), shell=True)
        except subprocess.CalledProcessError, e:
            raise FedpkgError('Could not build %s: %s' % (self.module, e))
        return