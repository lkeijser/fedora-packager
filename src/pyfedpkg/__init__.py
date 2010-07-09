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
import sys
import shutil
import re
import pycurl
import subprocess
import hashlib
import koji
import rpm
import logging
import git
import ConfigParser
import stat
import StringIO
import tempfile

# Define some global variables, put them here to make it easy to change
LOOKASIDE = 'http://cvs.fedoraproject.org/repo/pkgs'
LOOKASIDEHASH = 'md5'
LOOKASIDE_CGI = 'https://cvs.fedoraproject.org/repo/pkgs/upload.cgi'
GITBASEURL = 'ssh://%(user)s@pkgs.stg.fedoraproject.org/%(module)s'
ANONGITURL = 'git://pkgs.stg.fedoraproject.org/%(module)s'
UPLOADEXTS = ['tar', 'gz', 'bz2', 'lzma', 'xz', 'Z', 'zip', 'tff', 'bin',
              'tbz', 'tbz2', 'tlz', 'txz', 'pdf', 'rpm', 'jar', 'war', 'db',
              'cpio', 'jisp', 'egg', 'gem']
BRANCHFILTER = 'FC?-\d\d?|master'

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

def _run_command(cmd, shell=False, env=None):
    """Run the given command.

    Will determine if caller is on a real tty and if so stream to the tty

    Or else will run and log output.

    cmd is a list of the command and arguments

    shell is whether to run in a shell or not, defaults to False

    env is a dict of environment variables to use (if any)

    Raises on error, or returns nothing.

    """

    # Process any environment vairables.
    environ = os.environ
    if env:
        for item in env.keys():
            log.debug('Adding %s:%s to the environment' % (item, env[item]))
            environ[item] = env[item]
    # Check if we're supposed to be on a shell.  If so, the command must
    # be a string, and not a list.
    command = cmd
    if shell:
        command = ' '.join(cmd)
    # Check to see if we're on a real tty, if so, stream it baby!
    if sys.stdout.isatty():
        log.debug('Running %s directly on the tty' %
                  subprocess.list2cmdline(cmd))
        try:
            subprocess.check_call(command, env=environ, stdout=sys.stdout,
                                  stderr=sys.stderr, shell=shell)
        except subprocess.CalledProcessError, e:
            raise FedpkgError(e)
        except KeyboardInterrupt:
            raise FedpkgError()
    else:
        # Ok, we're not on a live tty, so pipe and log.
        log.debug('Running %s and logging output' %
                  subprocess.list2cmdline(cmd))
        try:
            proc = subprocess.Popen(command, env=environ,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, shell=shell)
            output, error = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        log.info(output)
        if error:
            log.error(error)
        if proc.returncode:
            raise FedpkgError('Command %s returned code %s with error: %s' %
                              (subprocess.list2cmdline(cmd),
                               proc.returncode,
                               error))
    return

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

