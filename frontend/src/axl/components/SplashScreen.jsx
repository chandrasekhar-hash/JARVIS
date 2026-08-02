import React from 'react';
import { useAXLStartup } from '../context/AXLStartupContext';
import './SplashScreen.css';

export default function SplashScreen() {
  const { progress, statusMessage } = useAXLStartup();

  return (
    <div className="splash-wrapper">
      <div className="splash-content">
        <div className="hologram-ring">
          <div className="inner-core"></div>
        </div>
        <h1 className="splash-title">J.A.R.V.I.S.</h1>
        <p className="splash-subtitle">APPLICATION EXPERIENCE LAYER v1.1.0</p>
        
        <div className="progress-bar-container">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
        </div>

        <div className="splash-status-text">
          <span className="pulse-dot"></span> {statusMessage}
        </div>
      </div>
    </div>
  );
}
