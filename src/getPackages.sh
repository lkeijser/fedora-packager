#!/bin/sh

# This script came from http://fedoraproject.org/wiki/PackageMaintainers/UsefulScripts 
# initiall contributed by Contributed by Ignacio Vazquez-Abrams, modified to work with pkgdb by ToshioKuratomi


PKGDBURL=${PACKAGEDBURL:-'https://admin.fedoraproject.org/pkgdb'}
PKGDBADDRESS=${PKGDBURL}/acls/bugzilla?tg_format=plain

download=1

while getopts :f:u:o:n opt ; do
  case $opt in
    u)
      user="$OPTARG"
      ;;
    f)
      file="$OPTARG"
      ;;
    o)
      owners="$OPTARG"
      ;;
    n)
      download=0
      ;;
    \?)
      echo "Usage: $(basename $0) [-u <fedora username>] [-f <plague-client config file>] [-o <owners.list>] -n"
      echo "  -o -- must point to a file downloaded from:"
      echo "    $PKGDBADDRESS"
      echo "    This script will automatically download a copy if <owners.list>"
      echo "    does not exist."
      echo "  -n Do not download even if the file is nonexistent"
      exit 255
      ;;
  esac
done

file=${file:-~/.plague-client.cfg}

[ -f "$file" -o -z "$email" ] || { echo "File $file does not exist" ; exit 1 ; }

user=${user:-$(awk 'BEGIN { FS="[ =]+" } $1 == "upload_user" { print $2 }' < "$file")}

owners=${owners:-/var/tmp/owners.list}
if [ ! -e $owners ] ; then
  if [ $download -le 0 ] ; then
    echo "$owners does not exist.  Cannot lookup packages"
    exit 1
  fi
  if [ ! -e `dirname $owners` ] ; then
    mkdir -p `dirname $owners` || exit $?
  fi
  wget $PKGDBADDRESS -O $owners
fi

awk -v user="$user" 'BEGIN { FS="|" } $1 ~ "^Fedora( EPEL| OLPC)?" && $4 == user { printf "%-11ls  %s\n", $1, $2 }' < $owners