def _srpmdetails(srpm):
    """Return a tuple of package name, package files, and upload files."""

    # get the name
    cmd = ['rpm', '-qp', '--qf', '%{NAME}', srpm]
            # Run the command
    log.debug('Running: %s' % subprocess.list2cmdline(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    name = output
    if error:
        log.error(error)
        raise FedpkgError('Error querying srpm')

    # now get the files and upload files
    files = []
    uploadfiles = []
    cmd = ['rpm', '-qpl', srpm]
    log.debug('Running: %s' % subprocess.list2cmdline(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    if error:
        log.error(error)
        raise FedpkgError('Error querying srpm')
    contents = output.split()
    # Cycle through the stuff and sort correctly by its extension
    for file in contents:
        if file.rsplit('.')[-1] in UPLOADEXTS:
            uploadfiles.append(file)
        else:
            files.append(file)

    return((name, files, uploadfiles))

def clean(dry=False, useignore=True):
    """Clean a module checkout of untracked files.

    Can optionally perform a dry-run

    Can optionally not use the ignore rules

    Logs output and returns the returncode

    """

    # setup the command, this could probably be done with some python api...
    cmd = ['git', 'clean', '-f', '-d']
    if dry:
        cmd.append('--dry-run')
    if not useignore:
        cmd.append('-x')
    # Run it!
    log.debug('Running: %s' % subprocess.list2cmdline(cmd))
    try:
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    log.info(output)
    if error:
        log.error(error)
    return proc.returncode

def clone(module, user, path=os.getcwd(), branch=None, bare_dir=None):
    """Clone a repo, optionally check out a specific branch.

    module is the name of the module to clone

    path is the basedir to perform the clone in

    branch is the name of a branch to checkout instead of origin/master

    bare_dir is the name of a directory to make a bare clone too if this is a
    bare clone. None otherwise.

    Logs the output and returns nothing.

    """

    # construct the git url
    giturl = GITBASEURL % {'user': user, 'module': module}
    # Create the command
    cmd = ['git', 'clone']
    # do the clone
    if branch and bare_dir:
        log.debug('Cloning %s bare with branch %s' % (giturl, branch))
        cmd.extend(['--branch', branch, '--bare', giturl, bare_dir])
    elif branch:
        log.debug('Cloning %s with branch %s' % (giturl, branch))
        cmd.extend(['--branch', branch, giturl])
    elif bare_dir:
        log.debug('Cloning %s bare' % giturl)
        cmd.extend(['--bare', giturl, bare_dir])
    else:
        log.debug('Cloning %s' % giturl)
        cmd.extend([giturl])
    _run_command(cmd)
    return

def clone_with_dirs(module, user, path=os.getcwd()):
    """Clone a repo old style with subdirs for each branch.

    module is the name of the module to clone

    gitargs is an option list of arguments to git clone

    """

    # Get the full path of, and git object for, our directory of branches
    top_path = os.path.join(path, module)
    top_git = git.Git(top_path)

    # Create our new top directory
    try:
        os.mkdir(top_path)
    except (OSError), e:
        raise FedpkgError('Could not create directory for module %s: %s' %
                (module, e))

    # Create a bare clone first. This gives us a good list of branches
    clone(module, user, top_path, bare_dir="fedpkg.git")
    # Get the full path to, and a git object for, our new bare repo
    repo_path = os.path.join(top_path, "fedpkg.git")
    repo_git = git.Git(repo_path)

    # Get a branch listing
    branches = [x for x in repo_git.branch().split() if x != "*" and
            re.match(BRANCHFILTER, x)]

    for branch in branches:
        try:
            # Make a local clone for our branch
            top_git.clone("--branch", branch, repo_path, branch)

            # Set the origin correctly
            branch_path = os.path.join(top_path, branch)
            branch_git = git.Git(branch_path)
            branch_git.config("--replace-all", "remote.origin.url",
                    GITBASEURL % {'user': user, 'module': module})
        except (git.GitCommandError, OSError), e:
            raise FedpkgError('Could not locally clone %s from %s: %s' %
                    (branch, repo_path, e))

    # We don't need this now. Ignore errors since keeping it does no harm
    shutil.rmtree(repo_path, ignore_errors=True)

    # consistent with clone method since the commands should return 0 when
    # successful.
    return 0

def get_latest_commit(module):
    """Discover the latest commit has for a given module and return it"""

    # This is stupid that I have to use subprocess :/
    url = ANONGITURL % {'module': module}
    cmd = ['git', 'ls-remote', url, 'master']
    try :
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    if error:
        raise FedpkgError('Got an error finding head for %s: %s' %
                          (module, error))
    # Return the hash sum
    return output.split()[0]

def import_srpm(srpm, path=os.getcwd()):
    """Import the contents of an srpm into a repo.

    srpm: File to import contents from

    path: optional path to work in, defaults to cwd.

    This function will add/remove content to match the srpm,

    upload new files to the lookaside, and stage the changes.

    Returns a list of files to upload.

    """

    # see if the srpm even exists
    srpm = os.path.abspath(srpm)
    if not os.path.exists(srpm):
        raise FedpkgError('File not found.')
    # bail if we're dirty
    repo = git.Repo(path)
    if repo.is_dirty():
        raise FedpkgError('There are uncommitted changes in your repo')
    # Get the details of the srpm
    name, files, uploadfiles = _srpmdetails(srpm)

    # Need a way to make sure the srpm name matches the repo some how.

    # Get a list of files we're currently tracking
    ourfiles = repo.git.ls_files().split()
    # Trim out sources and .gitignore
    try:
        ourfiles.remove('.gitignore')
        ourfiles.remove('sources')
    except ValueError:
        pass
    try:
        ourfiles.remove('sources')
    except ValueError:
        pass

    # Things work better if we're in our module directory
    oldpath = os.getcwd()
    os.chdir(path)

    # Look through our files and if it isn't in the new files, remove it.
    for file in ourfiles:
        if file not in files:
            log.info("Removing no longer used file: %s" % file)
            rv = repo.index.remove([file])
            os.remove(file)

    # Extract new files
    cmd = ['rpm2cpio', srpm]
    # We have to force cpio to copy out (u) because git messes with
    # timestamps
    cmd2 = ['cpio', '-iud', '--quiet']

    rpmcall = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    cpiocall = subprocess.Popen(cmd2, stdin=rpmcall.stdout)
    output, err = cpiocall.communicate()
    if output:
        log.debug(output)
    if err:
        os.chdir(oldpath)
        raise FedpkgError("Got an error from rpm2cpio: %s" % err)

    # And finally add all the files we know about (and our stock files)
    for file in ('.gitignore', 'sources'):
        if not os.path.exists(file):
            # Create the file
            open(file, 'w').close()
        files.append(file)
    rv = repo.index.add(files)
    # Return to the caller and let them take it from there.
    os.chdir(oldpath)
    return(uploadfiles)

def new(path=os.getcwd()):
    """Return changes in a repo since the last tag"""

    # setup the repo object based on our path
    try:
        repo = git.Repo(path)
    except git.errors.InvalidGitRepositoryError:
        raise FedpkgError('%s is not a valid repo' % path)
    # Find the latest tag
    tag = repo.git.describe('--tags', '--abbrev=0')
    # Now get the diff
    log.debug('Diffing from tag %s' % tag)
    return repo.git.diff('-M', tag)


class Lookaside(object):
    """ Object for interacting with the lookaside cache. """

    def __init__(self, url=LOOKASIDE_CGI):
        self.lookaside_cgi = url
        self.cert_file = os.path.expanduser('~/.fedora.cert')
        self.ca_cert_file = os.path.expanduser('~/.fedora-server-ca.cert')

    def _create_curl(self):
        """
        Common curl setup options used for all requests to lookaside.
        """
        curl = pycurl.Curl()

        curl.setopt(pycurl.URL, self.lookaside_cgi)

        # Set the users Fedora certificate:
        if os.path.exists(self.cert_file):
            curl.setopt(pycurl.SSLCERT, self.cert_file)
        else:
            log.warn("Missing certificate: %s" % self.cert_file)

        # Set the Fedora CA certificate:
        if os.path.exists(self.ca_cert_file):
            curl.setopt(pycurl.CAINFO, self.ca_cert_file)
        else:
            log.warn("Missing certificate: %s" % self.ca_cert_file)

        return curl

    def file_exists(self, pkg_name, filename, md5sum):
        """
        Return True if the given file exists in the lookaside cache, False
        if not.

        A FedpkgError will be thrown if the request looks bad or something
        goes wrong. (i.e. the lookaside URL cannot be reached, or the package
        named does not exist)
        """

        # String buffer, used to receive output from the curl request:
        buf = StringIO.StringIO()

        # Setup the POST data for lookaside CGI request. The use of
        # 'filename' here appears to be what differentiates this
        # request from an actual file upload.
        post_data = [
                ('name', pkg_name),
                ('md5sum', md5sum),
                ('filename', filename)]

        curl = self._create_curl()
        curl.setopt(pycurl.WRITEFUNCTION, buf.write)
        curl.setopt(pycurl.HTTPPOST, post_data)

        curl.perform()
        curl.close()
        output = buf.getvalue().strip()

        # Lookaside CGI script returns these strings depending on whether
        # or not the file exists:
        if output == "Available":
            return True
        if output == "Missing":
            return False

        # Something unexpected happened, will trigger if the lookaside URL
        # cannot be reached, the package named does not exist, and probably
        # some other scenarios as well.
        raise FedpkgError("Error checking for %s at: %s" %
                (filename, self.lookaside_cgi))

    def upload_file(self, pkg_name, filepath, md5sum):
        """ Upload a file to the lookaside cache. """

        # Setup the POST data for lookaside CGI request. The use of
        # 'file' here appears to trigger the actual upload:
        post_data = [
                ('name', pkg_name),
                ('md5sum', md5sum),
                ('file', (pycurl.FORM_FILE, filepath))]

        curl = self._create_curl()
        curl.setopt(pycurl.HTTPPOST, post_data)

        # TODO: disabled until safe way to test is known. Watchout for the
        # file parameter:
        curl.perform()
        curl.close()


class GitIgnore(object):
    """ Smaller wrapper for managing a .gitignore file and it's entries. """

    def __init__(self, path):
        """
        Create GitIgnore object for the given full path to a .gitignore file.

        File does not have to exist yet, and will be created if you write out
        any changes.
        """
        self.path = path

        # Lines of the .gitignore file, used to check if entries need to be added
        # or already exist.
        self.__lines = []
        if os.path.exists(self.path):
            gitignore_file = open(self.path, 'r')
            self.__lines = gitignore_file.readlines()
            gitignore_file.close()

        # Set to True if we end up making any modifications, used to
        # prevent unecessary writes.
        self.modified = False

    def add(self, line):
        """
        Add a line to .gitignore, but check if it's a duplicate first.
        """

        # Append a newline character if the given line didn't have one:
        if line[-1] != '\n':
            line = "%s\n" % line

        # Add this line if it doesn't already exist:
        if not line in self.__lines:
            self.__lines.append(line)
            self.modified = True

    def write(self):
        """ Write the new .gitignore file if any modifications were made. """
        if self.modified:
            gitignore_file = open(self.path, 'w')
            for line in self.__lines:
                gitignore_file.write(line)
            gitignore_file.close()


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
        log.debug('Creating module object from %s' % path)
        self.path = path
        self.lookaside = LOOKASIDE
        self.lookasidehash = LOOKASIDEHASH
        self.spec = self.gimmespec()
        self.module = self.spec.split('.spec')[0]
        self.localarch = self._getlocalarch()
        # Set the default mock config to None, not all branches have a config
        self.mockconfig = None
        # Set a place holder for kojisession
        self.kojisession = None
        # Find the branch and set things based from that
        # Still requires a 'branch' file in each branch
        self.branch = self._findbranch()
        if self.branch.startswith('F-'):
            self.distval = self.branch.split('-')[1]
            self.distvar = 'fedora'
            self.dist = '.fc%s' % self.distval
            self.target = 'dist-f%s-updates-candidate' % self.distval
            self.mockconfig = 'fedora-%s-%s' % (self.distval, self.localarch)
        elif self.branch.startswith('EL-'):
            self.distval = self.branch.split('-')[1]
            self.distvar = 'epel'
            self.dist = '.el%s' % self.distval
            self.target = 'dist-%sE-epel-testing-candidate' % self.distval
            self.mockconfig = 'epel-%s-%s' % (self.distval, self.localarch)
        elif self.branch.startswith('OLPC-'):
            self.distval = self.branch.split('-')[1]
            self.distvar = 'olpc'
            self.dist = '.olpc%s' % self.distval
            self.target = 'dist-olpc%s' % self.distval
        # Need to do something about no branch here
        elif self.branch == 'devel':
            self.distval = '14' # this is hardset for now, which is bad
            self.distvar = 'fedora'
            self.dist = '.fc%s' % self.distval
            self.target = 'dist-f%s' % self.distval # will be dist-rawhide
            self.mockconfig = 'fedora-devel-%s' % self.localarch
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
        try:
            self.repo = git.Repo(path)
        except git.errors.InvalidGitRepositoryError:
            raise FedpkgError('%s is not a valid repo' % path)

    def build(self, skip_tag=False, scratch=False, background=False,
              url=None, chain=None):
        """Initiate a build of the module.  Available options are:

        skip_tag: Skip the tag action after the build

        scratch: Perform a scratch build

        background: Perform the build with a low priority

        url: A url to an uploaded srpm to build from

        chain: A chain build set

        This function submits the task to koji and returns the taskID

        It is up to the client to wait or watch the task.

        """

        # Make sure we have a valid session.
        if not self.kojisession:
            raise FedpkgError('No koji session found.')
        # construct the url
        if not url:
            # We don't have a url, so build from the latest commit
            # Check to see if the tree is dirty
            if self.repo.is_dirty():
                raise FedpkgError('There are uncommitted changes in your repo')
            # Need to check here to see if the local commit you want to build is
            # pushed or not
            # This doesn't work if the local branch name doesn't match the remote
            if self.repo.git.rev_list('...origin/%s' % self.repo.active_branch):
                raise FedpkgError('There are unpushed changes in your repo')
            # Get the commit hash to build
            commit = self.repo.iter_commits().next().sha
            url = ANONGITURL % {'module': self.module} + '?#%s' % commit
        # Check to see if the target is valid
        build_target = self.kojisession.getBuildTarget(self.target)
        if not build_target:
            raise FedpkgError('Unknown build target: %s' % self.target)
        # see if the dest tag is locked
        dest_tag = self.kojisession.getTag(build_target['dest_tag_name'])
        if not dest_tag:
            raise FedpkgError('Unknown destination tag %s' %
                              build_target['dest_tag_name'])
        if dest_tag['locked'] and not scratch:
            raise FedpkgError('Destination tag %s is locked' % dest_tag['name'])
        # If we're chain building, make sure inheritance works
        if chain:
            ancestors = self.kojisession.getFullInheritance(build_target['build_tag'])
            if dest_tag['id'] not in [build_target['build_tag']] + [ancestor['parent_id'] for ancestor in ancestors]:
                raise FedpkgError('Packages in destination tag ' \
                                  '%(dest_tag_name)s are not inherited by' \
                                  'build tag %(build_tag_name)s' %
                                  build_target)
        # define our dictionary for options
        opts = {}
        # Set a placeholder for the build priority
        priority = None
        if skip_tag:
            opts['skip_tag'] = True
        if scratch:
            opts['scratch'] = True
        if background:
            priority = 5 # magic koji number :/

        # Now submit the task and get the task_id to return
        # Handle the chain build version
        if chain:
            log.debug('Adding %s to the chain' % url)
            chain[-1].append(url)
            log.debug('Building chain %s for %s with options %s and a ' \
                      'priority of %s' %
                      (chain, self.target, opts, priority))
            task_id = self.kojisession.chainBuild(chain, self.target, opts,
                                                  priority=priority)
        # Now handle the normal build
        else:
            log.debug('Building %s for %s with options %s and a priority of %s' %
                      (url, self.target, opts, priority))
            task_id = self.kojisession.build(url, self.target, opts,
                                             priority=priority)
        log.info('Created task: %s' % task_id)
        log.info('Task info: %s/taskinfo?taskID=%s' % (self.kojiweburl,
                                                       task_id))
        return task_id

    def clog(self):
        """Write the latest spec changelog entry to a clog file"""

        # This is a little ugly.  We want to find where %changelog starts,
        # then only deal with the content up to the first empty newline.
        # Then remove any lines that start with $ or %, and then replace
        # %% with %

        # This should probably change behavior from dist-cvs and not print
        # the first line with the date/name/version as git has that info
        # already and it would be redundant.

        cloglines = []
        spec = open(os.path.join(self.path, self.spec), 'r').readlines()
        for line in spec:
            if line.startswith('%changelog'):
                # Grab all the lines below changelog
                for line2 in spec[spec.index(line):]:
                    if line2.startswith('\n'):
                        break
                    if line2.startswith('$'):
                        continue
                    if line2.startswith('%'):
                        continue
                    cloglines.append(line2.replace('%%', '%'))
        # Now open the clog file and write out the lines
        clogfile = open(os.path.join(self.path, 'clog'), 'w')
        clogfile.writelines(cloglines)
        return

    def commit(self, message=None, file=None, files=[]):
        """Commit changes to a module.

        Can take a message to use as the commit message

        a file to find the commit message within

        and a list of files to commit.

        Requires the caller be a real tty or a message passed.

        Logs the output and returns nothing.

        """

        # First lets see if we got a message or we're on a real tty:
        if not sys.stdin.isatty():
            if not message or not file:
                raise FedpkgError('Must have a commit message or be on a real tty.')

        # construct the git command
        # We do this via subprocess because the git module is terrible.
        cmd = ['git', 'commit']
        if message:
            cmd.extend(['-m', message])
        elif file:
            cmd.extend(['-F', os.path.abspath(file)])
        if not files:
            cmd.append('-a')
        else:
            cmd.extend(files)
        # make it so
        _run_command(cmd)
        return

    def compile(self, arch=None, short=False):
        """Run rpm -bc on a module

        optionally for a specific arch, or short-circuit it

        Logs the output and returns nothing

        """

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
        # Run the command
        _run_command(cmd, shell=True)
        return

    def diff(self, cached=False, files=[]):
        """Excute a git diff

        optionally diff the cached or staged changes

        Takes an optional list of files to diff reletive to the module base
        directory

        Logs the output and returns nothing

        """

        # Things work better if we're in our module directory
        oldpath = os.getcwd()
        os.chdir(self.path)

        # build up the command
        cmd = ['git', 'diff']
        if cached:
            cmd.append('--cached')
        if files:
            cmd.extend(files)

        # Run it!
        _run_command(cmd)
        # popd
        os.chdir(oldpath)
        return

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
        """Return the name of a specfile within a package module"""
    
        # Get a list of files in the path we're looking at
        files = os.listdir(self.path)
        # Search the files for the first one that ends with ".spec"
        for f in files:
            if f.endswith('.spec'):
                return f
        raise FedpkgError('No spec file found.')

    def koji_upload(self, file, path, callback=None):
        """Upload a file to koji

        file is the file you wish to upload

        path is the relative path on the server to upload to

        callback is the progress callback to use, if any

        Returns nothing or raises

        """

        # See if we actually have a file
        if not os.path.exists(file):
            raise FedpkgError('No such file: %s' % file)
        if not self.kojisession:
            raise FedpkgError('No active koji session.')
        # This should have a try and catch koji errors
        self.kojisession.uploadWrapper(file, path, callback = callback)
        return

    def init_koji(self, user, kojiconfig=None, url=None):
        """Initiate a koji session.  Available options are:

        user: User to log into koji as

        kojiconfig: Use an alternate koji config file

        This function attempts to log in and returns nothing or raises.

        """

        # Stealing a bunch of code from /usr/bin/koji here, too bad it isn't
        # in a more usable library form
        defaults = {
                    'server' : 'http://localhost/kojihub',
                    'weburl' : 'http://localhost/koji',
                    'pkgurl' : 'http://localhost/packages',
                    'topdir' : '/mnt/koji',
                    'cert': '~/.koji/client.crt',
                    'ca': '~/.koji/clientca.crt',
                    'serverca': '~/.koji/serverca.crt',
                    'authtype': None
                    }
        # Process the configs in order, global, user, then any option passed
        configs = ['/etc/koji.conf', os.path.expanduser('~/.koji/config')]
        if kojiconfig:
            configs.append(os.path.join(kojiconfig))
        for configFile in configs:
            if os.access(configFile, os.F_OK):
                f = open(configFile)
                config = ConfigParser.ConfigParser()
                config.readfp(f)
                f.close()
                if config.has_section('koji'):
                    for name, value in config.items('koji'):
                        if defaults.has_key(name):
                            # HAAACK to force use of the stg environment
                            if value.startswith('http://koji.fedoraproject.org'):
                                value = value.replace('http://koji.fedoraproject.org',
                                                      'http://koji.stg.fedoraproject.org')
                            defaults[name] = value
        # Expand out the directory options
        for name in ('topdir', 'cert', 'ca', 'serverca'):
            defaults[name] = os.path.expanduser(defaults[name])
        session_opts = {'user': user}
        # We assign the kojisession to our self as it can be used later to
        # watch the tasks.
        self.kojisession = koji.ClientSession(defaults['server'], session_opts)
        # save the weburl for later use too
        self.kojiweburl = defaults['weburl']
        # log in using ssl
        self.kojisession.ssl_login(defaults['cert'], defaults['ca'],
                                   defaults['serverca'])
        if not self.kojisession.logged_in:
            raise FedpkgError('Could not auth with koji as %s' % user)
        return

    def install(self, arch=None, short=False):
        """Run rpm -bi on a module

        optionally for a specific arch, or short-circuit it

        Logs the output and returns nothing

        """

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
        # Run the command
        _run_command(cmd, shell=True)
        return

    def lint(self):
        """Run rpmlint over a built srpm

        Log the output and returns nothing

        """

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
        # Run the command
        _run_command(cmd, shell=True)
        return

    def local(self, arch=None, hashtype='sha256'):
        """rpmbuild locally for given arch.

        Takes arch to build for, and hashtype to build with.

        Writes output to a log file and logs it to the logger

        Returns the returncode from the build call

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
        # Run the command
        log.debug('Running: %s' % ' '.join(cmd))
        try:
            proc = subprocess.Popen(' '.join(cmd), stderr=subprocess.PIPE,
                                    stdout=subprocess.PIPE, shell=True)
            output, error = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        outfile = open(os.path.join(self.path, '.build-%s-%s.log' % (self.ver,
                       self.rel)), 'w')
        outfile.writelines(output)
        log.info(output)
        if error:
            outfile.writelines(error)
            log.error(error)
        outfile.close()
        return proc.returncode

    def mockbuild(self, mockargs=[]):
        """Build the package in mock, using mockargs

        Log the output and returns nothing

        """

        # Make sure we have an srpm to run on
        srpm = os.path.join(self.path,
                            "%s-%s-%s.src.rpm" % (self.module,
                                                  self.ver, self.rel))
        if not os.path.exists(srpm):
            raise FedpkgError('Need to build srpm first')

        # setup the command
        cmd = ['mock']
        cmd.extend(mockargs)
        cmd.extend(['-r', self.mockconfig, '--resultdir',
                    os.path.join(self.path, self.module, self.ver, self.rel),
                    '--rebuild', srpm])
        # Run the command
        _run_command(cmd)
        return

    def upload(self, files, replace=False):
        """Upload source file(s) in the lookaside cache

        Can optionally replace the existing tracked sources

        """

        oldpath = os.getcwd()
        os.chdir(self.path)

        # Decide to overwrite or append to sources:
        if replace:
            sources = []
            sources_file = open('sources', 'w')
        else:
            sources = open('sources', 'r').readlines()
            sources_file = open('sources', 'a')

        # Will add new sources to .gitignore if they are not already there.
        gitignore = GitIgnore(os.path.join(self.path, '.gitignore'))

        lookaside = Lookaside()
        for f in files:
            # TODO: Skip empty file needed?
            file_hash = _hash_file(f, self.lookasidehash)
            log.info("Uploading: %s  %s" % (file_hash, f))
            file_basename = os.path.basename(f)
            if not "%s  %s\n" % (file_hash, file_basename) in sources:
                sources_file.write("%s  %s\n" % (file_hash, file_basename))

            # Add this file to .gitignore if it's not already there:
            gitignore.add(file_basename)

            if lookaside.file_exists(self.module, file_basename, file_hash):
                # Already uploaded, skip it:
                log.info("File already uploaded: %s" % file_basename)
            else:
                # Ensure the new file is readable:
                os.chmod(f, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                #lookaside.upload_file(self.module, f, file_hash)
                # For now don't use the pycurl upload function as it does
                # not produce any progress output.  Cheat and use curl
                # directly.
                # This command is stolen from the dist-cvs make file
                # It assumes and hard codes the cert file name/location
                cmd = ['curl', '-k', '--cert',
                       os.path.expanduser('~/.fedora.cert'), '--fail', '-o',
                       '/dev/null', '--show-error', '--progress-bar', '-F',
                       'name=%s' % self.module, '-F', 'md5sum=%s' % file_hash,
                       '-F', 'file=@%s' % f, LOOKASIDE_CGI]
                _run_command(cmd)

        sources_file.close()

        # Write .gitignore with the new sources if anything changed:
        gitignore.write()

        rv = self.repo.index.add(['sources', '.gitignore'])

        # Change back to original working dir:
        os.chdir(oldpath)

        return

    def prep(self, arch=None):
        """Run rpm -bp on a module

        optionally for a specific arch

        Logs the output and returns the returncode from the prep call

        """

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
            proc = subprocess.Popen(' '.join(cmd), stderr=subprocess.PIPE,
                                    stdout=subprocess.PIPE, shell=True)
            output, error = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        log.info(output)
        if error:
            log.error(error)
        return proc.returncode
               
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
            _run_command(command)
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
        _run_command(cmd, shell=True)
        return

    def unused_patches(self):
        """Discover patches checked into source control that are not used

        Returns a list of unused patches, which may be empty.

        """

        # Create a list for unused patches
        unused = []
        # Get the content of spec into memory for fast searching
        spec = open(self.spec, 'r').read()
        # Get a list of files tracked in source control
        files = self.repo.git.ls_files('--exclude-standard').split()
        for file in files:
            # throw out non patches
            if not file.endswith('.patch'):
                continue
            if file not in spec:
                unused.append(file)
        return unused
