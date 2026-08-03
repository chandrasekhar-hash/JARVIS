import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAXLAuth } from '../axl/context/AXLAuthContext';
import { useAXLRouter, ROUTE_STATES } from '../axl/context/AXLRouterContext';
import { fetchWithAuth } from '../axl/services/apiInterceptor';
import './UserProfileView.css';

const safeParseJson = async (res) => {
  try {
    const text = await res.text();
    if (!text || !text.trim()) return {};
    return JSON.parse(text);
  } catch (_) {
    return { detail: 'Server returned an invalid response.' };
  }
};

/* ─── Curated Futuristic & Science Quotes Collection ─────────────────── */
const JARVIS_QUOTES = [
  { text: "Innovation distinguishes between a leader and a follower.", author: "Steve Jobs" },
  { text: "The future belongs to those who prepare for it today.", author: "Malcolm X" },
  { text: "We can only see a short distance ahead, but there is plenty there that needs to be done.", author: "Alan Turing" },
  { text: "The present is theirs; the future, for which I really worked, is mine.", author: "Nikola Tesla" },
  { text: "Sometimes it's the people no one imagines anything of who do the things that no one can imagine.", author: "Alan Turing" },
  { text: "The best way to predict the future is to invent it.", author: "Alan Kay" },
  { text: "Any sufficiently advanced technology is indistinguishable from magic.", author: "Arthur C. Clarke" },
  { text: "The only limit to our realization of tomorrow will be our doubts of today.", author: "Franklin D. Roosevelt" },
  { text: "Imagination is more important than knowledge. Knowledge is limited. Imagination encircles the world.", author: "Albert Einstein" },
  { text: "It is not that I'm so smart, it's just that I stay with problems longer.", author: "Albert Einstein" },
  { text: "I have not failed. I've just found 10,000 ways that won't work.", author: "Thomas A. Edison" },
  { text: "The measure of intelligence is the ability to change.", author: "Albert Einstein" },
  { text: "Intelligence is the ability to adapt to change.", author: "Stephen Hawking" },
  { text: "Look up at the stars and not down at your feet. Try to make sense of what you see.", author: "Stephen Hawking" },
  { text: "Somewhere, something incredible is waiting to be known.", author: "Carl Sagan" },
  { text: "When something is important enough, you do it even if the odds are not in your favor.", author: "Elon Musk" },
  { text: "Part of the journey is the end. Everything is going to work out exactly the way it's supposed to.", author: "Tony Stark" },
  { text: "I am ready for any challenge, sir. Operational efficiency at maximum capacity.", author: "J.A.R.V.I.S." },
  { text: "Systems online. All subroutines functioning within optimal parameters.", author: "J.A.R.V.I.S." },
  { text: "The true sign of intelligence is not knowledge but imagination.", author: "Albert Einstein" },
  { text: "Science of today is the technology of tomorrow.", author: "Edward Teller" },
  { text: "The computer was born to solve problems that did not exist before.", author: "Bill Gates" },
];

/* ─── 3D Liquid & Cybermatic Background Canvas ───────────────────────── */
function ParticleCanvas() {
  const canvasRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const PARTICLE_COUNT = 110;
    const CONNECTION_DIST = 160;
    const particles = [];

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        z: Math.random() * 2 + 0.5,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 2.2 + 0.6,
        color: Math.random() > 0.4 ? '0, 225, 255' : '176, 38, 255',
        alpha: Math.random() * 0.55 + 0.2,
      });
    }

    let waveOffset = 0;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      waveOffset += 0.007;

      ctx.save();
      for (let w = 0; w < 3; w++) {
        ctx.beginPath();
        const baseColor = w % 2 === 0 ? 'rgba(0, 225, 255, ' : 'rgba(176, 38, 255, ';
        ctx.strokeStyle = `${baseColor}${0.12 - w * 0.03})`;
        ctx.lineWidth = 1.8 - w * 0.4;
        const startY = canvas.height * (0.2 + w * 0.15);

        for (let x = 0; x < canvas.width; x += 12) {
          const y = Math.sin(x * 0.004 + waveOffset + w) * (40 + w * 10) +
                    Math.cos(x * 0.002 - waveOffset * 0.5) * (20 + w * 5) + startY;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.restore();

      for (const p of particles) {
        p.x += p.vx * p.z;
        p.y += p.vy * p.z;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
      }

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < CONNECTION_DIST) {
            const opacity = (1 - dist / CONNECTION_DIST) * 0.22;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(0, 210, 255, ${opacity})`;
            ctx.lineWidth = 0.75 * particles[i].z;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * p.z, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.color}, ${p.alpha})`;
        ctx.shadowColor = `rgba(${p.color}, 0.8)`;
        ctx.shadowBlur = 10 * p.z;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      animRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, []);

  return <canvas ref={canvasRef} className="profile-particle-canvas" aria-hidden="true" />;
}

