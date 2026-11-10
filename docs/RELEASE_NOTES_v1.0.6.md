# ConfTune FC v1.0.6 Release Notes ⚡

**ConfTune FC** is the open-source system optimization, kernel tuning, and automated deployment suite for Fedora Linux, Red Hat Enterprise Linux (RHEL), Rocky Linux, AlmaLinux, and CentOS Stream.

---

## 🚀 Key Improvements in v1.0.6

### 1. Table Cell Button Alignment & Centering
- **Kernel Sysctl Table**:
  - Embedded each row's `"↺ Default"` button in a container `QWidget` with a centered `QHBoxLayout` and symmetric padding.
  - Assigned a dedicated fixed column width (`110px`) for column 5 (`Reset`), perfectly framing the 85px button without horizontal or vertical drift.
  - Standardized table row height to `38px` and hid the vertical index header for a clean, aligned modern look.
- **Boot & Systemd Service Optimizer Table**:
  - Wrapped each recommended service's `"Disable"` / `"Enable"` action toggle button in a centered `QHBoxLayout` cell container within the 195px action column.
  - Set explicit 160×30 button geometry, eliminating off-center top-left pinning in table cells.
  - Added non-editable `QTableWidgetItem` placeholders in column 3 to ensure alternating row colors and selection bounds render smoothly.
- **Login Autostart Applications Table**:
  - Applied the identical cell container layout and horizontal/vertical centering to the Disable / Enable toggle buttons in the login autostart table.

### 2. Stylesheet Table Button Constraint Polish
- **Scoped Min-Width Rules**: Refactored `QTableWidget QPushButton` stylesheet rules in `conftune/gui/styles.py` to prevent global `min-width: 150px` from overflowing compact cell buttons like `btn_row_reset` (`table_btn_reset`).
- Retained full `min-width: 150px` styling for large action buttons (`table_btn_wide`).

---

## 📦 Package Artifacts & Checksums (v1.0.6)

| File | SHA256 Checksum |
| :--- | :--- |
| `conftune-fc-1.0.6-1.noarch.rpm` | `772e28e63619bc8970c1506cacbc263dbe9b20d6e0912c4a5ea930f1b3425bc6` |
| `conftune-fc-1.0.6-1.src.rpm` | `a4ff001645a89b2255f2dc9e350a3fae44977e9a78b062e41efd3b786371528c` |

---

## 📥 Installation & Upgrade Instructions

To upgrade to **v1.0.6** on Fedora, Rocky Linux, CentOS Stream, or RHEL:

```bash
sudo dnf update -y ./conftune-fc-1.0.6-1.noarch.rpm
```
*(or via rpm: `sudo rpm -Uvh ./conftune-fc-1.0.6-1.noarch.rpm`)*
