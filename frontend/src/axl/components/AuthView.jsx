import React, { useState, useRef, useEffect } from 'react';
import { useAXLAuth } from '../context/AXLAuthContext';
import { useAXLRouter, ROUTE_STATES } from '../context/AXLRouterContext';
import { fetchWithAuth } from '../services/apiInterceptor';
import JarvisParticleCanvas from './JarvisParticleCanvas';
import './AuthView.css';

// REAL BREVO OTP VERIFICATION SYSTEM FOR J.A.R.V.I.S.

const safeParseJson = async (res) => {
  try {
    const text = await res.text();
    if (!text || !text.trim()) return {};
    return JSON.parse(text);
  } catch (_) {
    return { detail: 'Server returned an invalid or empty response.' };
  }
};

const checkPasswordCriteria = (pwd) => ({
  hasMinLength: pwd.length >= 8,
  hasUppercase: /[A-Z]/.test(pwd),
  hasSpecialChar: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>?/]/.test(pwd),
});

function PasswordRequirements({ password }) {
  const { hasMinLength, hasUppercase, hasSpecialChar } = checkPasswordCriteria(password);
  return (
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
  );
}

function OtpInput({ otpDigits, setOtpDigits, onSubmit, disabled, hasError }) {
  const inputRefs = useRef([]);

  const handleChange = (index, value) => {
    const digitsOnly = value.replace(/\D/g, '');
    const digit = digitsOnly.slice(-1);

    const newDigits = [...otpDigits];
    newDigits[index] = digit;
    setOtpDigits(newDigits);

    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace') {
      if (otpDigits[index]) {
        const newDigits = [...otpDigits];
        newDigits[index] = '';
        setOtpDigits(newDigits);
      } else if (index > 0) {
        const newDigits = [...otpDigits];
        newDigits[index - 1] = '';
        setOtpDigits(newDigits);
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
    } else if (e.key === 'Enter') {
      if (otpDigits.every((d) => d !== '')) {
        onSubmit();
      }
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text');
    const numericText = pastedText.replace(/\D/g, '').slice(0, 6);
    if (!numericText) return;

    const newDigits = [...otpDigits];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = numericText[i] || '';
    }
    setOtpDigits(newDigits);

    const targetIdx = Math.min(numericText.length, 5);
    inputRefs.current[targetIdx]?.focus();
  };

  return (
    <div className="otp-boxes-container">
      {otpDigits.map((digit, idx) => (
        <input
          key={idx}
          ref={(el) => (inputRefs.current[idx] = el)}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={1}
          value={digit}
          onChange={(e) => handleChange(idx, e.target.value)}
          onKeyDown={(e) => handleKeyDown(idx, e)}
          onPaste={handlePaste}
          className={`otp-digit-box ${hasError ? 'otp-error-glow' : ''}`}
          disabled={disabled}
          autoComplete="one-time-code"
          aria-label={`Digit ${idx + 1}`}
        />
      ))}
    </div>
  );
}

