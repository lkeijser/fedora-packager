Name:           fedora-packager
Version:        0.1
Release:        1%{?dist}
Summary:        Tools for setting up a fedora maintainer environment

Group:          Applications/Productivity
License:        GPLv2+
URL:            https://hosted.fedoraproject.org/projects/fedora-packager/
Source0:        https://hosted.fedoraproject.org/projects/fedora-packager/attachment/wiki/WikiStart/fedora-packager-0.1.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:       koji bodhi-client plague-client
Requires:       rpm-build rpmdevtools rpmlint
Requires:       cvs mercurial git bzr
Requires:       gcc gcc-c++ mock

BuildArch:      noarch

%description
Set of utilities useful for a fedora packager in setting up thier environment.

%prep
%setup -q


%build
%configure
make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc COPYING TODO AUTHORS ChangeLog
%{_bindir}/fedora-packager-setup.sh
%{_bindir}/fedora-cvs



%changelog
* Sun Nov 11 2008 Dennis Gilmore <dennis@ausil.us> - 0.1-1
- initial build
