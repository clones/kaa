Summary: Python wrapper for Evas
Name: kaa-evas
Version: 0.0.1
Release: 1
License: LGPL
Group: System Environment/Libraries

Source: http://sault.org/mebox/downloads/pyevas/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/root-%{name}-%{version}
Prefix: %{_prefix}

BuildRequires: python >= 2.3

%description
Kaa is an umbrella project housing a set of Python modules related to
media.  kaa-evas is small python module partially wrapping Evas. 

Evas is a clean display canvas API for several target display systems
that can draw anti-aliased text, smooth super and sub-sampled scaled
images, alpha-blend objects much and more.

%prep
%setup

%build
python setup.py build

%install
%{__rm} -rf %{buildroot}
python setup.py install --root=%{buildroot} --record=INSTALLED_FILES

cat >>INSTALLED_FILES << EOF
%doc README
EOF

%clean
%{__rm} -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-, root, root, 0755)


%changelog
* Mon May 23 2005 Jason Tackaberry <tack@sault.org> - 0.0.1-1
- Initial package
