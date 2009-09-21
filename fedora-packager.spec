Name:           fedora-packager
Version:        0.3.8
Release:        1%{?dist}
Summary:        Tools for setting up a fedora maintainer environment

Group:          Applications/Productivity
License:        GPLv2+
URL:            https://fedorahosted.org/fedora-packager
Source0:        https://fedorahosted.org/releases/f/e/fedora-packager/fedora-packager-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:       koji bodhi-client 
Requires:       rpm-build rpmdevtools rpmlint
Requires:       mock cvs curl wget
Requires:       pyOpenSSL python-pycurl
Requires:       redhat-rpm-config
Requires:       python-offtrac

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
%{_bindir}/fedoradev-pkgowners
%{_bindir}/fedora-cert
%{_bindir}/fedora-getsvn
%{_bindir}/fedora-hosted
%{_bindir}/rpmbuild-md5


%changelog
* Tue Aug 04 2009 Jesse Keating <jkeating@redhat.com> - 0.3.8-1
- Add fedora-hosted and require offtrac

* Thu Jul 30 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.7-1
- define user_cert in fedora-cvs before refrencing it 

* Tue Jul 28 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.6-1
- use anon checkout when a fedora cert doesnt exist bz#514108
- quote arguments passed onto rpmbuild bz#513269

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Mon Jul 13 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.5-1
- add new rpmbuild-md5 script to build old style hash srpms
- it is a wrapper around rpmbuild

* Mon Jul  6 2009 Tom "spot" Callaway <tcallawa@redhat.com> - 0.3.4-3
- add Requires: redhat-rpm-config to be sure fedora packagers are using all available macros

* Wed Jun 24 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.4-2
- minor bump

* Mon Jun 22 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.4-1
- update to 0.3.4 
- bugfix release with some new scripts

* Mon Mar 02 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.3-1
- update to 0.3.3

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

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
