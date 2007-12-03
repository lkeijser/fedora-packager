Name:           fedora-packager
Version:        0.1
Release:        1%{?dist}
Summary:        Tools for setting up a fedora mainter environment

Group:          Applications/
License:        GPLv2+
URL:            https://hosted.fedoraproject.org/projects/fedora-packager/
Source0:        %{name}-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:       koji bodhi-client plague-client
Requires:       rpm-build rpmdevtools rpmlint
Requires:       cvs mercurial git bzr
Requires:       gcc gcc-c++ mock

%description
Set of utilities useful for a fedora packager in setting up thier environment.

%prep
%setup -q


%build


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_bindir}
make install DESTDIR=$RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc
%{_bindir}/fedora-packager-setup.sh
%{_bindir}/fedora-cvs



%changelog
* Sun Nov 11 2008 Dennis Gilmore <dennis@ausil.us> - 0.1-1
- initial build
