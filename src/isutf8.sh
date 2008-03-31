#!/bin/sh

# written by Ville Skyttä
# pulled in from http://fedoraproject.org/wiki/PackageMaintainers/UsefulScripts

VERBOSE=

while [ -n "$1" ] ; do
    [ "$1" = "-v" ] && { VERBOSE=1 ; shift ; continue ; }
    [ -f "$1" ] || { [ -n "$VERBOSE" ] && echo "???: $1" ; shift ; continue ; }

    cat="cat"
    case "$1" in 
       *.bz|*.bz2) cat="bzip2 -dcf" ;; 
       *.gz) cat="gzip -dcf" ;;
    esac

    if $cat "$1" | iconv -f utf-8 -t utf-8 >/dev/null 2>&1 ; then
        [ -n "$VERBOSE" ] && echo "yes: $1"
    else
        echo " NO: $1"
    fi

    shift
done
