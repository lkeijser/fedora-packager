#!/usr/bin/python
# fedora-hosted - a commandline frontend for the Fedora Hosted Projects Trac
#
# Copyright (C) 2008 Red Hat Inc.
# Author: Jesse Keating <jkeating@redhat.com>
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

# TODO: this file should probably go away and be far more generic
# And we should load specific things like url structure from a config
# store of some sort.

import getpass
import optparse
import offtrac
import sys
import time

# Define some constants
BASEURL = 'fedorahosted.org/'

# List currently available commands
cmdlist = ('list-tickets', 'list-milestones', 'ticket-info', 'milestone-info',
           'new-ticket', 'new-milestone', 'update-ticket')

# Define some functions
def setup_action_parser(action):
    """Setup parsers for the various action types"""

    usage = "usage: %%prog %s [options]" % action
    p = optparse.OptionParser(usage = usage)

    if action == "list-tickets":
        p.add_option("--owner", "-o")
        p.add_option("--status", "-s", default="!=closed",
                     help="Query string for status, default is '!=closed'")
        p.add_option("--component", "-c")
        p.add_option("--type", "-t")

#    elif action == "list-milestones":
#        p.add_option("--name", "-n", 
#                     help="Show information about a particular milestone")
#        p.add_option("--all", "-a", action="store_true",
#                     help="Show all milestones, otherwise only show active.")

    elif action == "ticket-info":
        p.set_usage("usage: %%prog %s [ticket numbers]" % action)

    elif action == "milestone_info":
        p.set_usage("usage: %%prog %s [milestones]" % action)

    elif action == "new-ticket":
        p.add_option("--summary", "-s", help="REQUIRED!")
        p.add_option("--description", "-d", help="REQUIRED!")
        p.add_option("--type", "-t", default=None)
        p.add_option("--priority", "-p", default=None)
        p.add_option("--milestone", "-m", default=None)
        p.add_option("--component", "-C", default=None)
        p.add_option("--version", "-v", default=None)
        p.add_option("--keyword", "-k", action="append",
                     help="Keyword to add, can be used multiple times.")
        p.add_option("--assignee", "-a", default=None)
        p.add_option("--cc", action="append",
                     help="Carbon Copy address, can be used multiple times.")
        # This one is a little backwards.  The rpc call is actually notify,
        # and defaults to false, but we want to default to true.
        p.add_option("--stealth", action="store_false", default=True,
                     help="Suppress initial notification of this ticket.")

    elif action == "update-ticket":
        p.add_option("--ticket", "-n", help="Ticket number.  REQUIRED!")
        p.add_option("--comment", "-c", default='')
        p.add_option("--summary", "-s", default=None)
        p.add_option("--description", "-d", default=None)
        p.add_option("--type", "-t", default=None)
        p.add_option("--priority", "-p", default=None)
        p.add_option("--milestone", "-m", default=None)
        p.add_option("--component", "-C", default=None)
        p.add_option("--version", "-v", default=None)
        p.add_option("--keyword", "-k", action="append",
                     help="Keyword to add, can be used multiple times.")
        p.add_option("--assignee", "-a", default=None)
        p.add_option("--cc", action="append",
                     help="Carbon Copy address, can be used multiple times.")
        p.add_option("--status", "-S", default=None)
        p.add_option("--resolution", "-r", default=None)
        # This one is a little backwards.  The rpc call is actually notify,
        # and defaults to false, but we want to default to true.
        p.add_option("--stealth", action="store_false", default=True,
                     help="Suppress notification of this update.")

    elif action == "new-milestone":
        p.add_option("--name", "-n", help="REQUIRED!")
        p.add_option("--description", "-d", default=None)
        p.add_option("--due", "-D", default=None,
                     help="Due date in MM-DD-YY format.")

    return p