export default function AuthView() {
  const { login, register } = useAXLAuth();
  const { navigateTo } = useAXLRouter();

  // Full-screen Welcome Video Intro State
  const [showWelcomeIntro, setShowWelcomeIntro] = useState(true);
  const [, setHasUserInitialized] = useState(false);
  const [isFadingInit, setIsFadingInit] = useState(false);
  const [isHoveringInitBtn, setIsHoveringInitBtn] = useState(false);

  // Audio & Greeting Refs
  const welcomeVideoRef = useRef(null);
  const welcomeAudioRef = useRef(null);
  const audioObjectUrlRef = useRef(null);
  const hasWelcomeVoicePlayedRef = useRef(false);

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
      let displayNameToSay = null;

      // 1. Check visitor hint from AXLAuthContext
      const visitorHint = localStorage.getItem('jarvis_visitor_hint');
      if (visitorHint) {
        try {
          const parsed = JSON.parse(visitorHint);
          const name = parsed.displayName || parsed.display_name || parsed.username;
          if (name && typeof name === 'string' && name.trim()) {
            displayNameToSay = name.trim();
          }
        } catch (_) {}
      }

      // 2. Fallback check for last visitor
      if (!displayNameToSay) {
        const lastVisitor = localStorage.getItem('jarvis_last_visitor');
        if (lastVisitor) {
          try {
            const parsed = JSON.parse(lastVisitor);
            const name = parsed.displayName || parsed.display_name || parsed.username;
            if (name && typeof name === 'string' && name.trim()) {
              displayNameToSay = name.trim();
            }
          } catch (_) {}
        }
      }

      const greetingText = displayNameToSay
        ? `Welcome back, ${displayNameToSay}.`
        : "Hello and welcome. JARVIS is ready for you.";

      fetchWithAuth('/tts', {
        method: 'POST',
        body: JSON.stringify({ text: greetingText }),
      })
        .then(async (res) => {
          if (!res.ok) throw new Error('Speech synthesis failed');
          return safeParseJson(res);
        })
        .then((data) => {
          if (transitionStartedRef.current) return;
          if (!data || !data.url) throw new Error('Invalid TTS response');

          const audioUrl = data.url.startsWith('http') ? data.url : `http://localhost:8000${data.url}`;
          const audio = new Audio(audioUrl);
          audio.volume = 1.0;
          welcomeAudioRef.current = audio;

          audio.onended = () => {
            welcomeAudioRef.current = null;
          };

          if (welcomeVideoRef.current && welcomeVideoRef.current.currentTime >= 1.0) {
            playWelcomeVoice();
          }
        })
        .catch((err) => {
          console.warn('[JARVIS TTS] Speech synthesis error:', err);
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

  // Step states: Reg (1..3), Forgot (1..4)
  const [regStep, setRegStep] = useState(1);
  const [forgotStep, setForgotStep] = useState(1);

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

  // Forgot password form state
  const [forgotUser, setForgotUser] = useState('');
  const [forgotPasswordNew, setForgotPasswordNew] = useState('');
  const [forgotPasswordConfirm, setForgotPasswordConfirm] = useState('');
  const [showForgotPassNew, setShowForgotPassNew] = useState(false);
  const [showForgotPassConfirm, setShowForgotPassConfirm] = useState(false);

  // OTP State
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', '']);
  const [resendTimer, setResendTimer] = useState(30);
  const [regVerificationToken, setRegVerificationToken] = useState('');
  const [forgotResetToken, setForgotResetToken] = useState('');

  // Validation & Submitting state
  const [validationError, setValidationError] = useState('');
  const [authSuccessMsg, setAuthSuccessMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isValidEmail = (email) => {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email.trim());
  };

  // Resend Countdown Effect
  useEffect(() => {
    let interval = null;
    const isOtpStep = (isRegister && regStep === 2) || (isForgotPassword && forgotStep === 2);
    if (isOtpStep && resendTimer > 0) {
      interval = setInterval(() => {
        setResendTimer((prev) => prev - 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRegister, regStep, isForgotPassword, forgotStep, resendTimer]);

  const resetOtpState = () => {
    setOtpDigits(['', '', '', '', '', '']);
    setResendTimer(30);
  };

  const handleSwitchToRegister = () => {
    setIsRegister(true);
    setIsForgotPassword(false);
    setRegStep(1);
    setValidationError('');
    setAuthSuccessMsg('');
    setLoginPass('');
    setRegUsername('');
    setRegEmail('');
    setRegPassword('');
    setRegConfirmPassword('');
    resetOtpState();
  };

  const handleSwitchToLogin = () => {
    setIsRegister(false);
    setIsForgotPassword(false);
    setRegStep(1);
    setForgotStep(1);
    setValidationError('');
    setAuthSuccessMsg('');
    setLoginPass('');
    setRegPassword('');
    setRegConfirmPassword('');
    setForgotPasswordNew('');
    setForgotPasswordConfirm('');
    resetOtpState();
  };

  const handleStartForgotPassword = () => {
    setIsForgotPassword(true);
    setIsRegister(false);
    setForgotStep(1);
    setValidationError('');
    setAuthSuccessMsg('');
    setForgotUser(loginUser.trim());
    setForgotPasswordNew('');
    setForgotPasswordConfirm('');
    setLoginPass('');
    resetOtpState();
  };

  const handleResendCode = async () => {
    if (resendTimer > 0 || submitting) return;
    setSubmitting(true);
    setValidationError('');
    setAuthSuccessMsg('');
    try {
      if (isForgotPassword) {
        const res = await fetchWithAuth('/auth/forgot-password/request-otp', {
          method: 'POST',
          body: JSON.stringify({
            identifier: forgotUser.trim(),
          }),
        });
        const data = await safeParseJson(res);
        if (!res.ok) {
          throw new Error(data.detail || 'Unable to send verification code.');
        }
        setResendTimer(30);
        setOtpDigits(['', '', '', '', '', '']);
        setAuthSuccessMsg(data.message || 'Verification code resent.');
      } else {
        const res = await fetchWithAuth('/auth/register/request-otp', {
          method: 'POST',
          body: JSON.stringify({
            username: regUsername.trim(),
            email: regEmail.trim().toLowerCase(),
          }),
        });
        const data = await safeParseJson(res);
        if (!res.ok) {
          throw new Error(data.detail || 'Unable to send verification code.');
        }
        setResendTimer(30);
        setOtpDigits(['', '', '', '', '', '']);
        setAuthSuccessMsg(data.message || `Verification code resent to ${regEmail.trim()}.`);
      }
    } catch (err) {
      setValidationError(err.message || 'Unable to send verification code.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFormSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (submitting) return;

    setValidationError('');
    setAuthSuccessMsg('');

    // --- 1. FORGOT PASSWORD FLOW ---
    if (isForgotPassword) {
      // STEP 1: RECOVER ACCOUNT
      if (forgotStep === 1) {
        if (!forgotUser.trim()) {
          setValidationError('Please enter your email or username.');
          return;
        }

        setSubmitting(true);
        try {
          const res = await fetchWithAuth('/auth/forgot-password/request-otp', {
            method: 'POST',
            body: JSON.stringify({
              identifier: forgotUser.trim(),
            }),
          });
          const data = await safeParseJson(res);
          if (!res.ok) {
            throw new Error(data.detail || 'Unable to process account recovery. Please try again.');
          }
          resetOtpState();
          setAuthSuccessMsg(data.message || 'A verification code has been sent.');
          setForgotStep(2);
        } catch (err) {
          setValidationError(err.message || 'Unable to process account recovery. Please try again.');
        } finally {
          setSubmitting(false);
        }
        return;
      }

      // STEP 2: VERIFY IDENTITY (OTP)
      if (forgotStep === 2) {
        const code = otpDigits.join('');
        if (code.length < 6) {
          setValidationError('Please enter all 6 digits.');
          return;
        }

        setSubmitting(true);
        try {
          const res = await fetchWithAuth('/auth/forgot-password/verify-otp', {
            method: 'POST',
            body: JSON.stringify({
              identifier: forgotUser.trim(),
              otp: code,
            }),
          });
          const data = await safeParseJson(res);
          if (!res.ok) {
            throw new Error(data.detail || 'Invalid verification code.');
          }
          setForgotResetToken(data.reset_token);
          setValidationError('');
          setAuthSuccessMsg('');
          setForgotStep(3);
        } catch (err) {
          setValidationError(err.message || 'Invalid verification code.');
        } finally {
          setSubmitting(false);
        }
        return;
      }

      // STEP 3: CREATE NEW PASSWORD
      if (forgotStep === 3) {
        if (!forgotPasswordNew || !forgotPasswordConfirm) {
          setValidationError('Please enter and confirm your new password.');
          return;
        }

        const { hasMinLength, hasUppercase, hasSpecialChar } = checkPasswordCriteria(forgotPasswordNew);
        if (!hasMinLength || !hasUppercase || !hasSpecialChar) {
          setValidationError('Password does not meet the security requirements.');
          return;
        }

        if (forgotPasswordNew !== forgotPasswordConfirm) {
          setValidationError('Passwords do not match.');
          return;
        }

        setSubmitting(true);
        try {
          const res = await fetchWithAuth('/auth/forgot-password/reset-password', {
            method: 'POST',
            body: JSON.stringify({
              identifier: forgotUser.trim(),
              reset_token: forgotResetToken,
              new_password: forgotPasswordNew,
            }),
          });
          const data = await safeParseJson(res);
          if (!res.ok) {
            throw new Error(data.detail || 'Password reset failed.');
          }
          setValidationError('');
          setAuthSuccessMsg(data.message || 'Your password has been updated successfully. Please log in.');
          setForgotStep(4);
        } catch (err) {
          setValidationError(err.message || 'Password reset failed.');
        } finally {
          setSubmitting(false);
        }
        return;
      }

      // STEP 4: PASSWORD UPDATED -> RETURN TO LOGIN
      if (forgotStep === 4) {
        setIsForgotPassword(false);
        setForgotStep(1);
        setLoginUser(forgotUser.trim());
        setLoginPass('');
        setAuthSuccessMsg('Your password has been updated successfully. Please log in.');
        setForgotPasswordNew('');
        setForgotPasswordConfirm('');
        setForgotResetToken('');
        resetOtpState();
        return;
      }
    }

    // --- 2. REGISTER FLOW ---
    if (isRegister) {
      // STEP 1: ACCOUNT DETAILS
      if (regStep === 1) {
        if (!regUsername.trim() || !regEmail.trim()) {
          setValidationError('Please fill in all required fields.');
          return;
        }
        if (!isValidEmail(regEmail)) {
          setValidationError('Enter a valid email address.');
          return;
        }

        setSubmitting(true);
        try {
          const res = await fetchWithAuth('/auth/register/request-otp', {
            method: 'POST',
            body: JSON.stringify({
              username: regUsername.trim(),
              email: regEmail.trim().toLowerCase(),
            }),
          });
          const data = await safeParseJson(res);
          if (!res.ok) {
            throw new Error(data.detail || 'Unable to send verification code. Please try again.');
          }
          resetOtpState();
          setAuthSuccessMsg(data.message || `Verification code sent to ${regEmail.trim()}.`);
          setRegStep(2);
        } catch (err) {
          setValidationError(err.message || 'Unable to send verification code. Please try again.');
        } finally {
          setSubmitting(false);
        }
        return;
      }

      // STEP 2: VERIFY EMAIL (OTP)
      if (regStep === 2) {
        const code = otpDigits.join('');
        if (code.length < 6) {
          setValidationError('Please enter all 6 digits.');
          return;
        }

        setSubmitting(true);
        try {
          const res = await fetchWithAuth('/auth/register/verify-otp', {
            method: 'POST',
            body: JSON.stringify({
              email: regEmail.trim().toLowerCase(),
              otp: code,
            }),
          });
          const data = await safeParseJson(res);
          if (!res.ok) {
            throw new Error(data.detail || 'Invalid verification code.');
          }
          setRegVerificationToken(data.verification_token);
          setValidationError('');
          setAuthSuccessMsg('');
          setRegStep(3);
        } catch (err) {
          setValidationError(err.message || 'Invalid verification code.');
        } finally {
          setSubmitting(false);
        }
        return;
      }

      // STEP 3: CREATE PASSWORD
      if (regStep === 3) {
        if (!regPassword || !regConfirmPassword) {
          setValidationError('Please fill in all required fields.');
          return;
        }

        const { hasMinLength, hasUppercase, hasSpecialChar } = checkPasswordCriteria(regPassword);
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
          const res = await fetchWithAuth('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
              username: regUsername.trim(),
              email: regEmail.trim().toLowerCase(),
              password: regPassword,
              verification_token: regVerificationToken,
            }),
          });
          const data = await safeParseJson(res);
          if (!res.ok) {
            throw new Error(data.detail || 'Account creation failed.');
          }

          setLoginUser(regUsername.trim());
          setIsRegister(false);
          setRegStep(1);
          setAuthSuccessMsg('Account created successfully. Please log in.');
          setLoginPass('');
          setRegPassword('');
          setRegConfirmPassword('');
          setRegVerificationToken('');
          resetOtpState();
        } catch (err) {
          setValidationError(err.message || 'Account creation failed.');
        } finally {
          setSubmitting(false);
        }
        return;
      }
    }

    // --- 3. LOGIN MODE ---
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

                <div key="login-intro" className="auth-form-animated-wrapper">
                  <div className="auth-section-header">
                    <h2 className="login-title">LOGIN</h2>
                    <p className="login-desc">Enter your credentials to access your system.</p>
                  </div>

                  <form className="auth-form" onSubmit={handleFormSubmit}>
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
          {!isTransitioningToLogin && (
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

      {/* RIGHT 50% PANEL — LOGIN / REGISTER / RECOVERY INTERFACE */}
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
          <div
            key={isForgotPassword ? `forgot-${forgotStep}` : isRegister ? `reg-${regStep}` : 'login'}
            className="auth-form-animated-wrapper"
          >
            
            {/* SECTION HEADER */}
            <div className="auth-section-header">
              <h2 className="login-title">
                {isForgotPassword ? (
                  forgotStep === 1 ? 'RECOVER ACCOUNT' :
                  forgotStep === 2 ? 'VERIFY YOUR IDENTITY' :
                  forgotStep === 3 ? 'CREATE NEW PASSWORD' :
                  'PASSWORD UPDATED'
                ) : isRegister ? (
                  regStep === 1 ? 'CREATE ACCOUNT' :
                  regStep === 2 ? 'VERIFY YOUR EMAIL' :
                  'CREATE PASSWORD'
                ) : (
                  'LOGIN'
                )}
              </h2>
              <p className="login-desc">
                {isForgotPassword ? (
                  forgotStep === 1 ? 'Enter your details to begin recovery.' :
                  forgotStep === 2 ? 'Enter the 6-digit verification code sent to the email associated with your account.' :
                  forgotStep === 3 ? 'Enter a new password for your account.' :
                  'Your password has been updated successfully.'
                ) : isRegister ? (
                  regStep === 1 ? 'Enter your details to create a new JARVIS account.' :
                  regStep === 2 ? (
                    <>
                      Enter the 6-digit verification code sent to{' '}
                      <span className="highlight-email">{regEmail}</span>
                    </>
                  ) : (
                    'Set a secure password for your account.'
                  )
                ) : (
                  'Enter your credentials to access your system.'
                )}
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
            <form className="auth-form" onSubmit={handleFormSubmit}>

              {/* ==================== LOGIN MODE ==================== */}
              {!isForgotPassword && !isRegister && (
                <>
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
                  {/* STEP 1: ACCOUNT DETAILS */}
                  {regStep === 1 && (
                    <>
                      <div className="form-group">
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

                      <div className="form-group">
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

                      <button type="submit" className="login-submit-btn" disabled={submitting}>
                        <span>CONTINUE</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"></line>
                          <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                      </button>
                    </>
                  )}

                  {/* STEP 2: VERIFY EMAIL (OTP) */}
                  {regStep === 2 && (
                    <>

                      <OtpInput
                        otpDigits={otpDigits}
                        setOtpDigits={setOtpDigits}
                        onSubmit={() => handleFormSubmit()}
                        disabled={submitting}
                        hasError={Boolean(validationError)}
                      />

                      <div className="otp-actions-container">
                        <div className="otp-resend-row">
                          <span>Didn't receive the code?</span>
                          <button
                            type="button"
                            className="resend-code-btn"
                            onClick={handleResendCode}
                            disabled={resendTimer > 0}
                          >
                            RESEND CODE {resendTimer > 0 ? `(${resendTimer}s)` : ''}
                          </button>
                        </div>
                        <button
                          type="button"
                          className="otp-back-btn"
                          onClick={() => {
                            setValidationError('');
                            setRegStep(1);
                          }}
                        >
                          ← CHANGE EMAIL
                        </button>
                      </div>

                      <button type="submit" className="login-submit-btn" disabled={submitting}>
                        <span>VERIFY CODE</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"></line>
                          <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                      </button>
                    </>
                  )}

                  {/* STEP 3: CREATE PASSWORD */}
                  {regStep === 3 && (
                    <>
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

                      <PasswordRequirements password={regPassword} />

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

                      <button type="submit" className="login-submit-btn reg-submit-btn" disabled={submitting}>
                        <span>CREATE ACCOUNT</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"></line>
                          <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                      </button>
                    </>
                  )}
                </>
              )}

              {/* ==================== FORGOT PASSWORD MODE ==================== */}
              {isForgotPassword && (
                <>
                  {/* STEP 1: RECOVER ACCOUNT */}
                  {forgotStep === 1 && (
                    <>
                      <div className="form-group">
                        <div className="input-wrapper">
                          <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                            <circle cx="12" cy="7" r="4"></circle>
                          </svg>
                          <input
                            type="text"
                            value={forgotUser}
                            onChange={(e) => setForgotUser(e.target.value)}
                            placeholder="Email / Username"
                            autoComplete="off"
                            disabled={submitting}
                            aria-invalid={Boolean(validationError)}
                          />
                        </div>
                      </div>

                      <button type="submit" className="login-submit-btn" disabled={submitting}>
                        <span>CONTINUE</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"></line>
                          <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                      </button>
                    </>
                  )}

                  {/* STEP 2: VERIFY YOUR IDENTITY (OTP) */}
                  {forgotStep === 2 && (
                    <>
                      <OtpInput
                        otpDigits={otpDigits}
                        setOtpDigits={setOtpDigits}
                        onSubmit={() => handleFormSubmit()}
                        disabled={submitting}
                        hasError={Boolean(validationError)}
                      />

                      <div className="otp-actions-container">
                        <div className="otp-resend-row">
                          <button
                            type="button"
                            className="resend-code-btn"
                            onClick={handleResendCode}
                            disabled={resendTimer > 0}
                          >
                            RESEND CODE {resendTimer > 0 ? `(${resendTimer}s)` : ''}
                          </button>
                        </div>
                        <button
                          type="button"
                          className="otp-back-btn"
                          onClick={() => {
                            setValidationError('');
                            setForgotStep(1);
                          }}
                        >
                          ← BACK
                        </button>
                      </div>

                      <button type="submit" className="login-submit-btn" disabled={submitting}>
                        <span>VERIFY CODE</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"></line>
                          <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                      </button>
                    </>
                  )}

                  {/* STEP 3: CREATE NEW PASSWORD */}
                  {forgotStep === 3 && (
                    <>
                      <div className="form-group form-group-dense">
                        <div className="input-wrapper">
                          <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                          </svg>
                          <input
                            type={showForgotPassNew ? 'text' : 'password'}
                            value={forgotPasswordNew}
                            onChange={(e) => {
                              setForgotPasswordNew(e.target.value);
                              if (validationError === 'Password does not meet the security requirements.') setValidationError('');
                              if (forgotPasswordConfirm && e.target.value === forgotPasswordConfirm && validationError === 'Passwords do not match.') setValidationError('');
                            }}
                            placeholder="New Password"
                            autoComplete="off"
                            disabled={submitting}
                            aria-invalid={Boolean(validationError)}
                          />
                          <button
                            type="button"
                            className="password-toggle-btn"
                            onClick={() => setShowForgotPassNew(!showForgotPassNew)}
                            aria-label={showForgotPassNew ? 'Hide password' : 'Show password'}
                          >
                            {showForgotPassNew ? (
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

                      <PasswordRequirements password={forgotPasswordNew} />

                      <div className="form-group form-group-dense">
                        <div className="input-wrapper">
                          <svg className="input-icon-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                          </svg>
                          <input
                            type={showForgotPassConfirm ? 'text' : 'password'}
                            value={forgotPasswordConfirm}
                            onChange={(e) => {
                              setForgotPasswordConfirm(e.target.value);
                              if (forgotPasswordNew && e.target.value === forgotPasswordNew && validationError === 'Passwords do not match.') {
                                setValidationError('');
                              } else if (forgotPasswordNew && e.target.value !== forgotPasswordNew) {
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
                            onClick={() => setShowForgotPassConfirm(!showForgotPassConfirm)}
                            aria-label={showForgotPassConfirm ? 'Hide password' : 'Show password'}
                          >
                            {showForgotPassConfirm ? (
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

                      <button type="submit" className="login-submit-btn" disabled={submitting}>
                        <span>RESET PASSWORD</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="5" y1="12" x2="19" y2="12"></line>
                          <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                      </button>
                    </>
                  )}

                  {/* STEP 4: PASSWORD UPDATED */}
                  {forgotStep === 4 && (
                    <>
                      <div className="recovery-success-box">
                        <svg className="success-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                          <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                        <p className="success-text">Your password has been updated successfully.</p>
                      </div>

                      <button
                        type="button"
                        className="login-submit-btn"
                        onClick={handleFormSubmit}
                        disabled={submitting}
                      >
                        <span>RETURN TO LOGIN</span>
                      </button>
                    </>
                  )}
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

