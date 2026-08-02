import React, { useState, useEffect } from 'react';
import { useAXLRouter } from '../context/AXLRouterContext';
import { useAXLStartup } from '../context/AXLStartupContext';
import './MaintenanceView.css';

export default function MaintenanceView() {
  const { maintenanceInfo } = useAXLRouter();
  const { retryBoot } = useAXLStartup();
  const [countdown, setCountdown] = useState((maintenanceInfo?.estimated_recovery_minutes || 5) * 60);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="maintenance-wrapper">
      <div className="maintenance-card">
        <div className="maintenance-icon">⚙️</div>
        <h2>SYSTEM MAINTENANCE</h2>
        <p className="maintenance-msg">{maintenanceInfo?.message || 'JARVIS is currently performing scheduled database optimization.'}</p>
        
        <div className="countdown-box">
          <span className="countdown-label">ESTIMATED RECOVERY</span>
          <span className="countdown-value">{formatTime(countdown)}</span>
        </div>

        <button className="maintenance-retry-btn" onClick={retryBoot}>RETRY CONNECTION NOW</button>
      </div>
    </div>
  );
}