/* ─── Main User Profile View ───────────────────────────────────────────── */
export default function UserProfileView() {
  const { user, updateProfile, logout } = useAXLAuth();
  const { navigateTo } = useAXLRouter();

  /* ── Derived base values ── */
  const baseDisplayName = user?.display_name || user?.displayName || user?.username || 'User';
  const baseUsername    = user?.username || '';
  const email           = user?.email || '';

  /* ── Local editable state ── */
  const [editDisplayName, setEditDisplayName] = useState(baseDisplayName);
  const [editUsername, setEditUsername]       = useState(baseUsername);
  const [isEditingName, setIsEditingName]     = useState(false);
  const [isEditingUser, setIsEditingUser]     = useState(false);

  const [saveState, setSaveState]   = useState('idle');
  const [saveError, setSaveError]   = useState('');
  const [logoutState, setLogoutState] = useState('idle');

  /* ── Pick a random quote dynamically on mount ── */
  const [quote] = useState(() => {
    const idx = Math.floor(Math.random() * JARVIS_QUOTES.length);
    return JARVIS_QUOTES[idx];
  });

  const createdDate = user?.created_at
    ? new Date(user.created_at * 1000).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    : 'Aug 02, 2026';

  useEffect(() => {
    setEditDisplayName(user?.display_name || user?.displayName || user?.username || 'User');
    setEditUsername(user?.username || '');
  }, [user]);

  const getInitials = (name) => {
    if (!name || typeof name !== 'string') return 'J';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const liveInitials = getInitials(editDisplayName || baseDisplayName);

  const handleSave = useCallback(async () => {
    if (saveState === 'saving') return;
    setSaveError('');
    setSaveState('saving');
    try {
      await updateProfile(
        editDisplayName.trim() || undefined,
        editUsername.trim() || undefined
      );
      setSaveState('success');
      setIsEditingName(false);
      setIsEditingUser(false);
      setTimeout(() => setSaveState('idle'), 2800);
    } catch (err) {
      setSaveError(err.message || 'Failed to save changes.');
      setSaveState('error');
      setTimeout(() => { setSaveState('idle'); setSaveError(''); }, 4000);
    }
  }, [saveState, updateProfile, editDisplayName, editUsername]);

  const handleLogout = async () => {
    if (logoutState === 'loading') return;
    setLogoutState('loading');
    try { await logout(); } catch (_) { setLogoutState('idle'); }
  };

  /* ── Account Deletion Modal States ── */
  const [showDeleteModalStep1, setShowDeleteModalStep1] = useState(false);
  const [showDeleteModalStep2, setShowDeleteModalStep2] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [showDeletePassword, setShowDeletePassword] = useState(false);
  const [confirmCheckbox, setConfirmCheckbox] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleConfirmAccountDelete = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!deletePassword || !confirmCheckbox || isDeletingAccount) return;

    setIsDeletingAccount(true);
    setDeleteError('');

    try {
      const res = await fetchWithAuth('/account/delete', {
        method: 'POST',
        body: JSON.stringify({ password: deletePassword }),
      });
      const data = await safeParseJson(res);
      if (!res.ok) {
        let errMsg = 'Incorrect password.';
        if (typeof data.detail === 'string') {
          errMsg = data.detail;
        } else if (Array.isArray(data.detail) && data.detail.length > 0) {
          errMsg = data.detail[0]?.msg || 'Validation error.';
        } else if (data.message) {
          errMsg = data.message;
        }
        throw new Error(errMsg);
      }

      localStorage.clear();
      sessionStorage.clear();

      setShowDeleteModalStep1(false);
      setShowDeleteModalStep2(false);

      if (logout) {
        await logout();
      }

      if (navigateTo) {
        navigateTo(ROUTE_STATES.UNAUTHENTICATED);
      }
    } catch (err) {
      setDeleteError(err.message || 'Failed to delete account.');
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const handleBackToConsole = () => {
    navigateTo(ROUTE_STATES.AUTHENTICATED);
  };

  const systemId = `JARVIS-${(baseUsername || 'ABHISEK').toUpperCase()}-07`;

  return (
    <div className="profile-root">
      {/* 3D Particle & Laser Background */}
      <ParticleCanvas />

      {/* Cybernetic Radial Glow highlights */}
      <div className="profile-glow-bg glow-left" aria-hidden="true" />
      <div className="profile-glow-bg glow-right" aria-hidden="true" />

      {/* Main Container - Full Screen */}
      <main className="profile-main-container" role="main" aria-label="User Profile">

        {/* Top Back Navigation Bar */}
        <div className="profile-top-bar">
          <button
            type="button"
            className="btn-back-console"
            onClick={handleBackToConsole}
            aria-label="Back to JARVIS Console"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>BACK TO CONSOLE</span>
          </button>
        </div>

        <div className="profile-content-grid">

          {/* LEFT SIDEBAR PANEL */}
          <aside className="profile-sidebar-panel" aria-label="System Identity">
            <div className="sidebar-glass-card _3d-liquid-glass">

              {/* Glossy reflection overlay */}
              <div className="glass-shine-overlay" aria-hidden="true" />

              {/* SYSTEM ID */}
              <div className="sidebar-sys-id glowing-hud-title">{systemId}</div>

              {/* ACTIVE SESSION METRICS */}
              <div className="sidebar-metrics-block">
                <div className="metrics-header-row">
                  <span className="metrics-title">ACTIVE SESSION</span>
                  <span className="live-green-dot" aria-hidden="true" />
                </div>

                <div className="metrics-list">
                  <div className="metric-item">
                    <div className="metric-label-group">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="metric-icon">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                      </svg>
                      <span>STATUS</span>
                    </div>
                    <span className="metric-value status-online">ONLINE</span>
                  </div>

                  <div className="metric-item">
                    <div className="metric-label-group">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="metric-icon">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      <span>LAST ACTIVE</span>
                    </div>
                    <span className="metric-value">Just now</span>
                  </div>

                  <div className="metric-item">
                    <div className="metric-label-group">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="metric-icon">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                        <line x1="8" y1="21" x2="16" y2="21" />
                        <line x1="12" y1="17" x2="12" y2="21" />
                      </svg>
                      <span>DEVICE</span>
                    </div>
                    <span className="metric-value">Chrome on macOS</span>
                  </div>
                </div>
              </div>

              {/* RANDOM FUTURISTIC QUOTE BLOCK */}
              <div className="sidebar-quote-card _3d-liquid-card">
                <span className="quote-icon">“</span>
                <p className="quote-body">{quote.text}</p>
                <span className="quote-author">— {quote.author}</span>
              </div>

            </div>
          </aside>

          {/* RIGHT MAIN PROFILE SECTION */}
          <section className="profile-main-section">

            {/* HERO AVATAR & NAME HEADER */}
            <div className="profile-hero-block">
              {/* 3D Glowing Avatar Ring */}
              <div className="avatar-ring-container">
                <div className="avatar-ring-outer _3d-avatar-glow">
                  <div className="avatar-ring-inner">
                    <span className="avatar-initials-text">{liveInitials}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="avatar-pencil-btn"
                  onClick={() => setIsEditingName(true)}
                  aria-label="Edit name"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 20h9" />
                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                  </svg>
                </button>
              </div>

              {/* User Bio Details */}
              <div className="hero-bio-details">
                <div className="bio-name-row">
                  <h1 className="bio-display-name futuristic-font-glow">{editDisplayName || baseDisplayName}</h1>
                  <button
                    type="button"
                    className="bio-edit-btn"
                    onClick={() => setIsEditingName(!isEditingName)}
                    aria-label="Edit Display Name"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                  </button>
                </div>

                <div className="bio-username-row">
                  <span className="bio-username">@{editUsername || baseUsername}</span>
                  <button
                    type="button"
                    className="bio-edit-btn"
                    onClick={() => setIsEditingUser(!isEditingUser)}
                    aria-label="Edit Username"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                  </button>
                </div>

                <div className="bio-joined-date">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                  <span>Member since {createdDate}</span>
                </div>
              </div>
            </div>

            {/* ACCOUNT INFORMATION SECTION */}
            <div className="profile-section-block">
              <div className="section-header-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>ACCOUNT INFORMATION</span>
              </div>

              <div className="input-rows-wrapper">
                {/* DISPLAY NAME ROW */}
                <div className={`field-glass-bar _3d-liquid-bar ${isEditingName ? 'active-editing' : ''}`}>
                  <div className="field-bar-left">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="field-icon">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <span className="field-label-text">DISPLAY NAME</span>
                  </div>
                  <div className="field-bar-right">
                    <input
                      type="text"
                      className="field-text-input"
                      value={editDisplayName}
                      onChange={(e) => {
                        setEditDisplayName(e.target.value);
                        setSaveState('idle');
                        setSaveError('');
                      }}
                      aria-label="Display Name"
                    />
                    <button
                      type="button"
                      className={`check-circle-btn ${editDisplayName.trim() !== baseDisplayName ? 'dirty' : ''}`}
                      onClick={handleSave}
                      title="Save change"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* USERNAME ROW */}
                <div className={`field-glass-bar _3d-liquid-bar ${isEditingUser ? 'active-editing' : ''}`}>
                  <div className="field-bar-left">
                    <span className="field-icon-text">@</span>
                    <span className="field-label-text">USERNAME</span>
                  </div>
                  <div className="field-bar-right">
                    <input
                      type="text"
                      className="field-text-input"
                      value={editUsername}
                      onChange={(e) => {
                        setEditUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''));
                        setSaveState('idle');
                        setSaveError('');
                      }}
                      aria-label="Username"
                    />
                    <button
                      type="button"
                      className={`check-circle-btn ${editUsername.trim().toLowerCase() !== baseUsername.toLowerCase() ? 'dirty' : ''}`}
                      onClick={handleSave}
                      title="Save change"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* EMAIL ADDRESS ROW (READ-ONLY) */}
                <div className="field-glass-bar _3d-liquid-bar readonly-bar">
                  <div className="field-bar-left">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="field-icon">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                    <span className="field-label-text">EMAIL ADDRESS</span>
                  </div>
                  <div className="field-bar-right">
                    <span className="field-readonly-text">{email}</span>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="lock-icon">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* ACCOUNT STATUS SECTION */}
            <div className="profile-section-block">
              <div className="section-header-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span>ACCOUNT STATUS</span>
              </div>

              <div className="active-session-glass-banner _3d-liquid-banner">
                <div className="banner-text-group">
                  <div className="banner-main-title">
                    <span className="banner-dot" aria-hidden="true" />
                    <span>ACTIVE SESSION</span>
                  </div>
                  <p className="banner-desc">Your account is active and secure.</p>
                </div>
                <div className="banner-shield-box _3d-shield-glow">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#00d2ff" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    <polyline points="9 12 11 14 15 10" />
                  </svg>
                </div>
              </div>
            </div>

            {/* DANGER ZONE SECTION */}
            <div className="profile-section-block danger-zone-block">
              <div className="section-header-title danger-header-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <span>DANGER ZONE</span>
              </div>

              <div className="danger-zone-glass-banner _3d-liquid-banner">
                <div className="danger-text-group">
                  <div className="danger-main-title">Deleting your account is permanent.</div>
                  <p className="danger-desc">
                    This action will permanently remove your JARVIS account and cannot be undone.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-danger-delete-outlined"
                  onClick={() => {
                    setShowDeleteModalStep1(true);
                    setShowDeleteModalStep2(false);
                    setDeleteError('');
                  }}
                >
                  Delete My Account
                </button>
              </div>
            </div>

            {/* TOAST FEEDBACK */}
            {saveState === 'success' && (
              <div className="toast-banner toast-success">
                ✓ Profile changes saved successfully.
              </div>
            )}
            {saveState === 'error' && saveError && (
              <div className="toast-banner toast-error">
                ⚠️ {saveError}
              </div>
            )}

            {/* ULTRA-FUTURISTIC 3D HUD ACTION BUTTONS ROW */}
            <div className="profile-action-buttons-row">
              <button
                type="button"
                className={`futuristic-hud-btn btn-hud-save ${saveState === 'saving' ? 'loading' : ''}`}
                onClick={handleSave}
                disabled={saveState === 'saving'}
              >
                <div className="hud-btn-glow" aria-hidden="true" />
                <div className="hud-btn-content">
                  {saveState === 'saving' ? (
                    <>
                      <span className="btn-spinner" aria-hidden="true" />
                      <span>SAVING...</span>
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="hud-btn-icon">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                        <polyline points="17 21 17 13 7 13 7 21" />
                        <polyline points="7 3 7 8 15 8" />
                      </svg>
                      <span>SAVE CHANGES</span>
                    </>
                  )}
                </div>
              </button>

              <button
                type="button"
                className={`futuristic-hud-btn btn-hud-logout ${logoutState === 'loading' ? 'loading' : ''}`}
                onClick={handleLogout}
                disabled={logoutState === 'loading'}
              >
                <div className="hud-btn-glow" aria-hidden="true" />
                <div className="hud-btn-content">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="hud-btn-icon">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  <span>LOG OUT</span>
                </div>
              </button>
            </div>

          </section>

        </div>
      </main>

      {/* STEP 1: DELETE CONFIRMATION MODAL */}
      {showDeleteModalStep1 && (
        <div className="delete-modal-overlay">
          <div className="delete-modal-card _3d-liquid-modal">
            <div className="delete-modal-header">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <h3>Delete Account</h3>
            </div>
            <div className="delete-modal-body">
              <p className="delete-warning-bold">This action is permanent.</p>
              <p className="delete-warning-sub">Deleting your account will remove:</p>
              <ul className="delete-removal-list">
                <li>• Profile</li>
                <li>• Memory</li>
                <li>• Personal settings</li>
                <li>• Saved preferences</li>
                <li>• Chat history owned by JARVIS</li>
                <li>• Active sessions</li>
              </ul>
              <p className="delete-warning-bold">This action cannot be undone.</p>
            </div>
            <div className="delete-modal-footer">
              <button
                type="button"
                className="modal-btn-cancel"
                onClick={() => setShowDeleteModalStep1(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn-danger"
                onClick={() => {
                  setShowDeleteModalStep1(false);
                  setShowDeleteModalStep2(true);
                  setDeletePassword('');
                  setConfirmCheckbox(false);
                  setDeleteError('');
                }}
              >
                Delete Account
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: PASSWORD CONFIRMATION MODAL */}
      {showDeleteModalStep2 && (
        <div className="delete-modal-overlay">
          <div className="delete-modal-card _3d-liquid-modal">
            <div className="delete-modal-header">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <h3>Confirm Password</h3>
            </div>
            <form onSubmit={handleConfirmAccountDelete} className="delete-modal-body">
              {deleteError && (
                <div className="delete-modal-error">
                  ⚠️ {deleteError}
                </div>
              )}
              <div className="delete-input-group">
                <label htmlFor="current-password-input">Current Password</label>
                <div className="delete-password-wrapper">
                  <input
                    id="current-password-input"
                    type={showDeletePassword ? 'text' : 'password'}
                    className="delete-password-input"
                    placeholder="Enter your current password"
                    value={deletePassword}
                    onChange={(e) => {
                      setDeletePassword(e.target.value);
                      setDeleteError('');
                    }}
                    disabled={isDeletingAccount}
                    required
                  />
                  <button
                    type="button"
                    className="delete-password-toggle-btn"
                    onClick={() => setShowDeletePassword(!showDeletePassword)}
                    aria-label={showDeletePassword ? 'Hide password' : 'Show password'}
                  >
                    {showDeletePassword ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    )}
                  </button>
                </div>
              </div>
              <label className="delete-checkbox-label">
                <input
                  type="checkbox"
                  checked={confirmCheckbox}
                  onChange={(e) => setConfirmCheckbox(e.target.checked)}
                  disabled={isDeletingAccount}
                />
                <span>I understand this action cannot be undone.</span>
              </label>
              <div className="delete-modal-footer">
                <button
                  type="button"
                  className="modal-btn-cancel"
                  onClick={() => {
                    setShowDeleteModalStep2(false);
                    setDeletePassword('');
                    setConfirmCheckbox(false);
                    setDeleteError('');
                  }}
                  disabled={isDeletingAccount}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-btn-danger"
                  disabled={!deletePassword || !confirmCheckbox || isDeletingAccount}
                >
                  {isDeletingAccount ? 'DELETING...' : 'DELETE MY ACCOUNT'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
