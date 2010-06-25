#!/usr/bin/python
# fedpkg - a script to interact with the Fedora Packaging system
#
# Copyright (C) 2009 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import argparse
import pyfedpkg
import fedora_cert
import os
import sys
import logging
import koji
import xmlrpclib
import time
import random
import string

# Define packages which belong to specific secondary arches
# This is ugly and should go away.  A better way to do this is to have a list
# of secondary arches, and then check the spec file for ExclusiveArch that
# is one of the secondary arches, and handle it accordingly.
SECONDARY_ARCH_PKGS = {'sparc': ['silo', 'prtconf', 'lssbus', 'afbinit',
                                 'piggyback', 'xorg-x11-drv-sunbw2',
                                 'xorg-x11-drv-suncg14', 'xorg-x11-drv-suncg3',
                                 'xorg-x11-drv-suncg6', 'xorg-x11-drv-sunffb',
                                 'xorg-x11-drv-sunleo', 'xorg-x11-drv-suntcx'],
                       'ppc': ['ppc64-utils', 'yaboot'],
                       'arm': []}

# Add a class stolen from /usr/bin/koji to watch tasks
# this was cut/pasted from koji, and then modified for local use.
# The formatting is koji style, not the stile of this file.  Do not use these
# functions as a style guide.
# This is fragile and hopefully will be replaced by a real kojiclient lib.
class TaskWatcher(object):

    def __init__(self,task_id,session,level=0,quiet=False):
        self.id = task_id
        self.session = session
        self.info = None
        self.level = level
        self.quiet = quiet

    #XXX - a bunch of this stuff needs to adapt to different tasks

    def str(self):
        if self.info:
            label = koji.taskLabel(self.info)
            return "%s%d %s" % ('  ' * self.level, self.id, label)
        else:
            return "%s%d" % ('  ' * self.level, self.id)

    def __str__(self):
        return self.str()

    def get_failure(self):
        """Print infomation about task completion"""
        if self.info['state'] != koji.TASK_STATES['FAILED']:
            return ''
        error = None
        try:
            result = self.session.getTaskResult(self.id)
        except (xmlrpclib.Fault,koji.GenericError),e:
            error = e
        if error is None:
            # print "%s: complete" % self.str()
            # We already reported this task as complete in update()
            return ''
        else:
            return '%s: %s' % (error.__class__.__name__, str(error).strip())

    def update(self):
        """Update info and log if needed.  Returns True on state change."""
        if self.is_done():
            # Already done, nothing else to report
            return False
        last = self.info
        self.info = self.session.getTaskInfo(self.id, request=True)
        if self.info is None:
            log.error("No such task id: %i" % self.id)
            sys.exit(1)
        state = self.info['state']
        if last:
            #compare and note status changes
            laststate = last['state']
            if laststate != state:
                log.info("%s: %s -> %s" % (self.str(),
                                           self.display_state(last),
                                           self.display_state(self.info)))
                return True
            return False
        else:
            # First time we're seeing this task, so just show the current state
            log.info("%s: %s" % (self.str(), self.display_state(self.info)))
            return False

    def is_done(self):
        if self.info is None:
            return False
        state = koji.TASK_STATES[self.info['state']]
        return (state in ['CLOSED','CANCELED','FAILED'])

    def is_success(self):
        if self.info is None:
            return False
        state = koji.TASK_STATES[self.info['state']]
        return (state == 'CLOSED')

    def display_state(self, info):
        if info['state'] == koji.TASK_STATES['OPEN']:
            if info['host_id']:
                host = self.session.getHost(info['host_id'])
                return 'open (%s)' % host['name']
            else:
                return 'open'
        elif info['state'] == koji.TASK_STATES['FAILED']:
            return 'FAILED: %s' % self.get_failure()
        else:
            return koji.TASK_STATES[info['state']].lower()

# Add a simple function to print usage, for the 'help' command
def usage(args):
    parser.print_help()