# get command line options
usage = "usage: %prog [global options] COMMAND [options]"
usage += "\nCommands: %s" % ', '.join(cmdlist)
parser = optparse.OptionParser(usage=usage)
parser.disable_interspersed_args()

# TODO: Try to get this info from fedora config files
parser.add_option("--user", "-u")
parser.add_option("--password", "-p")
parser.add_option("--project", "-P")

# Parse our global options
(opts, args) = parser.parse_args()

# See if we got a command
if len(args) and args[0] in cmdlist:
    action = args.pop(0)
else:
    parser.print_help()
    sys.exit(1)

# Parse the command
action_parser = setup_action_parser(action)
(actopt, actargs) = action_parser.parse_args(args)

if not opts.user:
    opts.user=raw_input('Username: ')

if not opts.password:
    opts.password=getpass.getpass('Password for %s: ' % opts.user)

if not opts.project:
    opts.project=raw_input('Project space: ')


# Create the TracServ object
uri = 'https://%s:%s@%s/%s/login/xmlrpc' % (opts.user,
                                            opts.password,
                                            BASEURL,
                                            opts.project)
trac = offtrac.TracServer(uri)

# Try to do something
if action == "list-tickets":
    # setup the query string
    query = "status%s" % actopt.status
    if actopt.owner:
        query += "&owner=%s" % actopt.owner
    if actopt.component:
        query += "&component=%s" % actopt.component
    if actopt.type:
        query += "&type=%s" % actopt.type

    results = trac.query_tickets(query)
    print results

elif action == "list-milestones":
    results = trac.list_milestones()
    print results

elif action == "ticket-info":
    if not actargs: # FIXME, this isn't working
        action_parser.print_help()
        sys.exit(1)
    # Setup the trac object for multicall
    trac.setup_multicall()
    for number in actargs:
        trac.get_ticket(number)
    # Do the multicall and print out the results
    for result in trac.do_multicall():
        print result

elif action == "milestone-info":
    if not actargs: # FIXME, this isn't working
        action_parser.print_help()
        sys.exit(1)
    trac.setup_multicall()
    for milestone in actargs:
        trac.get_milestone(milestone)
    for result in trac.do_multicall():
        print result

elif action == "new-ticket":
    # Check to make sure we got all we need
    if actopt.summary and actopt.description:
        pass
    else:
        action_parser.print_help()
        sys.exit(1)
    # Wrap up our keywords and cc into one string, if any
    keywords = None
    ccs = None
    if actopt.keyword:
        keywords = ' '.join(actopt.keyword)
    if actopt.cc:
        ccs = ' '.join(actopt.cc)

    result = trac.create_ticket(actopt.summary, actopt.description,
                              actopt.type, actopt.priority, actopt.milestone,
                              actopt.component, actopt.version, keywords,
                              actopt.assignee, ccs, actopt.stealth)
    print result

elif action == "update-ticket":
    # Check to make sure we got all we need
    if actopt.ticket:
        pass
    else:
        action_parser.print_help()
        sys.exit(1)
    # Wrap up our keywords and cc into one string, if any
    keywords = None
    ccs = None
    if actopt.keyword:
        keywords = ' '.join(actopt.keyword)
    if actopt.cc:
        ccs = ' '.join(actopt.cc)

    result = trac.update_ticket(actopt.ticket, actopt.comment, actopt.summary,
                                actopt.type, actopt.description,
                                actopt.priority, actopt.milestone,
                                actopt.component, actopt.version, keywords,
                                ccs, actopt.status, actopt.resolution,
                                actopt.assignee, actopt.stealth)
    print result

elif action == "new-milestone":
    if not actopt.name:
        action_parser.print_help()
        sys.exit(1)
    # Convert due date to seconds if needed
    due = None
    if actopt.due:
        due = int(time.mktime(time.strptime(actopt.due, "%m-%d-%y")))

    result = trac.create_milestone(actopt.name, actopt.description, due)
    print result # The result here is "0" if successful, printing isn't fun

