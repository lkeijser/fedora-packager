Name:           fedora-packager
Version:        0.1
Release:        1%{?dist}
Summary:        Tools for setting up a fedora mainter environment

Group:          Applications/
License:        GPLv2+
URL:            https://hosted.fedoraproject.org/projects/fedora-packager/
Source0:        %{name}-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  
Requires:       koji bodhi-client plague-client
Requires:       rpm-build rpmdevtools 
Requires:       cvs mercurial git bzr
Requires:       

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
%doc



%changelog
* Sun Nov 11 2008 Dennis Gilmore <dennis@ausil.us> - 0.1-1
- initial build
