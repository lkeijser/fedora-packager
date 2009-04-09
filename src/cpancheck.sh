#!/bin/sh

set -e

wget="wget -q"
cvs="cvs -q -z1"

me=""
rpms=~/code/fedora

OWNERS=${OWNERS:-https://admin.fedoraproject.org/pkgdb/acls/bugzilla?tg_format=plain}
CPAN=${CPAN:-"http://www.cpan.org"}
packages=$HOME/.cpan/sources/modules/02packages.details.txt.gz

tmpdir=$( mktemp -d /tmp/cpancheck.XXXXXX )
trap cleanup EXIT
cleanup()
{
    set +e
    [ -z "$tmpdir" -o ! -d "$tmpdir" ] || rm -rf "$tmpdir"
}
owners=$tmpdir/owners.list

mkdir -p $( dirna~/code/fedorame $packages )
echo "Updating CPAN package details..."
$wget -N -O $packages $CPAN/modules/$( basename $packages )

echo "Retrieving package owners list..."
$wget -N -O $owners $OWNERS

for package in $( grep "\\b$me\\b" $owners | cut -d'|' -f2 | grep '^perl-' ) ; do
    echo "Updating $package..."
    ( cd $rpms && $cvs up $package )

    echo "Checking $package..."

    if [ ! -d $rpms/$package/devel ] ; then
        echo " - No devel/, skipping..."
        continue
    fi

    module=$( echo $package | sed 's,^perl-,,;s/-/::/g' )
    cpanversion=$( zgrep '^'$module' ' $packages | awk '{print $2}' )
    pkgversion=$( grep '^Version:' $rpms/$package/devel/$package.spec \
                    | awk '{print $2}' )

    if [ $cpanversion != $pkgversion ] ; then
        echo " *** MISMATCH: devel is $pkgversion, CPAN is $cpanversion." >&2
    else
        echo "$package is up-to-date!"
    fi
done

# vi: set ai et:
