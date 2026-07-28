import React, { useState, useEffect } from 'react';
import './Identity.css';

const API_BASE = 'http://localhost:8000/api';

const Identity = () => {
  const [userProfile, setUserProfile] = useState(null);
  const [deviceProfile, setDeviceProfile] = useState(null);
  const [securityStatus, setSecurityStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Edit state
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchIdentityData = async () => {
    try {
      setLoading(true);
      const [uRes, dRes, sRes] = await Promise.all([
        fetch(`${API_BASE}/identity`),
        fetch(`${API_BASE}/device`),
        fetch(`${API_BASE}/security/status`),
      ]);

      if (!uRes.ok || !dRes.ok || !sRes.ok) {
        throw new Error('Failed to fetch identity & security data');
      }

      const uData = await uRes.json();
      const dData = await dRes.json();
      const sData = await sRes.json();

      setUserProfile(uData.user_profile);
      setDeviceProfile(dData.device_profile);
      setSecurityStatus(sData.security_status);

      if (uData.user_profile) {
        setDisplayName(uData.user_profile.display_name || '');
        setEmail(uData.user_profile.email || '');
      }
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIdentityData();
  }, []);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);

    try {
      const res = await fetch(`${API_BASE}/identity`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: displayName,
          email: email,
        }),
      });

      if (!res.ok) throw new Error('Failed to update profile');
      const data = await res.json();
      setUserProfile(data.user_profile);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleTrust = async () => {
    if (!deviceProfile) return;
    const newTrust = deviceProfile.trust_state === 'trusted' ? 'revoked' : 'trusted';
    try {
      const res = await fetch(`${API_BASE}/device/trust`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trust_state: newTrust }),
      });
      if (!res.ok) throw new Error('Failed to update device trust');
      const data = await res.json();
      setDeviceProfile(data.device_profile);
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading) {
    return <div className="identity-loading">Loading Identity & Security Layer...</div>;
  }

  return (
    <div className="identity-dashboard">
      <div className="identity-header">
        <div className="identity-title-container">
          <h2>🛡️ Identity & Security Layer (Phase 8.1)</h2>
          <p className="identity-subtitle">
            Local-first cryptographic identity, Ed25519 signing keys, and device trust telemetry.
          </p>
        </div>
        <button className="identity-refresh-btn" onClick={fetchIdentityData}>
          🔄 Refresh Security Telemetry
        </button>
      </div>

      {error && <div className="identity-error-banner">⚠️ {error}</div>}

      <div className="identity-grid">
        {/* User Profile Card */}
        <div className="identity-card">
          <div className="card-header">
            <h3>👤 User Identity Profile</h3>
            <span className="badge-local">LOCAL FIRST</span>
          </div>

          <form onSubmit={handleUpdateProfile} className="profile-form">
            <div className="form-group">
              <label>User ID:</label>
              <input type="text" value={userProfile?.user_id || ''} disabled className="input-disabled" />
            </div>

            <div className="form-group">
              <label>Display Name:</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="J.A.R.V.I.S. User"
                required
              />
            </div>

            <div className="form-group">
              <label>Email Address (Optional):</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@jarvis.ai"
              />
            </div>

            <div className="form-group-row">
              <div className="form-group half">
                <label>Locale:</label>
                <input type="text" value={userProfile?.locale || 'en-US'} disabled className="input-disabled" />
              </div>
              <div className="form-group half">
                <label>Timezone:</label>
                <input type="text" value={userProfile?.timezone || 'UTC'} disabled className="input-disabled" />
              </div>
            </div>

            <button type="submit" className="save-btn" disabled={saving}>
              {saving ? 'Saving...' : '💾 Save Profile'}
            </button>

            {saveSuccess && <span className="save-success-msg">✓ Profile saved successfully!</span>}
          </form>
        </div>

        {/* Device Profile Card */}
        <div className="identity-card">
          <div className="card-header">
            <h3>💻 Cryptographic Device Identity</h3>
            <span className={`badge-trust ${deviceProfile?.trust_state}`}>
              {deviceProfile?.trust_state?.toUpperCase()}
            </span>
          </div>

          <div className="device-details">
            <div className="detail-row">
              <span className="label">Device Name:</span>
              <span className="value">{deviceProfile?.device_name}</span>
            </div>
            <div className="detail-row">
              <span className="label">Platform / Arch:</span>
              <span className="value">{deviceProfile?.platform} ({deviceProfile?.architecture})</span>
            </div>
            <div className="detail-row">
              <span className="label">Device ID:</span>
              <span className="value code-font">{deviceProfile?.device_id}</span>
            </div>
            <div className="detail-row">
              <span className="label">Signing Key Spec:</span>
              <span className="value badge-crypto">Ed25519 Elliptic Curve</span>
            </div>

            <div className="key-fingerprint-box">
              <span className="fingerprint-label">Ed25519 Public Key Fingerprint:</span>
              <code className="fingerprint-code">{deviceProfile?.public_key_fingerprint}</code>
            </div>

            <button
              className={`trust-toggle-btn ${deviceProfile?.trust_state === 'trusted' ? 'revoke' : 'trust'}`}
              onClick={handleToggleTrust}
            >
              {deviceProfile?.trust_state === 'trusted' ? '⛔ Revoke Device Trust' : '✅ Trust Device'}
            </button>
          </div>
        </div>

        {/* Security Status Telemetry Card */}
        <div className="identity-card full-width">
          <div className="card-header">
            <h3>🔒 Zero-Trust Security Status</h3>
            <span className="badge-version">{securityStatus?.current_schema_version}</span>
          </div>

          <div className="security-telemetry-grid">
            <div className="telemetry-tile">
              <span className="tile-label">Security Model</span>
              <span className="tile-value highlight">Zero-Trust Local First</span>
            </div>
            <div className="telemetry-tile">
              <span className="tile-label">Crypto Algorithm</span>
              <span className="tile-value highlight">{securityStatus?.crypto_algorithm || 'Ed25519'}</span>
            </div>
            <div className="telemetry-tile">
              <span className="tile-label">Active Sessions</span>
              <span className="tile-value">{securityStatus?.active_sessions_count || 0}</span>
            </div>
            <div className="telemetry-tile">
              <span className="tile-label">Database Schema</span>
              <span className="tile-value">{securityStatus?.current_schema_version}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Identity;
