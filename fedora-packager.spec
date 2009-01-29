Name:           fedora-packager
Version:        0.3.1
Release:        1%{?dist}
Summary:        Tools for setting up a fedora maintainer environment

Group:          Applications/Productivity
License:        GPLv2+
URL:            https://fedorahosted.org/fedora-packager
Source0:        https://fedorahosted.org/fedora-packager/attachment/wiki/WikiStart/fedora-packager-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:       koji bodhi-client plague-client
Requires:       rpm-build rpmdevtools rpmlint
Requires:       mock pyOpenSSL curl wget cvs

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
%{_bindir}/fedora-packager-setup
%{_bindir}/fedora-cvs



%changelog
* Mon Aug 18 2008 Dennis Gilmore <dennis@ausil.us> - 0.3.1-1
- update to 0.3.1 fedora-cvs allows anonymous checkout
- fix some Requires  add cvs curl and wget

* Sun Mar 30 2008 Dennis Gilmore <dennis@ausil.us> - 0.3.0-1
- update to 0.3.0 fedora-cvs uses pyOpenSSL to work out username
- remove Requires on RCS's for fedora-hosted
- rename fedora-packager-setup.sh to fedora-packager-setup

* Fri Feb 22 2008 Dennis Gilmore <dennis@ausil.us> - 0.2.0-1
- new upstream release
- update for fas2
- fedora-cvs  can now check out multiple modules at once
- only require git-core

* Mon Dec 03 2007 Dennis Gilmore <dennis@ausil.us> - 0.1.1-1
- fix typo in description
- update to 0.1.1  fixes typo in fedora-cvs

* Sun Nov 11 2007 Dennis Gilmore <dennis@ausil.us> - 0.1-1
- initial build