# Define our stub functions
def _is_secondary(module):
    """Check a list to see if the package is a secondary arch package"""

    for arch in SECONDARY_ARCH_PKGS.keys():
        if module in SECONDARY_ARCH_PKGS[arch]:
            return arch
    return None

def _get_secondary_config(mymodule):
    """Return the right config for a given secondary arch"""

    arch = _is_secondary(mymodule.module)
    if arch:
        if arch == 'ppc' and mymodule.distvar == 'feodra' and \
           mymodule.distval < '13':
            return None
        return os.path.expanduser('~/.koji/%s-config' % arch)
    else:
        return None

def _display_tasklist_status(tasks):
    free = 0
    open = 0
    failed = 0
    done = 0
    for task_id in tasks.keys():
        status = tasks[task_id].info['state']
        if status == koji.TASK_STATES['FAILED']:
            failed += 1
        elif status == koji.TASK_STATES['CLOSED'] or status == koji.TASK_STATES['CANCELED']:
            done += 1
        elif status == koji.TASK_STATES['OPEN'] or status == koji.TASK_STATES['ASSIGNED']:
            open += 1
        elif status == koji.TASK_STATES['FREE']:
            free += 1
    log.info("  %d free  %d open  %d done  %d failed" % (free, open, done, failed))

def _display_task_results(tasks):
    for task in [task for task in tasks.values() if task.level == 0]:
        state = task.info['state']
        task_label = task.str()

        if state == koji.TASK_STATES['CLOSED']:
            log.info('%s completed successfully' % task_label)
        elif state == koji.TASK_STATES['FAILED']:
            log.info('%s failed' % task_label)
        elif state == koji.TASK_STATES['CANCELED']:
            log.info('%s was canceled' % task_label)
        else:
            # shouldn't happen
            log.info('%s has not completed' % task_label)

def _watch_koji_tasks(session, tasklist, quiet=False):
    if not tasklist:
        return
    log.info('Watching tasks (this may be safely interrupted)...')
    # Place holder for return value
    rv = 0
    try:
        tasks = {}
        for task_id in tasklist:
            tasks[task_id] = TaskWatcher(task_id, session, quiet=quiet)
        while True:
            all_done = True
            for task_id,task in tasks.items():
                changed = task.update()
                if not task.is_done():
                    all_done = False
                else:
                    if changed:
                        # task is done and state just changed
                        if not quiet:
                            _display_tasklist_status(tasks)
                    if not task.is_success():
                        rv = 1
                for child in session.getTaskChildren(task_id):
                    child_id = child['id']
                    if not child_id in tasks.keys():
                        tasks[child_id] = TaskWatcher(child_id, session, task.level + 1, quiet=quiet)
                        tasks[child_id].update()
                        # If we found new children, go through the list again,
                        # in case they have children also
                        all_done = False
            if all_done:
                if not quiet:
                    print
                    _display_task_results(tasks)
                break

            time.sleep(1)
    except (KeyboardInterrupt):
        if tasks:
            log.info(
"""\nTasks still running. You can continue to watch with the 'koji watch-task' command.
Running Tasks:
%s""" % '\n'.join(['%s: %s' % (t.str(), t.display_state(t.info))
                   for t in tasks.values() if not t.is_done()]))
        # /us/rbin/koji considers a ^c while tasks are running to be a
        # non-zero exit.  I don't quite agree, so I comment it out here.
        #rv = 1
    return rv

# Stole these three functions from /usr/bin/koji
def _format_size(size):
    if (size / 1073741824 >= 1):
        return "%0.2f GiB" % (size / 1073741824.0)
    if (size / 1048576 >= 1):
        return "%0.2f MiB" % (size / 1048576.0)
    if (size / 1024 >=1):
        return "%0.2f KiB" % (size / 1024.0)
    return "%0.2f B" % (size)

def _format_secs(t):
    h = t / 3600
    t = t % 3600
    m = t / 60
    s = t % 60
    return "%02d:%02d:%02d" % (h, m, s)

