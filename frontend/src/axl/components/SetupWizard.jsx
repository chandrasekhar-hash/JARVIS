import React, { useState } from 'react';
import { useAXLAuth } from '../context/AXLAuthContext';
import { useAXLRouter, ROUTE_STATES } from '../context/AXLRouterContext';
import './SetupWizard.css';

export default function SetupWizard() {
  const { register } = useAXLAuth();
  const { navigateTo } = useAXLRouter();
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('Commander');
  const [groqKey, setGroqKey] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleComplete = async () => {
    setSubmitting(true);
    try {
      if (password) {
        await register(username, password, displayName);
      }
      localStorage.setItem('jarvis-setup-completed', 'true');
      navigateTo(ROUTE_STATES.AUTHENTICATED);
    } catch (e) {
      alert(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="wizard-wrapper">
      <div className="wizard-card">
        <div className="wizard-progress">
          <div className={`step-dot ${step >= 1 ? 'active' : ''}`}>1</div>
          <div className="step-line"></div>
          <div className={`step-dot ${step >= 2 ? 'active' : ''}`}>2</div>
          <div className="step-line"></div>
          <div className={`step-dot ${step >= 3 ? 'active' : ''}`}>3</div>
        </div>

        {step === 1 && (
          <div className="wizard-step">
            <h2>Welcome to J.A.R.V.I.S.</h2>
            <p>Initializing Application Experience Layer (AXL). Let's configure your master administrator profile.</p>
            <div className="form-group">
              <label>Master Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Master Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Choose a strong password..." required />
            </div>
            <button className="wizard-btn" onClick={() => setStep(2)} disabled={!password}>Continue to API Keys →</button>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-step">
            <h2>API Intelligence Keys</h2>
            <p>Configure primary LLM provider access (optional, defaults saved in env).</p>
            <div className="form-group">
              <label>Groq API Key (Optional)</label>
              <input type="password" value={groqKey} onChange={e => setGroqKey(e.target.value)} placeholder="gsk_..." />
            </div>
            <div className="wizard-btn-row">
              <button className="wizard-btn-secondary" onClick={() => setStep(1)}>Back</button>
              <button className="wizard-btn" onClick={() => setStep(3)}>Continue to Preferences →</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-step">
            <h2>System Ready</h2>
            <p>Your identity profile and environment setup are complete. Click below to launch JARVIS.</p>
            <div className="wizard-btn-row">
              <button className="wizard-btn-secondary" onClick={() => setStep(2)}>Back</button>
              <button className="wizard-btn" onClick={handleComplete} disabled={submitting}>
                {submitting ? 'LAUNCHING...' : 'INITIALIZE DASHBOARD'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
