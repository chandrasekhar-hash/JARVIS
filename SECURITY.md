# J.A.R.V.I.S. Security Architecture

This document describes the Zero-Trust, Local-First Security and Identity Architecture implemented in **Phase 8.1**.

---

## 1. Core Security Principles

1. **Local-First & Offline Capable**: J.A.R.V.I.S. functions 100% offline out of the box. No external authentication server or internet connectivity is required.
2. **Zero-Trust Architecture**: Every installation auto-provisions a unique cryptographic user profile and device identity on first boot.
3. **Elliptic-Curve Modern Cryptography**: Device identities and message signatures utilize **Ed25519** elliptic-curve keys managed via OS Secure Credential Storage.
4. **OS Secure Credential Storage**: Private keys are stored in native operating system credential managers (**Apple Keychain**, **Windows DPAPI**, **Linux Secret Service API**). Plaintext private key `.pem` files are never written to disk.
5. **Random 256-Bit Master Secret Fallback**: If native OS keystore is unavailable, fallback storage uses **AES-256-GCM** authenticated encryption (`logs/device_ed25519_key.enc`) with a cryptographically secure random 256-bit master secret (`logs/.master_secret`).
6. **Transactional Legacy Migration**: Legacy `logs/device_ed25519_key.pem` files are automatically imported on boot using a 7-step transactional sequence (**Detect → Read → Import → Verify Signature → Verify Public Key Fingerprint → Mark Success → Secure Delete**).
7. **Database Schema Versioning**: Automated schema migration tracking (`schema_version` table) in `logs/jarvis_memory.db` starting at `v1_identity_security`.

---

## 2. OS Secure Credential Keystore Subsystem (`Backend/security/keystore/`)

### Platform Support Matrix

| Operating System | Primary Keystore Provider | Technology | Fallback Mechanism |
| :--- | :--- | :--- | :--- |
| **macOS** | Apple Keychain | `/usr/bin/security` / `keyring` | AES-256-GCM Encrypted File |
| **Windows** | Windows DPAPI | `win32crypt` / `keyring` | AES-256-GCM Encrypted File |
| **Linux** | Linux Secret Service | `libsecret` / `keyring` | AES-256-GCM Encrypted File |
| **Containers / Headless** | AES-256-GCM Encrypted File | Random 256-bit Master Secret + PBKDF2 | Log Security Warning |

### High-Level Non-Exportable Cryptographic API

Application components interact strictly with `KeystoreManager` via high-level non-exportable operations:
- `sign_data(message)`: Signs payload bytes inside the keystore.
- `verify_signature(pub_pem, signature, message)`: Verifies payload signatures.
- `export_public_key_pem()`: Returns public key PEM string.
- `rotate_keypair()`: Rotates keypair, updates fingerprint metadata, and preserves device trust.
- `health()`: Exposes operational health telemetry (`active_provider`, `secure_storage_available`, `fallback_active`, `migration_status`, `primary_key_present`, `rotation_count`, `last_error`). Identity payload/fingerprints are explicitly excluded from health probes.

---

## 3. Backup, Recovery & Security Guarantees

### Private Key Export Restriction
Ed25519 private key bytes are **never exportable** over API endpoints, saved in logs, or exposed to user-space Python functions as string variables.

### Keystore Reset & Recovery Behavior
- **Public Key & Identity Retention**: Device IDs (`dev_...`) and public key fingerprints are stored in `logs/jarvis_memory.db`.
- **OS Keystore Reset**: If the OS Keychain or DPAPI keystore is cleared, `KeystoreManager` generates a fresh keypair and updates public key metadata. The existing user identity is preserved while re-establishing cryptographic trust.

---

## 4. Identity & Device Models

### User Profile (`user_profiles`)
- **`user_id`**: Unique string prefixed with `usr_` (e.g. `usr_114a3a065fc0422a`).
- **`display_name`**: User's display name.
- **`locale` & `timezone`**: User preferences.
- **`ai_defaults`**: JSON configuration storing preferred AI model, provider priority, and voice synthesis settings.

### Device Profile (`device_profiles`)
- **`device_id`**: Unique string prefixed with `dev_` (e.g. `dev_29eef772b9d24eec`).
- **`public_key`**: PEM-encoded Ed25519 public key.
- **`public_key_fingerprint`**: SHA-256 fingerprint (e.g. `SHA256:e1a9ee6025c43915:fe3aec9af548775f`).
- **`trust_state`**: Device trust status (`UNTRUSTED`, `PROVISIONAL`, `TRUSTED`, `REVOKED`).

---

## 5. Session & Token Architecture

- **`access_token`**: Cryptographically secure 32-byte token (`atk_...`), expires in 24 hours.
- **`refresh_token`**: Cryptographically secure 32-byte token (`rtk_...`), expires in 30 days.
- **`SessionStatus`**: `ACTIVE`, `EXPIRED`, or `REVOKED`.
