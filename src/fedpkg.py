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
import fedpkg
import os

# Add a simple function to print usage, for the 'help' command
def usage(args):
    parser.print_help()

# Define our stub functions
def build(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def chainbuild(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def check(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def clean(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def clog(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def clone(args):
    if not args.user:
        # Use a method to scrape user from fedora cert here
        args.user = os.getlogin()
    if args.branches:
        fedpkg.clone_with_dirs(args.module, args.user)
    else:
        fedpkg.clone(args.module, args.user, args.branch)

def compile(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def export(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def gimmespec(args):
    try:
        mymodule = fedpkg.PackageModule(args.path)
        print(mymodule.spec)
    except fedpkg.FedpkgError, e:
        print('Could not get spec file: %s' % e)
        return 1

def install(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def lint(args):
    try:
        mymodule = fedpkg.PackageModule(args.path)
        print(mymodule.lint())
    except fedpkg.FedpkgError, e:
        print('Could not run rpmlint: %s' % e)
        return 1

def local(args):
    arch = None
    if args.arch:
        arch = args.arch
    try:
        mymodule = fedpkg.PackageModule(args.path)
        print(mymodule.local(arch=arch))
    except fedpkg.FedpkgError, e:
        print('Could not build locally: %s' % e)
        return 1

def mockbuild(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def new(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def new_sources(args):
    mymodule = fedpkg.PackageModule(args.path)
    mymodule.new_sources(args.files)

def patch(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def prep(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def scratchbuild(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def sources(args):
    try:
        mymodule = fedpkg.PackageModule(args.path)
        mymodule.sources(args.outdir)
    except fedpkg.FedpkgError, e:
        print('Could not download sources: %s' % e)
        return 1

def srpm(args):
    try:
        mymodule = fedpkg.PackageModule(args.path)
        mymodule.sources(args.path)
        if args.md5:
            mymodule.srpm('md5')
        else:
            mymodule.srpm()
    except fedpkg.FedpkgError, e:
        print('Could not make an srpm: %s' % e)
        return 1

def tagrequest(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def unusedfedpatches(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def unusedpatches(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def update(args):
    # not implimented
    print('Not implimented yet, got %s' % args)

def verrel(args):
    mymodule = fedpkg.PackageModule(args.path)
    print('%s-%s-%s' % (mymodule.module, mymodule.ver, mymodule.rel))

# THe main code goes here
if __name__ == '__main__':
    # Create the parser object
    parser = argparse.ArgumentParser(description = 'Fedora Packaging utility')

    # Add top level arguments
    # Let somebody override the username found in fedora cert
    parser.add_argument('-u', '--user')
    # Let the user define which path to look at instead of pwd
    parser.add_argument('--path', default = os.curdir,
                    help='Directory to interact with instead of current dir')
    # Verbosity
    parser.add_argument('-v', action = 'count',
                        help = 'Verbosity, may be specified multiple times')

    # Add a subparsers object to use for the actions
    subparsers = parser.add_subparsers(title = 'Targets')

    # Set up the various actions
    # Add help to -h and --help
    parser_help = subparsers.add_parser('help', help = 'Show usage')
    parser_help.set_defaults(command = usage)

    # build target
    parser_build = subparsers.add_parser('build',
                                         help = 'Request build')
    parser_build.set_defaults(command = build)

    # chain build
    parser_chainbuild = subparsers.add_parser('chain-build',
                help = 'Build current package in order with other packages')
    parser_chainbuild.set_defaults(command = chainbuild)

    # check preps
    parser_check = subparsers.add_parser('check',
                                help = 'Check test srpm preps on all arches')
    parser_check.set_defaults(command = check)

    # clean things up
    parser_clean = subparsers.add_parser('clean',
                                         help = 'Remove untracked files')
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
    parser_clone.add_argument('--module', '-m', required = True,
                              help = 'Name of the module to clone')
    parser_clone.set_defaults(command = clone)

    # compile locally
    parser_compile = subparsers.add_parser('compile',
                                        help = 'Local test rpmbuild compile')
    parser_compile.add_argument('--short-circuit', action = 'store_true',
                                help = 'short-circuit compile')
    parser_compile.set_defaults(command = compile)

    # export the module
    parser_export = subparsers.add_parser('export',
                                          help = 'Create a clean export')
    parser_export.set_defaults(command = export)

    # gimmespec takes an optional path argument, defaults to cwd
    parser_gimmespec = subparsers.add_parser('gimmespec',
                                             help = 'print spec file name')
    parser_gimmespec.set_defaults(command = gimmespec)

    # install locally
    parser_install = subparsers.add_parser('install',
                                        help = 'Local test rpmbuild install')
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
    parser_prep.set_defaults(command = prep)

    # scratch build
    parser_scratchbuild = subparsers.add_parser('scratch-build',
                                                help = 'Request scratch build')
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

    # Show unused Fedora patches
    parser_unusedfedpatches = subparsers.add_parser('unused-fedora-patches',
            help = 'Print Fedora patches not used by Patch and/or ApplyPatch'
                   ' directives')
    parser_unusedfedpatches.set_defaults(command = unusedfedpatches)

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

    # Parse the args and run the necessary command
    args = parser.parse_args()
    args.command(args)