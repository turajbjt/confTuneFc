# ConfTune FC v1.0.8 Release Notes ⚡

**ConfTune FC** is the open-source system optimization, kernel tuning, and automated deployment suite for Fedora Linux, Red Hat Enterprise Linux (RHEL), Rocky Linux, AlmaLinux, and CentOS Stream.

---

## 🚀 Key Improvements in v1.0.8

### 1. Repository Security & Secret Exclusions Hardening
- **Enhanced `.gitignore`**: Added defensive security exclusions to guard against accidental staging of credentials, private keys, and environment configs:
  - Private keys and certificates: `*.key`, `*.pem`, `*.cert`, `*.crt`, `*.pfx`, `*.p12`
  - SSH private identities: `*id_rsa*`, `*id_ed25519*`, `*id_ecdsa*`
  - Environment and credential files: `.env`, `.env.*`, `*.credentials`, `*.secret`

### 2. RPM Package Spec Metadata Anonymization
- **Maintainer Anonymization**: Updated the RPM spec file (`packaging/conftune-fc.spec`) `%changelog` metadata to attribute all package revisions uniformly to `BuildDesignCreate.com`, completely removing personal email addresses from repository source code and build manifests.

---

## 📦 Package Artifacts & Checksums (v1.0.8)

| File | SHA256 Checksum |
| :--- | :--- |
| `conftune-fc-1.0.8-1.noarch.rpm` | `b5eca99028a115120ab78cca3fe64e97003263725aa2504f7ece18529979a4df` |
| `conftune-fc-1.0.8-1.src.rpm` | `81219141ebf519df8f5e23b75252bc7f1dc728236aa23e9727974c89986c2a7e` |

---

## 📥 Installation & Upgrade Instructions

To upgrade to **v1.0.8** on Fedora, Rocky Linux, CentOS Stream, or RHEL:

```bash
sudo dnf update -y ./conftune-fc-1.0.8-1.noarch.rpm
```
*(or via rpm: `sudo rpm -Uvh ./conftune-fc-1.0.8-1.noarch.rpm`)*
