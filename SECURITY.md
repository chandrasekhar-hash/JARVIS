# J.A.R.V.I.S. Security Architecture

This document describes the Zero-Trust, Local-First Security and Identity Architecture implemented in **Phase 8.1**.

---

## 1. Core Security Principles

1. **Local-First & Offline Capable**: J.A.R.V.I.S. functions 100% offline out of the box. No external authentication server or internet connectivity is required.
2. **Zero-Trust Architecture**: Every installation auto-provisions a unique cryptographic user profile and device identity on first boot.
3. **Elliptic-Curve Modern Cryptography**: Device identities and message signatures utilize **Ed25519** elliptic-curve keys (`logs/device_ed25519_key.pem` and `logs/device_ed25519_pub.pem`).
4. **No Password Requirement for Local Mode**: Automatic, passwordless local operation while exposing abstract authentication interfaces (`BaseAuthProvider`) for future cloud OAuth integrations (`Google`, `GitHub`, `Apple`, `Microsoft`).
5. **Database Schema Versioning**: Automated schema migration tracking (`schema_version` table) in `logs/jarvis_memory.db` starting at `v1_identity_security`.

---

## 2. Identity & Device Models

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

## 3. Session & Token Architecture

- **`access_token`**: Cryptographically secure 32-byte token (`atk_...`), expires in 24 hours.
- **`refresh_token`**: Cryptographically secure 32-byte token (`rtk_...`), expires in 30 days.
- **`SessionStatus`**: `ACTIVE`, `EXPIRED`, or `REVOKED`.

---

## 4. Cryptographic Key Management

- Keys are stored locally under `logs/`:
  - `logs/device_ed25519_key.pem`: Ed25519 Private Key (PKCS8)
  - `logs/device_ed25519_pub.pem`: Ed25519 Public Key (SubjectPublicKeyInfo)
- SHA-256 fingerprinting ensures public keys can be verified visually across multi-device configurations in future cloud phases.
