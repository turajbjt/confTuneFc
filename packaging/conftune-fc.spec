Name:           conftune-fc
Version:        1.0.2
Release:        1
Summary:        Fedora, Rocky Linux & CentOS system setup, configuration & performance tuner

License:        GPL-3.0-or-later
URL:            https://github.com/turajbjt/confTuneFc
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

# Universal RPM requires: avoid distro-specific python ABI pins (e.g. python(abi) = 3.14)
# by relying on standard portable python3 >= 3.9 and python3-pyqt6
AutoReqProv:    no

Requires:       /bin/sh
Requires:       python3 >= 3.9
Requires:       python3-pyqt6
Recommends:     tuned
Recommends:     systemd-udev

%define dist %{nil}
%define __os_install_post %{nil}
%define __arch_install_post %{nil}
%define __check_files %{nil}
%define _unpackaged_files_terminate_build 0

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

# Universal package: DO NOT pre-compile bytecode at build time.
# Bytecode is compiled during %post on target system to match installed Python runtime.

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

# Install AppStream metainfo
mkdir -p %{buildroot}%{_datadir}/metainfo
install -m 644 assets/io.github.conftune_fc.metainfo.xml %{buildroot}%{_datadir}/metainfo/io.github.conftune_fc.metainfo.xml

# Install systemd service unit
mkdir -p %{buildroot}%{_prefix}/lib/systemd/system
install -m 644 packaging/systemd/conftune-powerd.service %{buildroot}%{_prefix}/lib/systemd/system/conftune-powerd.service

# Install desktop entry
mkdir -p %{buildroot}%{_datadir}/applications
install -m 644 conftune.desktop %{buildroot}%{_datadir}/applications/conftune-fc.desktop

# Install application scalable icon
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -m 644 assets/icon.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/conftune-fc.svg

# Install standard raster icon sizes (16x16 to 512x512)
for size in 16 24 32 48 64 128 256 512; do
    if [ -f "assets/icons/${size}x${size}/conftune-fc.png" ]; then
        mkdir -p "%{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps"
        install -m 644 "assets/icons/${size}x${size}/conftune-fc.png" "%{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/conftune-fc.png"
    fi
done

# Install documentation & licenses
mkdir -p %{buildroot}%{_docdir}/%{name}
install -m 644 README.md %{buildroot}%{_docdir}/%{name}/
install -m 644 CONTRIBUTING.md %{buildroot}%{_docdir}/%{name}/
cp -r docs %{buildroot}%{_docdir}/%{name}/

mkdir -p %{buildroot}%{_licensedir}/%{name}
install -m 644 LICENSE %{buildroot}%{_licensedir}/%{name}/

%post
/usr/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
/usr/bin/update-desktop-database &>/dev/null || :
/usr/bin/python3 -m compileall -q %{_datadir}/%{name} &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    find %{_datadir}/%{name} -name "*.pyc" -delete 2>/dev/null || :
    find %{_datadir}/%{name} -depth -type d -name "__pycache__" -delete 2>/dev/null || :
    /usr/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
    /usr/bin/update-desktop-database &>/dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%files
%license LICENSE
%doc README.md CONTRIBUTING.md docs
%{_bindir}/conftune
%{_bindir}/conftune-fc
%{_datadir}/%{name}
%{_datadir}/applications/conftune-fc.desktop
%{_datadir}/icons/hicolor/scalable/apps/conftune-fc.svg
%{_datadir}/icons/hicolor/*/apps/conftune-fc.png
%{_datadir}/polkit-1/actions/io.github.conftune_fc.policy
%{_datadir}/metainfo/io.github.conftune_fc.metainfo.xml
%{_prefix}/lib/systemd/system/conftune-powerd.service

%changelog
* Thu Nov 05 2026 James Turansky <turajb@gmail.com> - 1.0.2-1
- Fix PolicyKit privilege escalation with proven confclean-fc asynchronous handshake
- Fix Wayland/XWayland display authorization with xhost localroot and QT_QPA_PLATFORM=xcb
- Fix microscopic action button sizing and text truncation in Boot & Systemd tab
- Add AppStream releases metadata and update versioning pipeline

* Wed Nov 04 2026 James Turansky <turajb@gmail.com> - 1.0.0-1
- Initial universal release of ConfTune FC for Fedora, Rocky Linux, AlmaLinux, CentOS Stream, and RHEL
- Pure Python source package with noarch architecture and on-target bytecode compilation
- Full standard hicolor raster icons hierarchy (16x16 to 512x512) and scalable SVG
- Desktop integration with StartupWMClass and Wayland app_id desktopFileName mapping
- Polkit authentication actions for unprivileged desktop users