def _progress_callback(uploaded, total, piece, time, total_time):
    percent_done = float(uploaded)/float(total)
    percent_done_str = "%02d%%" % (percent_done * 100)
    data_done = _format_size(uploaded)
    elapsed = _format_secs(total_time)

    speed = "- B/sec"
    if (time):
        if (uploaded != total):
            speed = _format_size(float(piece)/float(time)) + "/sec"
        else:
            speed = _format_size(float(total)/float(total_time)) + "/sec"

    # write formated string and flush
    sys.stdout.write("[% -36s] % 4s % 8s % 10s % 14s\r" % ('='*(int(percent_done*36)), percent_done_str, elapsed, data_done, speed))
    sys.stdout.flush()

def build(args):
    # We may not actually nave an srpm arg if we come directly from the build task
    if hasattr(args, 'srpm') and args.srpm and not args.scratch:
        log.error('Non-scratch builds cannot be from srpms.')
        sys.exit(1)
    # Place holder for if we build with an uploaded srpm or not
    url = None
    # See if this is a chain or not
    chain = None
    if hasattr(args, 'chain'):
        chain = args.chain
    if not args.user:
        # Doing a try doesn't really work since the fedora_cert library just
        # exits on error, but if that gets fixed this will work better.
        try:
            args.user = fedora_cert.read_user_cert()
        except:
            log.debug('Could not read Fedora cert, using login name')
            args.user = os.getlogin()
    # Need to do something with BUILD_FLAGS or KOJI_FLAGS here for compat
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
    except pyfedpkg.FedpkgError, e:
        # This error needs a better print out
        log.error('Could not use module: %s' % e)
        sys.exit(1)
    kojiconfig = _get_secondary_config(mymodule)
    try:
        mymodule.init_koji(args.user, kojiconfig)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not log into koji: %s' % e)
        sys.exit(1)
    # handle uploading the srpm if we got one
    if hasattr(args, 'srpm') and args.srpm:
        # Figure out if we want a verbose output or not
        callback = None
        if not args.q:
            callback = _progress_callback
        # define a unique path for this upload.  Stolen from /usr/bin/koji
        uniquepath = 'cli-build/%r.%s' % (time.time(),
                                         ''.join([random.choice(string.ascii_letters)
                                                 for i in range(8)]))
        # Should have a try here, not sure what errors we'll get yet though
        mymodule.koji_upload(args.srpm, uniquepath, callback=callback)
        if not args.q:
            # print an extra blank line due to callback oddity
            print('')
        url = '%s/%s' % (uniquepath, os.path.basename(args.srpm))
    # Should also try this, again not sure what errors to catch
    task_id = mymodule.build(args.skip_tag, args.scratch, args.background,
                             url, chain)
    # Now that we have the task ID we need to deal with it.
    if args.nowait:
        # Log out of the koji session
        mymodule.kojisession.logout()
        return
    # pass info off to our koji task watcher
    return _watch_koji_tasks(mymodule.kojisession, [task_id], quiet=args.q)

