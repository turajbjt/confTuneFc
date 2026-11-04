Name:           conftune-fc
Version:        1.0.0
Release:        1%{?dist}
Summary:        Fedora, Rocky Linux & CentOS system setup, configuration & performance tuner

License:        GPL-3.0-or-later
URL:            https://github.com/turajbjt/confTuneFc
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       python3 >= 3.9
Requires:       python3-pyqt6
Recommends:     tuned
Recommends:     systemd-udev

%define __os_install_post %{nil}
%define __arch_install_post %{nil}

%description
ConfTune FC is a safety-first system setup, configuration, and performance tuner
built for Fedora Linux, Rocky Linux, CentOS Stream, AlmaLinux, and RHEL.

Features include:
- Hardware and RPM environment intelligence (desktop vs headless server detection)
- Workload-optimized presets: Workstation, Gaming/Proton, Enterprise Server,
  High-Throughput Web, Database, Docker/Podman Container Host, KVM Virtualization,
  and Virtualmin / Webmin Web Hosting
- Safe kernel sysctl parameters management with live runtime application
- DNF package manager accelerator (multi-threaded parallel downloads and fastest mirrors)
- Systemd boot speed analyzer (systemd-analyze blame) and daemon management
- Storage TRIM maintenance and block I/O scheduler tuning
- Red Hat tuned-adm daemon integration, SELinux status, and SSH server security audit
- Automatic pre-tune configuration snapshots and 1-click safe rollback engine
- Dual-mode operation: Modern GNOME 45+ Adwaita GUI and full headless CLI

%prep
%setup -q

%build
# Pure python application, no compilation required

%install
rm -rf %{buildroot}

# Install application files into /usr/share/conftune-fc
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -r conftune %{buildroot}%{_datadir}/%{name}/
cp -r assets %{buildroot}%{_datadir}/%{name}/
install -m 755 main.py %{buildroot}%{_datadir}/%{name}/main.py

# Pre-compile Python bytecode so RPM package owns all .pyc files
/usr/bin/python3 -m compileall -q -f -s %{buildroot} -p / %{buildroot}%{_datadir}/%{name}

# Install CLI wrapper / binaries into /usr/bin
mkdir -p %{buildroot}%{_bindir}
cat << 'EOF' > %{buildroot}%{_bindir}/conftune-fc
#!/bin/bash
if [ "$EUID" -eq 0 ] && [ -n "$DISPLAY" ] && [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM=xcb
fi
exec /usr/bin/python3 %{_datadir}/conftune-fc/main.py "$@"
EOF
chmod 755 %{buildroot}%{_bindir}/conftune-fc

# Convenience symlink: conftune -> conftune-fc
ln -sf conftune-fc %{buildroot}%{_bindir}/conftune

# Install polkit policy for privilege escalation
mkdir -p %{buildroot}%{_datadir}/polkit-1/actions
install -m 644 packaging/io.github.conftune_fc.policy %{buildroot}%{_datadir}/polkit-1/actions/io.github.conftune_fc.policy

# Install desktop entry
mkdir -p %{buildroot}%{_datadir}/applications
install -m 644 conftune.desktop %{buildroot}%{_datadir}/applications/conftune-fc.desktop

# Install application icons
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -m 644 assets/icon.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/conftune-fc.svg

# Install documentation & licenses
mkdir -p %{buildroot}%{_docdir}/%{name}
install -m 644 README.md %{buildroot}%{_docdir}/%{name}/

mkdir -p %{buildroot}%{_licensedir}/%{name}
install -m 644 LICENSE %{buildroot}%{_licensedir}/%{name}/

%pre
# Purge any stale unmanaged runtime __pycache__ from prior installs
rm -rf %{_datadir}/%{name}/conftune/**/__pycache__ %{_datadir}/%{name}/conftune/__pycache__ 2>/dev/null || :

%post
/usr/bin/update-desktop-database &> /dev/null || :
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
if [ -x %{_bindir}/gtk-update-icon-cache ]; then
    %{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%postun
/usr/bin/update-desktop-database &> /dev/null || :
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
if [ -x %{_bindir}/gtk-update-icon-cache ]; then
    %{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%files
%license LICENSE
%doc README.md
%{_bindir}/conftune
%{_bindir}/conftune-fc
%{_datadir}/%{name}
%{_datadir}/applications/conftune-fc.desktop
%{_datadir}/icons/hicolor/scalable/apps/conftune-fc.svg
%{_datadir}/polkit-1/actions/io.github.conftune_fc.policy

%changelog
* Tue Nov 03 2026 James Turansky <turajb@gmail.com> - 1.0.0-1
- Initial release of ConfTune FC for Fedora 44+, Rocky Linux, and CentOS Stream.
