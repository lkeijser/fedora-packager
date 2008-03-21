Name:           fedora-packager
Version:        0.2.0
Release:        1%{?dist}
Summary:        Tools for setting up a fedora maintainer environment

Group:          Applications/Productivity
License:        GPLv2+
URL:            https://fedorahosted.org/fedora-packager
Source0:        https://fedorahosted.org/fedora-packager/attachment/wiki/WikiStart/fedora-packager-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:       koji bodhi-client plague-client
Requires:       rpm-build rpmdevtools rpmlint
Requires:       cvs mercurial git-core bzr
Requires:       gcc gcc-c++ mock

BuildArch:      noarch

%description
Set of utilities useful for a fedora packager in setting up their environment.

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
* Thu Mar 20 2008 Dennis Gilmore <dennis@ausil.us> - 0.2.0-1
- update to 0.2.0  fedora-cvs now allows checking out multiple modules
- new url for fas2
- update links to fedorahosted

* Mon Dec 03 2007 Dennis Gilmore <dennis@ausil.us> - 0.1.1-1
- fix typo in description 
- update to 0.1.1  fixes typo in fedora-cvs

* Sun Nov 11 2007 Dennis Gilmore <dennis@ausil.us> - 0.1-1
- initial build