def chainbuild(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not use module %s' % e)
        sys.exit(1)
    # make sure we don't try to chain ourself
    if mymodule.module in args.package:
        log.error('%s must not be in the chain' % mymodule.module)
        sys.exit(1)
    # Break the chain up into sections
    urls = []
    build_set = []
    log.debug('Processing chain %s' % ' '.join(args.package))
    for component in args.package:
        if component == ':':
            if build_set:
                # We've hit the end of a set, add the set as a unit to the
                # url list and reset the build_set.
                urls.append(build_set)
                log.debug('Created a build set: %s' % ' '.join(build_set))
                build_set = []
        else:
            # Figure out the scm url to build from package name
            try:
                hash = pyfedpkg.get_latest_commit(component)
                url = pyfedpkg.ANONGITURL % {'module':
                                             component} + '#%s' % hash
                build_set.append(url)
            except pyfedpkg.FedpkgError, e:
                log.error('Could not get a build url for %s: %s'
                          % (component, e))
                sys.exit(1)
    # Take care of the last build set if we have one
    if build_set:
        log.debug('Created a build set: %s' % ' '.join(build_set))
        urls.append(build_set)
    # pass it off to build
    args.chain = urls
    args.skip_tag = False
    args.scratch = False
    build(args)

def check(args):
    # not implimented; Not planned
    log.warning('Not implimented yet, got %s' % args)

def clean(args):
    dry = False
    useignore = True
    if args.dry_run:
        dry = True
    if args.x:
        useignore = False
    try:
        return pyfedpkg.clean(dry, useignore)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not clean: %s' % e)
        sys.exit(1)

def clog(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        return mymodule.clog()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not generate clog: %s' % e)
        sys.exit(1)

def clone(args):
    if not args.user:
        # Doing a try doesn't really work since the fedora_cert library just
        # exits on error, but if that gets fixed this will work better.
        try:
            args.user = fedora_cert.read_user_cert()
        except:
            log.debug('Could not read Fedora cert, using login name')
            args.user = os.getlogin()
    if args.branches:
        pyfedpkg.clone_with_dirs(args.module[0], args.user)
    else:
        pyfedpkg.clone(args.module[0], args.user, args.path, args.branch)

def commit(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        mymodule.commit(args.message, args.file, args.files)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not commit: %s' % e)
        sys.exit(1)
    if args.push:
        # do the push command here.
        pass

def compile(args):
    arch = None
    short = False
    if args.arch:
        arch = args.arch
    if args.short_circuit:
        short = True
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        return mymodule.compile(arch=arch, short=short)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not compile: %s' % e)
        sys.exit(1)

def export(args):
    # not implimented; not planned
    log.warning('Not implimented yet, got %s' % args)

def gimmespec(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        print(mymodule.spec)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get spec file: %s' % e)
        sys.exit(1)

def import_srpm(args):
    # See if we need to create a module from scratch, and do so
    if args.create:
        log.warning('Not implimented yet.')
        sys.exit(0)
    if not args.create:
        try:
            mymodule = pyfedpkg.PackageModule(args.path)
            uploadfiles = pyfedpkg.import_srpm(mymodule.repo, args.srpm)
        except pyfedpkg.FedpkgError, e:
            log.error('Could import srpm: %s' % e)
            sys.exit(1)
        # replace this system call with a proper diff target when it is
        # readys
        os.system('GIT_PAGER='' git diff --cached')
        print('--------------------------------------------')
        print("New content staged and new sources uploaded.")
        print("Commit if happy or revert with: git reset --hard HEAD")
    return

def install(args):
    arch = None
    short = False
    if args.arch:
        arch = args.arch
    if args.short_circuit:
        short = True
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        return mymodule.install(arch=arch, short=short)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not install: %s' % e)
        sys.exit(1)

def lint(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        return mymodule.lint()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not run rpmlint: %s' % e)
        sys.exit(1)

def local(args):
    arch = None
    if args.arch:
        arch = args.arch
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        if args.md5:
            return mymodule.local(arch=arch, hashtype='md5')
        else:
            return mymodule.local(arch=arch)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not build locally: %s' % e)
        sys.exit(1)

def mockbuild(args):
    # Pick up any mockargs from the env
    mockargs = []
    try:
        mockargs = os.environ['MOCKARGS'].split()
    except KeyError:
        # there were no args
        pass
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        return mymodule.mockbuild(mockargs)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not run mockbuild: %s' % e)
        sys.exit(1)

def new(args):
    try:
        print(pyfedpkg.new(args.path))
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get new changes: %s' % e)
        sys.exit(1)

def new_sources(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        mymodule.new_sources(args.files)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not upload new sources: %s' % e)
        sys.exit(1)

def patch(args):
    # not implimented
    log.warning('Not implimented yet, got %s' % args)

def prep(args):
    arch = None
    if args.arch:
        arch = args.arch
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        return mymodule.prep(arch=arch)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not prep: %s' % e)
        sys.exit(1)

def scratchbuild(args):
    # A scratch build is just a build with --scratch
    args.scratch = True
    args.skip_tag = False
    build(args)

def sources(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        mymodule.sources(args.outdir)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not download sources: %s' % e)
        sys.exit(1)

def srpm(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        mymodule.sources(args.path)
        if args.md5:
            mymodule.srpm('md5')
        else:
            mymodule.srpm()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not make an srpm: %s' % e)
        sys.exit(1)

def tagrequest(args):
    # not implimented
    log.warning('Not implimented yet, got %s' % args)

def unusedfedpatches(args):
    # not implimented; not planned
    log.warning('Not implimented yet, got %s' % args)

def unusedpatches(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
        unused = mymodule.unused_patches()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get unused patches: %s' % e)
        sys.exit(1)
    print('\n'.join(unused))

def update(args):
    # not implimented
    log.warning('Not implimented yet, got %s' % args)

def verrel(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get ver-rel: %s' % e)
        sys.exit(1)
    print('%s-%s-%s' % (mymodule.module, mymodule.ver, mymodule.rel))

# THe main code goes here
if __name__ == '__main__':
    # Create the parser object
    parser = argparse.ArgumentParser(description = 'Fedora Packaging utility')

    # Add top level arguments
    # Let somebody override the username found in fedora cert
    parser.add_argument('-u', '--user')
    # Let the user define which path to look at instead of pwd
    parser.add_argument('--path', default = os.getcwd(),
                    help='Directory to interact with instead of current dir')
    # Verbosity
    parser.add_argument('-v', action = 'store_true',
                        help = 'Run with verbose debug output')
    parser.add_argument('-q', action = 'store_true',
                        help = 'Run quietly only displaying errors')

    # Add a subparsers object to use for the actions
    subparsers = parser.add_subparsers(title = 'Targets')

    # Set up the various actions
    # Add help to -h and --help
    parser_help = subparsers.add_parser('help', help = 'Show usage')
    parser_help.set_defaults(command = usage)

    # Add a common build parser to be used as a parent
    parser_build_common = subparsers.add_parser('build_common',
                                                add_help = False)
    parser_build_common.add_argument('--nowait', action = 'store_true',
                                     default = False,
                                     help = "Don't wait on build")
    parser_build_common.add_argument('--background', action = 'store_true',
                                     default = False,
                                     help = 'Run the build at a lower priority')

    # build target
    parser_build = subparsers.add_parser('build',
                                         help = 'Request build',
                                         parents = [parser_build_common])
    parser_build.add_argument('--skip-tag', action = 'store_true',
                              default = False,
                              help = 'Do not attempt to tag package')
    parser_build.add_argument('--scratch', action = 'store_true',
                              default = False,
                              help = 'Perform a scratch build')
    parser_build.set_defaults(command = build)

    # chain build
    parser_chainbuild = subparsers.add_parser('chain-build',
                help = 'Build current package in order with other packages',
                parents = [parser_build_common])
    parser_chainbuild.add_argument('package', nargs = '+',
                                   help = """
Build current package in order with other packages
example: fedpkg chain-build libwidget libgizmo
The current package is added to the end of the CHAIN list.
Colons (:) can be used in the CHAIN parameter to define groups of packages.
Packages in any single group will be built in parallel and all packages in
a group must build successfully and populate the repository before the next
group will begin building.  For example:
fedpkg chain-build libwidget libaselib : libgizmo :
will cause libwidget and libaselib to be built in parallel, followed by
libgizmo and then the currect directory package. If no groups are defined,
packages will be built sequentially.
""")
    parser_chainbuild.set_defaults(command = chainbuild)

    # check preps; not planned
    #parser_check = subparsers.add_parser('check',
    #                            help = 'Check test srpm preps on all arches')
    #parser_check.set_defaults(command = check)

    # clean things up
    parser_clean = subparsers.add_parser('clean',
                                         help = 'Remove untracked files')
    parser_clean.add_argument('--dry-run', '-n', action = 'store_true',
                              help = 'Perform a dry-run')
    parser_clean.add_argument('-x', action = 'store_true',
                              help = 'Do not follow .gitignore rules')
    parser_clean.set_defaults(command = clean)

    # Create a changelog stub
    parser_clog = subparsers.add_parser('clog',
                    help = 'Make a clog file containing top changelog entry')
    parser_clog.set_defaults(command = clog)

    # clone take some options, and then passes the rest on to git
    parser_clone = subparsers.add_parser('clone',
                                         help = 'Clone and checkout a module')
    # Allow an old style clone with subdirs for branches
    parser_clone.add_argument('--branches', '-B',
                action = 'store_true',
                help = 'Do an old style checkout with subdirs for branches')
    # provide a convenient way to get to a specific branch
    parser_clone.add_argument('--branch', '-b',
                              help = 'Check out a specific branch')
    # store the module to be cloned
    parser_clone.add_argument('module', nargs = 1,
                              help = 'Name of the module to clone')
    parser_clone.set_defaults(command = clone)

    # commit stuff
    parser_commit = subparsers.add_parser('commit',
                                          help = 'Commit changes')
    parser_commit.add_argument('-m', '--message',
                               default = None,
                               help = 'Use the given <msg> as the commit message.')
    parser_commit.add_argument('-F', '--file',
                               default = None,
                               help = 'Take the commit message from the given file.')
    # allow one to commit /and/ push at the same time.
    parser_commit.add_argument('-p', '--push',
                               default = False,
                               action = 'store_true',
                               help = 'Commit and push as one action')
    # Allow a list of files to be committed instead of everything
    parser_commit.add_argument('files', nargs = '*',
                               default = [],
                               help = 'Optional list of specific files to commit')
    parser_commit.set_defaults(command = commit)

    # compile locally
    parser_compile = subparsers.add_parser('compile',
                                        help = 'Local test rpmbuild compile')
    parser_compile.add_argument('--arch', help = 'Arch to compile for')
    parser_compile.add_argument('--short-circuit', action = 'store_true',
                                help = 'short-circuit compile')
    parser_compile.set_defaults(command = compile)

    # export the module; not planned
    #parser_export = subparsers.add_parser('export',
    #                                      help = 'Create a clean export')
    #parser_export.set_defaults(command = export)

    # gimmespec takes an optional path argument, defaults to cwd
    parser_gimmespec = subparsers.add_parser('gimmespec',
                                             help = 'print spec file name')
    parser_gimmespec.set_defaults(command = gimmespec)

    # Import content into a module
    parser_import_srpm = subparsers.add_parser('import',
                                          help = 'Import content into a module')
    parser_import_srpm.add_argument('--branch', '-b',
                                    help = 'Branch to import onto',
                                    default = 'devel')
    parser_import_srpm.add_argument('--create', '-c',
                                    help = 'Create a new local repo',
                                    action = 'store_true')
    parser_import_srpm.add_argument('srpm',
                                    help = 'Source rpm to import')
    parser_import_srpm.set_defaults(command = import_srpm)

    # install locally
    parser_install = subparsers.add_parser('install',
                                        help = 'Local test rpmbuild install')
    parser_install.add_argument('--arch', help = 'Arch to install for')
    parser_install.add_argument('--short-circuit', action = 'store_true',
                                help = 'short-circuit install')
    parser_install.set_defaults(command = install)

    # rpmlint target
    parser_lint = subparsers.add_parser('lint',
                            help = 'Run rpmlint against local build output')
    parser_lint.set_defaults(command = lint)

    # Build locally
    parser_local = subparsers.add_parser('local',
                                         help = 'Local test rpmbuild binary')
    parser_local.add_argument('--arch', help = 'Build for arch')
    # optionally define old style hashsums
    parser_local.add_argument('--md5', action = 'store_true',
                              help = 'Use md5 checksums (for older rpm hosts)')
    parser_local.set_defaults(command = local)

    # Build in mock
    parser_mockbuild = subparsers.add_parser('mockbuild',
                                        help = 'Local test build using mock')
    parser_mockbuild.set_defaults(command = mockbuild)

    # See what's different
    parser_new = subparsers.add_parser('new',
                                       help = 'Diff against last tag')
    parser_new.set_defaults(command = new)

    # newsources target takes one or more files as input
    parser_newsources = subparsers.add_parser('new-sources',
                                              help = 'Upload new source files')
    parser_newsources.add_argument('files', nargs = '+')
    parser_newsources.set_defaults(command = new_sources)

    # patch
    parser_patch = subparsers.add_parser('patch',
                                help = 'Create and add a gendiff patch file')
    parser_patch.add_argument('--suffix')
    parser_patch.add_argument('--rediff', action = 'store_true',
                            help = 'Recreate gendiff file retaining comments')
    parser_patch.set_defaults(command = patch)

    # Prep locally
    parser_prep = subparsers.add_parser('prep',
                                        help = 'Local test rpmbuild prep')
    parser_prep.add_argument('--arch', help = 'Prep for a specific arch')
    parser_prep.set_defaults(command = prep)

    # scratch build
    parser_scratchbuild = subparsers.add_parser('scratch-build',
                                                help = 'Request scratch build',
                                                parents = [parser_build_common])
    parser_scratchbuild.add_argument('--arches', nargs = '*',
                                     help = 'Build for specific arches')
    parser_scratchbuild.add_argument('--srpm', help='Build from srpm')
    parser_scratchbuild.set_defaults(command = scratchbuild)

    # sources downloads all the source files, into an optional output dir
    parser_sources = subparsers.add_parser('sources',
                                           help = 'Download source files')
    parser_sources.add_argument('--outdir',
                default = os.curdir,
                help = 'Directory to download files into (defaults to pwd)')
    parser_sources.set_defaults(command = sources)

    # srpm creates a source rpm from the module content
    parser_srpm = subparsers.add_parser('srpm',
                                        help = 'Create a source rpm')
    # optionally define old style hashsums
    parser_srpm.add_argument('--md5', action = 'store_true',
                             help = 'Use md5 checksums (for older rpm hosts)')
    parser_srpm.set_defaults(command = srpm)

    # Create a releng tag request
    parser_tagrequest = subparsers.add_parser('tag-request',
                            help = 'Submit last build as a releng tag request')
    parser_tagrequest.set_defaults(command = tagrequest)

    # Show unused Fedora patches; not planned
    #parser_unusedfedpatches = subparsers.add_parser('unused-fedora-patches',
    #        help = 'Print Fedora patches not used by Patch and/or ApplyPatch'
    #               ' directives')
    #parser_unusedfedpatches.set_defaults(command = unusedfedpatches)

    # Show unused patches
    parser_unusedpatches = subparsers.add_parser('unused-patches',
            help = 'Print list of patches not referenced by name in specfile')
    parser_unusedpatches.set_defaults(command = unusedpatches)

    # Submit to bodhi for update
    parser_update = subparsers.add_parser('update',
                                    help = 'Submit last build as an update')
    parser_update.set_defaults(command = update)

    # Get version and release
    parser_verrel = subparsers.add_parser('verrel',
                                          help = 'Print the'
                                          ' name-version-release')
    parser_verrel.set_defaults(command = verrel)

    # Parse the args
    args = parser.parse_args()

    # setup the logger
    log = pyfedpkg.log
    if args.v:
        log.setLevel(logging.DEBUG)
    elif args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)
    streamhandler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    streamhandler.setFormatter(formatter)
    log.addHandler(streamhandler)

    # Run the necessary command
    args.command(args)