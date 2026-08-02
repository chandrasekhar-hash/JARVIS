import React, { useState, useRef, useEffect } from 'react';
import { useAXLAuth } from '../context/AXLAuthContext';
import { useAXLRouter, ROUTE_STATES } from '../context/AXLRouterContext';
import JarvisParticleCanvas from './JarvisParticleCanvas';
import './AuthView.css';

export default function AuthView() {
  const { user, login, register, forgotPassword } = useAXLAuth();
  const { navigateTo } = useAXLRouter();

  // Full-screen Welcome Video Intro State
  const [showWelcomeIntro, setShowWelcomeIntro] = useState(true);
  const [hasUserInitialized, setHasUserInitialized] = useState(false);
  const [isFadingInit, setIsFadingInit] = useState(false);
  const [isHoveringInitBtn, setIsHoveringInitBtn] = useState(false);

  // Audio & Greeting Refs
  const welcomeVideoRef = useRef(null);
  const welcomeAudioRef = useRef(null);
  const audioObjectUrlRef = useRef(null);
  const hasWelcomeVoicePlayedRef = useRef(false);

  const [isFadingOutIntro, setIsFadingOutIntro] = useState(false);

  const transitionStartedRef = useRef(false);
  const [isTransitioningToLogin, setIsTransitioningToLogin] = useState(false);

  const playWelcomeVoice = async () => {
    if (hasWelcomeVoicePlayedRef.current) return;
    if (transitionStartedRef.current) return;
    if (!welcomeAudioRef.current) return;

    hasWelcomeVoicePlayedRef.current = true;
    try {
      welcomeAudioRef.current.volume = 1.0;
      welcomeAudioRef.current.muted = false;
      welcomeAudioRef.current.currentTime = 0;
      await welcomeAudioRef.current.play();
      console.log('[JARVIS Welcome Voice] Playback started successfully');
    } catch (error) {
      console.error('[JARVIS Welcome Voice] Playback failed:', error);
    }
  };

  // Explicit user-activation handler on clicking INITIALIZE
  const handleInitialize = () => {
    setIsFadingInit(true);

    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const tempCtx = new AudioCtx();
        if (tempCtx.state === 'suspended') {
          tempCtx.resume();
        }
      }
    } catch (_) {}

    try {
      const storedVisitor = localStorage.getItem('jarvis_last_visitor');
      let greetingText = "Welcome to J.A.R.V.I.S.";

      if (storedVisitor) {
        try {
          const parsedVisitor = JSON.parse(storedVisitor);
          const nameToSay = parsedVisitor.display_name || parsedVisitor.username;
          if (nameToSay && nameToSay.trim()) {
            greetingText = `Welcome back, ${nameToSay.trim()}.`;
          }
        } catch (_) {}
      }

      fetch('/api/speech/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: greetingText }),
      })
        .then((res) => {
          if (!res.ok) throw new Error('Speech synthesis failed');
          return res.blob();
        })
        .then((blob) => {
          if (transitionStartedRef.current) return;

          const objectUrl = URL.createObjectURL(blob);
          audioObjectUrlRef.current = objectUrl;

          const audio = new Audio(objectUrl);
          audio.volume = 1.0;
          welcomeAudioRef.current = audio;

          audio.onended = () => {
            if (audioObjectUrlRef.current) {
              URL.revokeObjectURL(audioObjectUrlRef.current);
              audioObjectUrlRef.current = null;
            }
          };

          if (welcomeVideoRef.current && welcomeVideoRef.current.currentTime >= 1.0) {
            playWelcomeVoice();
          }
        })
        .catch((err) => {
          console.warn('[JARVIS TTS] Fallback greeting speech error:', err);
        });
    } catch (e) {
      console.warn('[JARVIS TTS] Speech initialization error:', e);
    }

    setTimeout(() => {
      setHasUserInitialized(true);
      if (welcomeVideoRef.current) {
        welcomeVideoRef.current.muted = true;
        welcomeVideoRef.current.play().catch((err) => {
          console.warn('Welcome video play error:', err);
          handleWelcomeVideoEnd();
        });
      }
    }, 400);
  };

  const handleVideoTimeUpdate = (currentTime) => {
    if (currentTime >= 1.0 && !hasWelcomeVoicePlayedRef.current) {
      playWelcomeVoice();
    }
  };

  const transitionToLogin = () => {
    if (transitionStartedRef.current) return;
    transitionStartedRef.current = true;

    if (welcomeAudioRef.current) {
      try {
        welcomeAudioRef.current.pause();
        welcomeAudioRef.current.currentTime = 0;
      } catch (_) {}
    }

    setIsTransitioningToLogin(true);
    setTimeout(() => {
      setShowWelcomeIntro(false);
    }, 900);
  };

  const handleWelcomeVideoEnd = () => {
    transitionToLogin();
  };

  const handleSkipClick = (e) => {
    e.stopPropagation();
    if (welcomeVideoRef.current) {
      try {
        welcomeVideoRef.current.pause();
      } catch (_) {}
    }
    if (welcomeAudioRef.current) {
      try {
        welcomeAudioRef.current.pause();
        welcomeAudioRef.current.currentTime = 0;
      } catch (_) {}
    }
    transitionToLogin();
  };

  // Auth Mode: false = LOGIN | true = REGISTER
  const [isRegister, setIsRegister] = useState(false);
  const [isForgotPassword, setIsForgotPassword] = useState(false);

  // Login form state
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [showLoginPass, setShowLoginPass] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Register form state
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [showRegPass, setShowRegPass] = useState(false);
  const [showRegConfirmPass, setShowRegConfirmPass] = useState(false);

  // Validation & Submitting state
  const [validationError, setValidationError] = useState('');
  const [authSuccessMsg, setAuthSuccessMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Password criteria helper
  const hasMinLength = regPassword.length >= 8;
  const hasUppercase = /[A-Z]/.test(regPassword);
  const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(regPassword);

  const isValidEmail = (email) => {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email.trim());
  };

  const handleSwitchToRegister = () => {
    setIsRegister(true);
    setIsForgotPassword(false);
    setValidationError('');
    setAuthSuccessMsg('');
    setLoginPass('');
    setRegUsername('');
    setRegEmail('');
    setRegPassword('');
    setRegConfirmPassword('');
  };

  const handleSwitchToLogin = () => {
    setIsRegister(false);
    setIsForgotPassword(false);
    setValidationError('');
    setAuthSuccessMsg('');
    setRegPassword('');
    setRegConfirmPassword('');
  };

  const handleStartForgotPassword = () => {
    setIsForgotPassword(true);
    setIsRegister(false);
    setValidationError('');
    setAuthSuccessMsg('Account recovery is currently unavailable.');
  };

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (submitting) return;

    setValidationError('');
    setAuthSuccessMsg('');

    // --- 1. REGISTER MODE ---
    if (isRegister) {
      if (!regUsername.trim() || !regEmail.trim() || !regPassword || !regConfirmPassword) {
        setValidationError('Please fill in all required fields.');
        return;
      }

      if (!isValidEmail(regEmail)) {
        setValidationError('Enter a valid email address.');
        return;
      }

      if (!hasMinLength || !hasUppercase || !hasSpecialChar) {
        setValidationError('Password does not meet the security requirements.');
        return;
      }

      if (regPassword !== regConfirmPassword) {
        setValidationError('Passwords do not match.');
        return;
      }

      setSubmitting(true);
      try {
        await register(regUsername.trim(), regEmail.trim(), regPassword);
        setIsRegister(false);
        setLoginUser(regUsername.trim());
        setLoginPass('');
        setAuthSuccessMsg('Account created successfully. Please log in.');
        setRegPassword('');
        setRegConfirmPassword('');
      } catch (err) {
        setValidationError(err.message || 'Failed to create account.');
      } finally {
        setSubmitting(false);
      }
      return;
    }

    // --- 2. LOGIN MODE ---
    if (!loginUser.trim() || !loginPass) {
      setValidationError('Username/email and password are required.');
      return;
    }

    setSubmitting(true);
    try {
      await login(loginUser.trim(), loginPass, rememberMe);
      navigateTo(ROUTE_STATES.AUTHENTICATED);
    } catch (err) {
      setValidationError(err.message || 'Invalid email/username or password.');
    } finally {
      setSubmitting(false);
    }
  };

  if (showWelcomeIntro) {
    return (
      <>
        {isTransitioningToLogin && (
          <div className="auth-viewport-container">
            <div className="auth-panel-left">
              <video
                className="left-panel-video"
                autoPlay
                muted
                loop
                playsInline
                preload="auto"
                onError={(e) => console.warn('Left side video load error:', e)}
              >
                <source src="/videos/left_side_video_pingpong.mp4" type="video/mp4" />
              </video>
            </div>

            <div className="auth-panel-right auth-panel-right-entering">
              <div className="auth-content-box">
                <div className="auth-brand-header">
                  <h1 className="brand-name">J.A.R.V.I.S.</h1>
                  <div className="brand-subtitle-row">
                    <span className="brand-line"></span>
                    <span className="brand-subtitle">YOUR INTELLIGENT ASSISTANT</span>
                    <span className="brand-line"></span>
                  </div>
                </div>

                <div key={isRegister ? 'register' : 'login'} className="auth-form-animated-wrapper">
                  <div className="auth-section-header">
                    <h2 className="login-title">LOGIN</h2>
                    <p className="login-desc">Enter your credentials to access your system.</p>
                  </div>

                  <form className="auth-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                      <div className="input-wrapper">
                        <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                          <circle cx="12" cy="7" r="4"></circle>
                        </svg>
                        <input
                          type="text"
                          value={loginUser}
                          onChange={(e) => setLoginUser(e.target.value)}
                          placeholder="Email or Username"
                          autoComplete="off"
                          disabled={submitting}
                        />
                      </div>
                    </div>

                    <div className="form-group">
                      <div className="input-wrapper">
                        <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                        <input
                          type={showLoginPass ? 'text' : 'password'}
                          value={loginPass}
                          onChange={(e) => setLoginPass(e.target.value)}
                          placeholder="Password"
                          autoComplete="off"
                          disabled={submitting}
                        />
                      </div>
                    </div>

                    <div className="form-controls-row">
                      <label className="remember-checkbox-label">
                        <input
                          type="checkbox"
                          checked={rememberMe}
                          onChange={(e) => setRememberMe(e.target.checked)}
                          disabled={submitting}
                        />
                        <span className="custom-checkbox"></span>
                        <span className="checkbox-text">Remember Me</span>
                      </label>

                      <button
                        type="button"
                        className="forgot-password-link"
                        onClick={handleStartForgotPassword}
                        disabled={submitting}
                      >
                        Forgot Password?
                      </button>
                    </div>

                    <button type="submit" className="login-submit-btn" disabled={submitting}>
                      <span>{submitting ? 'AUTHENTICATING...' : 'LOGIN'}</span>
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className={`welcome-video-contracting-overlay ${isTransitioningToLogin ? 'contracting-to-left' : ''}`}>
          {!hasUserInitialized && (
            <div className={`welcome-init-overlay ${isFadingInit ? 'fade-out' : ''}`}>
              <JarvisParticleCanvas
                isHoveringBtn={isHoveringInitBtn}
                isActivating={isFadingInit}
              />

              <div className="welcome-init-title" style={{ zIndex: 2 }}>J.A.R.V.I.S.</div>
              <button
                className="welcome-init-btn"
                style={{ zIndex: 2 }}
                onClick={handleInitialize}
                onMouseEnter={() => setIsHoveringInitBtn(true)}
                onMouseLeave={() => setIsHoveringInitBtn(false)}
              >
                INITIALIZE
              </button>
              <div className="welcome-init-subtitle" style={{ zIndex: 2 }}>PERSONAL AI SYSTEM</div>
            </div>
          )}

          <video
            ref={welcomeVideoRef}
            className="welcome-fullscreen-video"
            muted
            playsInline
            preload="auto"
            onTimeUpdate={(e) => handleVideoTimeUpdate(e.target.currentTime)}
            onEnded={handleWelcomeVideoEnd}
            onError={(e) => {
              console.warn('Welcome video load error, falling back to Auth UI:', e);
              handleWelcomeVideoEnd();
            }}
          >
            <source src="/videos/welcome_video.mp4" type="video/mp4" />
          </video>

          {isFadingInit && !isTransitioningToLogin && (
            <button
              type="button"
              className="welcome-skip-btn"
              onClick={handleSkipClick}
              aria-label="Skip welcome video"
            >
              <span>SKIP</span>
              <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </button>
          )}
        </div>
      </>
    );
  }

  return (
    <div className="auth-viewport-container">
      {/* LEFT 50% PANEL — FROZEN LOOPING JARVIS VIDEO */}
      <div className="auth-panel-left">
        <video
          className="left-panel-video"
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          onError={(e) => console.warn('Left side video load error:', e)}
        >
          <source src="/videos/left_side_video_pingpong.mp4" type="video/mp4" />
        </video>
      </div>

      {/* RIGHT 50% PANEL — LOGIN / REGISTER INTERFACE */}
      <div className="auth-panel-right">
        <div className="auth-content-box">
          
          {/* BRAND HEADER */}
          <div className="auth-brand-header">
            <h1 className="brand-name">J.A.R.V.I.S.</h1>
            <div className="brand-subtitle-row">
              <span className="brand-line"></span>
              <span className="brand-subtitle">YOUR INTELLIGENT ASSISTANT</span>
              <span className="brand-line"></span>
            </div>
          </div>

          {/* DYNAMIC FORM CONTAINER */}
          <div key={isRegister ? 'register' : isForgotPassword ? 'forgot' : 'login'} className="auth-form-animated-wrapper">
            
            {/* SECTION HEADER */}
            <div className="auth-section-header">
              <h2 className="login-title">
                {isForgotPassword ? 'ACCOUNT RECOVERY' : isRegister ? 'CREATE ACCOUNT' : 'LOGIN'}
              </h2>
              <p className="login-desc">
                {isForgotPassword
                  ? 'Account recovery status'
                  : isRegister
                  ? 'Enter your details to create a new JARVIS account.'
                  : 'Enter your credentials to access your system.'}
              </p>
            </div>

            {/* INLINE SUCCESS BANNER */}
            {authSuccessMsg && (
              <div className="auth-success-banner">
                {authSuccessMsg}
              </div>
            )}

            {/* INLINE VALIDATION ERROR */}
            {validationError && (
              <div className="auth-validation-error" role="alert" aria-live="assertive">
                <span>{validationError}</span>
              </div>
            )}

            {/* DYNAMIC FORM */}
            <form className="auth-form" onSubmit={handleSubmit}>
              
              {/* ==================== FORGOT PASSWORD (UNAVAILABLE) ==================== */}
              {isForgotPassword && (
                <div style={{ marginTop: '10px', marginBottom: '20px', textAlign: 'center' }}>
                  <button
                    type="button"
                    className="login-submit-btn"
                    onClick={handleSwitchToLogin}
                  >
                    <span>RETURN TO LOGIN</span>
                  </button>
                </div>
              )}

              {/* ==================== LOGIN MODE ==================== */}
              {!isForgotPassword && !isRegister && (
                <>
                  {/* USERNAME / EMAIL INPUT */}
                  <div className="form-group">
                    <div className="input-wrapper">
                      <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                      </svg>
                      <input
                        type="text"
                        value={loginUser}
                        onChange={(e) => setLoginUser(e.target.value)}
                        placeholder="Email or Username"
                        autoComplete="off"
                        disabled={submitting}
                        aria-invalid={Boolean(validationError)}
                      />
                    </div>
                  </div>

                  {/* PASSWORD INPUT */}
                  <div className="form-group">
                    <div className="input-wrapper">
                      <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                      </svg>
                      <input
                        type={showLoginPass ? 'text' : 'password'}
                        value={loginPass}
                        onChange={(e) => setLoginPass(e.target.value)}
                        placeholder="Password"
                        autoComplete="off"
                        disabled={submitting}
                        aria-invalid={Boolean(validationError)}
                      />
                      <button
                        type="button"
                        className="password-toggle-btn"
                        onClick={() => setShowLoginPass(!showLoginPass)}
                        aria-label={showLoginPass ? 'Hide password' : 'Show password'}
                      >
                        {showLoginPass ? (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* REMEMBER ME + FORGOT PASSWORD */}
                  <div className="form-controls-row">
                    <label className="remember-checkbox-label">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        disabled={submitting}
                      />
                      <span className="custom-checkbox"></span>
                      <span className="checkbox-text">Remember Me</span>
                    </label>

                    <button
                      type="button"
                      className="forgot-password-link"
                      onClick={handleStartForgotPassword}
                      disabled={submitting}
                    >
                      Forgot Password?
                    </button>
                  </div>

                  {/* LOGIN BUTTON */}
                  <button type="submit" className="login-submit-btn" disabled={submitting} aria-busy={submitting}>
                    <span>{submitting ? 'AUTHENTICATING...' : 'LOGIN'}</span>
                    {!submitting && (
                      <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                      </svg>
                    )}
                  </button>
                </>
              )}

              {/* ==================== REGISTER MODE ==================== */}
              {!isForgotPassword && isRegister && (
                <>
                  {/* USERNAME INPUT */}
                  <div className="form-group form-group-dense">
                    <div className="input-wrapper">
                      <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                      </svg>
                      <input
                        type="text"
                        value={regUsername}
                        onChange={(e) => setRegUsername(e.target.value)}
                        placeholder="Username"
                        autoComplete="off"
                        disabled={submitting}
                        aria-invalid={Boolean(validationError)}
                      />
                    </div>
                  </div>

                  {/* EMAIL INPUT */}
                  <div className="form-group form-group-dense">
                    <div className="input-wrapper">
                      <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                        <polyline points="22,6 12,13 2,6"></polyline>
                      </svg>
                      <input
                        type="email"
                        value={regEmail}
                        onChange={(e) => {
                          setRegEmail(e.target.value);
                          if (validationError === 'Enter a valid email address.') setValidationError('');
                        }}
                        onBlur={() => {
                          if (regEmail.trim() && !isValidEmail(regEmail)) {
                            setValidationError('Enter a valid email address.');
                          } else if (validationError === 'Enter a valid email address.') {
                            setValidationError('');
                          }
                        }}
                        placeholder="Email"
                        autoComplete="off"
                        disabled={submitting}
                        aria-invalid={Boolean(validationError)}
                      />
                    </div>
                  </div>

                  {/* PASSWORD INPUT */}
                  <div className="form-group form-group-dense">
                    <div className="input-wrapper">
                      <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                      </svg>
                      <input
                        type={showRegPass ? 'text' : 'password'}
                        value={regPassword}
                        onChange={(e) => {
                          setRegPassword(e.target.value);
                          if (validationError === 'Password does not meet the security requirements.') setValidationError('');
                          if (regConfirmPassword && e.target.value === regConfirmPassword && validationError === 'Passwords do not match.') setValidationError('');
                        }}
                        placeholder="Password"
                        autoComplete="off"
                        disabled={submitting}
                        aria-invalid={Boolean(validationError)}
                      />
                      <button
                        type="button"
                        className="password-toggle-btn"
                        onClick={() => setShowRegPass(!showRegPass)}
                        aria-label={showRegPass ? 'Hide password' : 'Show password'}
                      >
                        {showRegPass ? (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* REAL-TIME PASSWORD REQUIREMENTS INDICATOR */}
                  <div className="password-requirements-box">
                    <span className="req-header">Password must contain:</span>
                    <div className="req-items-row">
                      <span className={`req-tag ${hasMinLength ? 'valid' : 'invalid'}`}>
                        {hasMinLength ? '✓' : '✕'} 8+ characters
                      </span>
                      <span className={`req-tag ${hasUppercase ? 'valid' : 'invalid'}`}>
                        {hasUppercase ? '✓' : '✕'} 1 uppercase letter
                      </span>
                      <span className={`req-tag ${hasSpecialChar ? 'valid' : 'invalid'}`}>
                        {hasSpecialChar ? '✓' : '✕'} 1 special character
                      </span>
                    </div>
                  </div>

                  {/* CONFIRM PASSWORD INPUT */}
                  <div className="form-group form-group-dense">
                    <div className="input-wrapper">
                      <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                      </svg>
                      <input
                        type={showRegConfirmPass ? 'text' : 'password'}
                        value={regConfirmPassword}
                        onChange={(e) => {
                          setRegConfirmPassword(e.target.value);
                          if (regPassword && e.target.value === regPassword && validationError === 'Passwords do not match.') {
                            setValidationError('');
                          } else if (regPassword && e.target.value !== regPassword) {
                            setValidationError('Passwords do not match.');
                          }
                        }}
                        placeholder="Confirm Password"
                        autoComplete="off"
                        disabled={submitting}
                        aria-invalid={Boolean(validationError)}
                      />
                      <button
                        type="button"
                        className="password-toggle-btn"
                        onClick={() => setShowRegConfirmPass(!showRegConfirmPass)}
                        aria-label={showRegConfirmPass ? 'Hide password' : 'Show password'}
                      >
                        {showRegConfirmPass ? (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* CREATE ACCOUNT BUTTON */}
                  <button type="submit" className="login-submit-btn reg-submit-btn" disabled={submitting} aria-busy={submitting}>
                    <span>{submitting ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT'}</span>
                    {!submitting && (
                      <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                      </svg>
                    )}
                  </button>
                </>
              )}

            </form>

            {/* FOOTER TOGGLE ROW */}
            <div className="register-footer-row">
              {isForgotPassword ? (
                <button type="button" className="register-link" onClick={handleSwitchToLogin} disabled={submitting}>
                  ← Back to Login
                </button>
              ) : !isRegister ? (
                <span>
                  <span className="register-prompt">Don't have an account?</span>
                  <button type="button" className="register-link" onClick={handleSwitchToRegister} disabled={submitting}>
                    Register Now
                  </button>
                </span>
              ) : (
                <span>
                  <span className="register-prompt">Already have an account?</span>
                  <button type="button" className="register-link" onClick={handleSwitchToLogin} disabled={submitting}>
                    Login
                  </button>
                </span>
              )}
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
