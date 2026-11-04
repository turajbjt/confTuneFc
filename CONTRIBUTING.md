# Contributing to ConfTune FC 🤝

Thank you for considering contributing to ConfTune FC! We welcome contributions to improve performance tuning, add new workload profiles, enhance safety validations, and expand distribution support.

---

## 🛠️ Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/turajbjt/confTuneFc.git
   cd confTuneFc
   ```

2. **Install development dependencies**:
   ```bash
   # System packages for Fedora / Rocky / CentOS:
   sudo dnf install python3-pyqt6 rpm-build python3-pytest

   # Or via pip:
   pip install PyQt6 pytest
   ```

3. **Verify the test suite**:
   ```bash
   PYTHONPATH=. python3 tests/test_core.py
   ```

---

## 🧪 Testing Guidelines

- All pull requests modifying core modules (`conftune/core/`) must include unit test coverage in `tests/`.
- Ensure tests run cleanly in dry-run mode without modifying host operating system files.
- Test both GUI instantiation and CLI parameter parsing.

---

## 📝 Code Style & Standards

- **Python**: Follow PEP 8 guidelines. Write clean, descriptive variable and function names.
- **Safety First**: Any logic that writes or modifies system files must integrate with `conftune.core.backup_manager.BackupManager` and respect `conftune.core.safety.SafetyEngine.dry_run`.
- **UI Aesthetics**: Maintain GNOME 45+ Adwaita Dark styling standards defined in `conftune/gui/styles.py`.

---

## 🚀 Adding a New Workload Profile

To add a new tuning profile preset:
1. Open `conftune/core/profiles.py`.
2. Add a new dictionary entry to `PROFILES` with:
   - `id`: Unique lowercase identifier
   - `name`: Human-readable name
   - `category`: Category grouping
   - `description`: Detailed explanation
   - `icon`: Unicode emoji icon
   - `tuned_profile`: Red Hat tuned daemon profile name
   - `journald_max`: Systemd journal size cap (e.g. `300M`, `500M`)
   - `sysctl`: Dictionary of key-value sysctl settings
   - `dnf_settings`: Recommended DNF configuration
   - `notes`: Rationale for parameters
3. Add a corresponding test case in `tests/test_core.py`.

---

## 📦 Versioning & Bumping

ConfTune FC follows Semantic Versioning (`MAJOR.MINOR.PATCH`). Use the helper script to bump versions consistently across all project files:

```bash
# Bump patch release (e.g., 1.0.0 -> 1.0.1):
python3 scripts/bump_version.py patch -m "Fix parameter validation"

# Bump minor release (e.g., 1.0.0 -> 1.1.0):
python3 scripts/bump_version.py minor -m "Add new storage scheduler optimizer"

# Bump and build RPM package immediately:
python3 scripts/bump_version.py patch --build-rpm
```
