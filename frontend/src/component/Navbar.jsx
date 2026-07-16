import React, { useState, useEffect, useRef } from 'react';
import { useAssistantConfig } from '../context/AssistantConfigContext';
import './Navbar.css';

export default function Navbar({
  blobColor,
  setBlobColor,
  blobSize,
  setBlobSize,
  isDraggable,
  setIsDraggable,
  blobPosition,
  setBlobPosition,
  jarvisFont,
  setJarvisFont,
  jarvisColor,
  setJarvisColor,
  jarvisFontSize,
  setJarvisFontSize,
  jarvisTextPosition,
  setJarvisTextPosition,
  isTextDraggable,
  setIsTextDraggable,
  blobSensitivity,
  setBlobSensitivity,
  terminalSettings,
  setTerminalSettings
}) {
  const { 
    assistantName, 
    updateAssistantName, 
    wakeWordRequired, 
    setWakeWordRequired, 
    statusSettings, 
    updateStatusSetting, 
    envWidgetSettings,
    updateEnvWidgetSetting,
    connWidgetSettings,
    updateConnWidgetSetting,
    visualizerMode, 
    setVisualizerMode,
    voiceGender,
    updateVoiceGender,
    creator,
    updateCreator,
    voiceLanguage,
    updateVoiceLanguage
  } = useAssistantConfig();
  const [activeIndex, setActiveIndex] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isBlobSectionOpen, setIsBlobSectionOpen] = useState(true);
  const [isJarvisSectionOpen, setIsJarvisSectionOpen] = useState(true);
  const [isInterfaceSectionOpen, setIsInterfaceSectionOpen] = useState(true);
  const [isTerminalSectionOpen, setIsTerminalSectionOpen] = useState(false);
  const [isStatusSectionOpen, setIsStatusSectionOpen] = useState(false);
  const [isEnvSectionOpen, setIsEnvSectionOpen] = useState(false);
  const [isConnSectionOpen, setIsConnSectionOpen] = useState(false);
  const [isVoiceSectionOpen, setIsVoiceSectionOpen] = useState(true);
  const [settingsTheme, setSettingsTheme] = useState(() => {
    return localStorage.getItem('jarvis-settings-theme') || 'dark';
  });

  // Env widget position state
  const [envPos, setEnvPos] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis-widget-env-pos');
      return saved ? JSON.parse(saved) : { x: 24, y: 110 };
    } catch { return { x: 24, y: 110 }; }
  });
  const [isDraggingEnvMap, setIsDraggingEnvMap] = useState(false);
  const envMapRef = useRef(null);

  const setEnvPosAndSync = (newPos) => {
    setEnvPos(newPos);
    localStorage.setItem('jarvis-widget-env-pos', JSON.stringify(newPos));
    window.dispatchEvent(new CustomEvent('jarvis-env-pos-change', { detail: newPos }));
  };

  // Conn widget position state
  const [connPos, setConnPos] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis-widget-conn-pos');
      return saved ? JSON.parse(saved) : { x: 24, y: 395 };
    } catch { return { x: 24, y: 395 }; }
  });
  const [isDraggingConnMap, setIsDraggingConnMap] = useState(false);
  const connMapRef = useRef(null);

  const setConnPosAndSync = (newPos) => {
    setConnPos(newPos);
    localStorage.setItem('jarvis-widget-conn-pos', JSON.stringify(newPos));
    window.dispatchEvent(new CustomEvent('jarvis-conn-pos-change', { detail: newPos }));
  };

  const navbarRef = useRef(null);
  const settingsPanelRef = useRef(null);
  const settingsRectRef = useRef(null);

  const handleSettingsMouseEnter = () => {
    if (settingsPanelRef.current) {
      settingsRectRef.current = settingsPanelRef.current.getBoundingClientRect();
    }
  };

  const handleSettingsMouseMove = (e) => {
    if (settingsPanelRef.current) {
      if (!settingsRectRef.current) {
        settingsRectRef.current = settingsPanelRef.current.getBoundingClientRect();
      }
      const rect = settingsRectRef.current;
      
      // Calculate cursor position relative to panel center
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      
      // Convert to rotation angles (max 6 degrees tilt for realistic weight)
      const rx = -(y / (rect.height / 2)) * 6;
      const ry = (x / (rect.width / 2)) * 6;
      
      settingsPanelRef.current.style.setProperty('--rx', `${rx}deg`);
      settingsPanelRef.current.style.setProperty('--ry', `${ry}deg`);
      
      // Calculate specular shine light position
      const mx = ((e.clientX - rect.left) / rect.width) * 100;
      const my = ((e.clientY - rect.top) / rect.height) * 100;
      settingsPanelRef.current.style.setProperty('--mx', `${mx}%`);
      settingsPanelRef.current.style.setProperty('--my', `${my}%`);
    }
  };

  const handleSettingsMouseLeave = () => {
    if (settingsPanelRef.current) {
      const panel = settingsPanelRef.current;
      panel.style.setProperty('--rx', '0deg');
      panel.style.setProperty('--ry', '0deg');
      panel.style.setProperty('--mx', '50%');
      panel.style.setProperty('--my', '50%');
    }
    settingsRectRef.current = null;
  };

  const menuItems = [
    { label: 'Home', path: '#' },
    { label: 'Features', path: '#features' },
    { label: 'Core', path: '#core' },
    { label: 'Sandbox', path: '#sandbox' },
    { label: 'Docs', path: '#docs' }
  ];

  // Helper colors utilities
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  };

  const rgbToHex = (r, g, b) => {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  };

  const generateColorsFromPrimary = (hexColor) => {
    const rgb = hexToRgb(hexColor);
    if (!rgb) return;
    const deep = rgbToHex(Math.floor(rgb.r * 0.08), Math.floor(rgb.g * 0.08), Math.floor(rgb.b * 0.2));
    const mid = rgbToHex(Math.floor(rgb.r * 0.5), Math.floor(rgb.g * 0.6), Math.floor(rgb.b * 0.9));
    const shell = rgbToHex(Math.floor(rgb.r * 0.3), Math.floor(rgb.g * 0.4), Math.floor(rgb.b * 0.9));
    const newColor = { name: 'Custom', deep, mid, bright: hexColor, shell };
    setBlobColor(newColor);
    localStorage.setItem('jarvis-blob-color', JSON.stringify(newColor));
  };

  const handleSavePosition = () => {
    if (blobPosition) {
      localStorage.setItem('jarvis-blob-position', JSON.stringify(blobPosition));
      setIsDraggable(false);
      showToast("Position saved!");
    }
  };

  const handleResetPosition = () => {
    localStorage.removeItem('jarvis-blob-position');
    const defaultPos = {
      x: window.innerWidth - blobSize - 20,
      y: window.innerHeight - blobSize - 20
    };
    setBlobPosition(defaultPos);
    setIsDraggable(false);
    showToast("Position reset!");
  };

  const applyPresetPosition = (preset) => {
    let x = 20;
    let y = 20;
    const margin = 20;

    switch (preset) {
      case 'top-left':
        x = margin;
        y = margin;
        break;
      case 'top-center':
        x = (window.innerWidth - blobSize) / 2;
        y = margin;
        break;
      case 'top-right':
        x = window.innerWidth - blobSize - margin;
        y = margin;
        break;
      case 'mid-left':
        x = margin;
        y = (window.innerHeight - blobSize) / 2;
        break;
      case 'center':
        x = (window.innerWidth - blobSize) / 2;
        y = (window.innerHeight - blobSize) / 2;
        break;
      case 'mid-right':
        x = window.innerWidth - blobSize - margin;
        y = (window.innerHeight - blobSize) / 2;
        break;
      case 'bottom-left':
        x = margin;
        y = window.innerHeight - blobSize - margin;
        break;
      case 'bottom-center':
        x = (window.innerWidth - blobSize) / 2;
        y = window.innerHeight - blobSize - margin;
        break;
      case 'bottom-right':
        x = window.innerWidth - blobSize - margin;
        y = window.innerHeight - blobSize - margin;
        break;
      default:
        return;
    }

    // Ensure within viewport boundaries
    x = Math.max(margin, Math.min(window.innerWidth - blobSize - margin, x));
    y = Math.max(margin, Math.min(window.innerHeight - blobSize - margin, y));

    const newPos = { x, y };
    setBlobPosition(newPos);
    localStorage.setItem('jarvis-blob-position', JSON.stringify(newPos));
    showToast(`Position set to ${preset.replace('-', ' ')}`);
  };

  const updateTerminalSetting = (key, value) => {
    setTerminalSettings(prev => {
      const updated = { ...prev, [key]: value };
      localStorage.setItem('jarvis-terminal-settings', JSON.stringify(updated));
      return updated;
    });
  };

  const handleSaveTextPosition = () => {
    if (jarvisTextPosition) {
      localStorage.setItem('jarvis-text-position', JSON.stringify(jarvisTextPosition));
      setIsTextDraggable(false);
      showToast("Text Position saved!");
    }
  };

  const handleResetTextPosition = () => {
    localStorage.removeItem('jarvis-text-position');
    setJarvisTextPosition(null);
    setIsTextDraggable(false);
    showToast("Text Position reset!");
  };

  const toastTimerRef = useRef(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToastMessage(''), 2000);
  };

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const navbarRectRef = useRef(null);

  const handleNavbarMouseEnter = () => {
    if (navbarRef.current) {
      navbarRectRef.current = navbarRef.current.getBoundingClientRect();
    }
  };

  const handleMouseMove = (e) => {
    if (navbarRef.current) {
      if (!navbarRectRef.current) {
        navbarRectRef.current = navbarRef.current.getBoundingClientRect();
      }
      const rect = navbarRectRef.current;
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      navbarRef.current.style.setProperty('--mouse-x', `${x}%`);
      navbarRef.current.style.setProperty('--mouse-y', `${y}%`);
    }
  };

  const handleNavbarMouseLeave = () => {
    navbarRectRef.current = null;
  };

  const handleLinkClick = (e, index) => {
    setActiveIndex(index);
    setMobileOpen(false);
    // Smooth scroll for hash links
    const targetId = menuItems[index].path;
    if (targetId.startsWith('#') && targetId.length > 1) {
      e.preventDefault();
      const element = document.getElementById(targetId.substring(1));
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <div className="navbar-container">
      <nav 
        ref={navbarRef}
        className="navbar" 
        onMouseEnter={handleNavbarMouseEnter}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleNavbarMouseLeave}
      >
        {/* Brand / Logo */}
        <a href="#" className="nav-logo" onClick={(e) => handleLinkClick(e, 0)}>
          <div className="logo-glow-dot"></div>
          <span className="logo-text">{assistantName}</span>
        </a>

        {/* Nav Links */}
        <ul className={`nav-links ${mobileOpen ? 'mobile-open' : ''}`}>
          {menuItems.map((item, idx) => (
            <li 
              key={item.label}
              className="nav-item"
            >
              <a
                href={item.path}
                className={`nav-link ${activeIndex === idx ? 'active' : ''}`}
                onClick={(e) => handleLinkClick(e, idx)}
              >
                {item.label}
              </a>
            </li>
          ))}
        </ul>

        {/* Actions (Launch App & Settings) */}
        <div className="nav-actions">
          <button 
            className={`btn-settings ${showSettings ? 'active' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
            aria-label="Toggle blob settings"
            title="Customize Blob settings"
          >
            <div className="settings-btn-glow"></div>
            <svg 
              className="reactor-svg"
              width="20" 
              height="20" 
              viewBox="0 0 100 100" 
              fill="none" 
            >
              {/* Outer dashed ring */}
              <circle className="ring-outer" cx="50" cy="50" r="42" stroke="currentColor" strokeWidth="3" strokeDasharray="10 8" />
              {/* Mid solid ring with gap */}
              <circle className="ring-mid" cx="50" cy="50" r="30" stroke="currentColor" strokeWidth="4.5" strokeDasharray="120 40" />
              {/* Inner details */}
              <circle className="ring-inner" cx="50" cy="50" r="18" stroke="currentColor" strokeWidth="3" strokeDasharray="14 7" />
              {/* Center core */}
              <circle className="core-dot" cx="50" cy="50" r="8" fill="currentColor" />
              {/* Core radiating lines */}
              <line x1="50" y1="6" x2="50" y2="18" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              <line x1="50" y1="82" x2="50" y2="94" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              <line x1="6" y1="50" x2="18" y2="50" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              <line x1="82" y1="50" x2="94" y2="50" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </button>
          
          <button className="btn-launch">
            <span>Launch Console</span>
            <svg 
              width="14" 
              height="14" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2.5" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            >
              <line x1="5" y1="12" x2="19" y2="12"></line>
              <polyline points="12 5 19 12 12 19"></polyline>
            </svg>
          </button>
          
          {/* Mobile hamburger menu toggle */}
          <button 
            className={`mobile-toggle ${mobileOpen ? 'open' : ''}`} 
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle navigation menu"
          >
            <span className="hamburger-line"></span>
            <span className="hamburger-line"></span>
            <span className="hamburger-line"></span>
          </button>
        </div>
      </nav>

      {/* Dropdown Settings Panel */}
      {showSettings && (
        <div 
          ref={settingsPanelRef}
          className={`settings-dropdown theme-${settingsTheme}`}
          onMouseEnter={handleSettingsMouseEnter}
          onMouseMove={handleSettingsMouseMove}
          onMouseLeave={handleSettingsMouseLeave}
        >
          {/* HUD futuristic elements */}
          <div className="hud-corner-bracket top-left"></div>
          <div className="hud-corner-bracket top-right"></div>
          <div className="hud-corner-bracket bottom-left"></div>
          <div className="hud-corner-bracket bottom-right"></div>
          <div className="hud-scan-line"></div>

          <div className="settings-header">
            <div className="settings-header-title">
              <span className="glow-dot"></span>
              <h3>Neural Core settings</h3>
            </div>
            <button className="btn-close-settings" onClick={() => setShowSettings(false)}>×</button>
          </div>

          <div className="settings-columns-container">
            {/* COLUMN 1: BLOB SETTINGS */}
            <div className={`settings-column ${isBlobSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsBlobSectionOpen(!isBlobSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-01</span>
                  <h4>Blob Settings</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isBlobSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isBlobSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isBlobSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                <div className="settings-section">
                  <label className="section-label">1. Blob Theme Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <span className="picker-label" style={{ fontSize: '13px', color: 'var(--text)' }}>Choose Color:</span>
                    <input
                      type="color"
                      value={blobColor.bright}
                      onChange={(e) => generateColorsFromPrimary(e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {blobColor.bright.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="settings-section">
                  <div className="section-label-row">
                    <label className="section-label">2. Blob Size</label>
                    <span className="size-value-display">{blobSize}px</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="500"
                    step="10"
                    value={blobSize}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setBlobSize(val);
                      localStorage.setItem('jarvis-blob-size', val);
                    }}
                    className="size-slider-input"
                  />
                </div>

                <div className="settings-section">
                  <div className="section-label-row">
                    <label className="section-label">3. Reaction Sensitivity</label>
                    <span className="size-value-display">{blobSensitivity}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="10.0"
                    step="0.1"
                    value={blobSensitivity}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setBlobSensitivity(val);
                      localStorage.setItem('jarvis-blob-sensitivity', val);
                    }}
                    className="size-slider-input"
                  />
                </div>

                <div className="settings-section">
                  <label className="section-label">4. Blob Position</label>
                  <div className="drag-action-row">
                    <button
                      className={`btn-drag-toggle ${!isDraggable ? 'active' : ''}`}
                      onClick={() => setIsDraggable(!isDraggable)}
                    >
                      {isDraggable ? '🔓 Drag Enabled — Click to Lock' : '🔒 Drag Locked — Click to Unlock'}
                    </button>
                    {isDraggable && (
                      <button className="btn-save-pos" onClick={handleSavePosition}>
                        Save Position
                      </button>
                    )}
                  </div>
                  <div className="drag-reset-row" style={{ marginTop: '10px' }}>
                    <button className="btn-reset-pos" onClick={handleResetPosition}>
                      Reset to Default
                    </button>
                  </div>
                  
                  {/* Preset Position Select Dropdown */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
                    <label className="section-label">Position Presets</label>
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        const preset = e.target.value;
                        if (preset) {
                          applyPresetPosition(preset);
                          e.target.value = ""; // reset selection
                        }
                      }}
                      style={{
                        background: settingsTheme === 'light' ? 'rgba(255, 255, 255, 0.95)' : 'rgba(10, 12, 16, 0.95)',
                        border: settingsTheme === 'light' ? '1px solid rgba(0, 0, 0, 0.15)' : '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '10px',
                        color: settingsTheme === 'light' ? '#000' : '#fff',
                        padding: '8px 12px',
                        fontSize: '13px',
                        outline: 'none',
                        cursor: 'pointer',
                        width: '100%',
                        boxSizing: 'border-box'
                      }}
                    >
                      <option value="" disabled>Select screen preset...</option>
                      <option value="top-left">Top Left</option>
                      <option value="top-center">Top Center</option>
                      <option value="top-right">Top Right</option>
                      <option value="mid-left">Middle Left</option>
                      <option value="center">Middle / Center</option>
                      <option value="mid-right">Middle Right</option>
                      <option value="bottom-left">Bottom Left</option>
                      <option value="bottom-center">Bottom Center</option>
                      <option value="bottom-right">Bottom Right</option>
                    </select>
                  </div>
                </div>

                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0' }}>
                  <label className="section-label">5. Visualizer Input Mode</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
                    <select
                      value={visualizerMode}
                      onChange={(e) => {
                        setVisualizerMode(e.target.value);
                        showToast(`Visualizer: ${e.target.value.toUpperCase()}`);
                      }}
                      style={{
                        background: settingsTheme === 'light' ? 'rgba(255, 255, 255, 0.95)' : 'rgba(10, 12, 16, 0.95)',
                        border: settingsTheme === 'light' ? '1px solid rgba(0, 0, 0, 0.15)' : '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '10px',
                        color: settingsTheme === 'light' ? '#000' : '#fff',
                        padding: '8px 12px',
                        fontSize: '13px',
                        outline: 'none',
                        cursor: 'pointer',
                        width: '100%',
                        boxSizing: 'border-box'
                      }}
                    >
                      <option value="real">🎙️ Real Microphone Input</option>
                      <option value="simulated">💻 Simulated Input (OBS / YouTube Mode)</option>
                    </select>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', fontFamily: 'var(--mono)', lineHeight: '1.4' }}>
                      Select <b>Simulated</b> if recording for YouTube/OBS to avoid microphone sharing conflicts.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 2: JARVIS CUSTOMIZATION */}
            <div className={`settings-column ${isJarvisSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsJarvisSectionOpen(!isJarvisSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-02</span>
                  <h4>{assistantName} Customization</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isJarvisSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isJarvisSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isJarvisSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                <div className="settings-section">
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>1. Assistant Name</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                    <input
                      type="text"
                      value={assistantName}
                      onChange={(e) => updateAssistantName(e.target.value)}
                      placeholder="Enter text..."
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.15)',
                        borderRadius: '10px',
                        color: '#fff',
                        padding: '8px 12px',
                        fontSize: '13px',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>2. Creator Profile</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                    <input
                      type="text"
                      value={creator}
                      onChange={(e) => updateCreator(e.target.value)}
                      placeholder="Enter creator name..."
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.15)',
                        borderRadius: '10px',
                        color: '#fff',
                        padding: '8px 12px',
                        fontSize: '13px',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>3. Wake Word Settings</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#fff', fontSize: '13px' }}>
                      <input
                        type="checkbox"
                        checked={wakeWordRequired}
                        onChange={(e) => setWakeWordRequired(e.target.checked)}
                        style={{ cursor: 'pointer', width: '15px', height: '15px' }}
                      />
                      <span>Wake Word Required</span>
                    </label>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', fontFamily: 'var(--mono)', lineHeight: '1.4' }}>
                      If ON, commands only execute when prefixed with a wake word (e.g. "{assistantName.toLowerCase()}").
                    </div>
                  </div>

                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>4. Font Styling</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                    <select
                      value={jarvisFont}
                      onChange={(e) => {
                        setJarvisFont(e.target.value);
                        localStorage.setItem('jarvis-text-font', e.target.value);
                      }}
                      style={{
                        background: settingsTheme === 'light' ? 'rgba(255, 255, 255, 0.95)' : 'rgba(10, 12, 16, 0.95)',
                        border: settingsTheme === 'light' ? '1px solid rgba(0, 0, 0, 0.15)' : '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '10px',
                        color: settingsTheme === 'light' ? '#000' : '#fff',
                        padding: '8px 12px',
                        fontSize: '13px',
                        outline: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      <option value="'Orbitron', sans-serif">Orbitron (Futuristic)</option>
                      <option value="'Space Grotesk', sans-serif">Space Grotesk (Tech)</option>
                      <option value="'Syne', sans-serif">Syne (Modern Bold)</option>
                      <option value="'Share Tech Mono', monospace">Share Tech Mono (HUD)</option>
                      <option value="'Bruno Ace SC', sans-serif">Bruno Ace SC (Cyberpunk)</option>
                      <option value="'Major Mono Display', monospace">Major Mono (Abstract)</option>
                      <option value="'Codystar', sans-serif">Codystar (Neon Dotted)</option>
                      <option value="'Bungee', sans-serif">Bungee (Retro Solid)</option>
                    </select>
                  </div>

                  {/* ── Text Color Section ── */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>

                    {/* Status badge */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="picker-label" style={{ fontSize: '13px', color: 'var(--text)', fontWeight: '600' }}>Text Color:</span>
                      <span style={{
                        fontSize: '10px',
                        fontFamily: "'Share Tech Mono', monospace",
                        fontWeight: 'bold',
                        letterSpacing: '1px',
                        padding: '2px 8px',
                        borderRadius: '20px',
                        background: jarvisColor ? 'rgba(255,51,102,0.12)' : 'rgba(0,229,255,0.12)',
                        border: jarvisColor ? '1px solid rgba(255,51,102,0.4)' : '1px solid rgba(0,229,255,0.4)',
                        color: jarvisColor ? '#ff3366' : '#00e5ff',
                      }}>
                        {jarvisColor ? '● CUSTOM' : '⟳ AUTO-SYNCED TO BLOB'}
                      </span>
                    </div>

                    {/* Color row: swatch preview + picker + hex value */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      {/* Live preview swatch */}
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: jarvisColor || blobColor.bright,
                        boxShadow: `0 0 10px ${jarvisColor || blobColor.bright}88`,
                        border: '2px solid rgba(255,255,255,0.15)',
                        flexShrink: 0
                      }} />
                      {/* Color input picker */}
                      <input
                        type="color"
                        value={jarvisColor || blobColor.bright}
                        onChange={(e) => {
                          setJarvisColor(e.target.value);
                          localStorage.setItem('jarvis-text-color', e.target.value);
                        }}
                        className="custom-color-input"
                        title="Pick custom color"
                        style={{
                          border: '2px solid rgba(0,229,255,0.35)',
                          background: 'transparent',
                          width: '36px',
                          height: '36px',
                          cursor: 'pointer',
                          borderRadius: '50%',
                          overflow: 'hidden',
                          padding: '0',
                          flexShrink: 0
                        }}
                      />
                      <span style={{ fontSize: '13px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold', letterSpacing: '1px' }}>
                        {(jarvisColor || blobColor.bright).toUpperCase()}
                      </span>
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>

                      {/* Sync with Blob toggle */}
                      <button
                        onClick={() => {
                          if (jarvisColor) {
                            // Currently custom → switch to auto-sync (clear custom color)
                            setJarvisColor('');
                            localStorage.removeItem('jarvis-text-color');
                            showToast('Text color synced to blob!');
                          } else {
                            // Currently auto-synced → pin the current blob color as custom
                            const pinned = blobColor.bright;
                            setJarvisColor(pinned);
                            localStorage.setItem('jarvis-text-color', pinned);
                            showToast('Blob color pinned to text!');
                          }
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: jarvisColor
                            ? 'rgba(255,255,255,0.06)'
                            : `linear-gradient(135deg, ${blobColor.bright}28, ${blobColor.mid}38)`,
                          border: jarvisColor
                            ? '1px solid rgba(255,255,255,0.18)'
                            : `1.5px solid ${blobColor.bright}66`,
                          borderRadius: '20px',
                          color: jarvisColor ? 'rgba(255,255,255,0.7)' : blobColor.bright,
                          fontSize: '12px',
                          fontWeight: '700',
                          fontFamily: "'Space Grotesk', sans-serif",
                          cursor: 'pointer',
                          padding: '7px 14px',
                          transition: 'all 0.25s ease',
                          letterSpacing: '0.5px',
                          boxShadow: jarvisColor ? 'none' : `0 0 10px ${blobColor.bright}33`
                        }}
                      >
                        <span style={{
                          display: 'inline-block',
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          background: jarvisColor ? 'rgba(255,255,255,0.4)' : blobColor.bright,
                          boxShadow: jarvisColor ? 'none' : `0 0 6px ${blobColor.bright}`,
                          flexShrink: 0
                        }} />
                        {jarvisColor ? 'Sync with Blob' : '✓ Synced with Blob'}
                      </button>

                      {/* Reset / unpin — only if custom color active */}
                      {jarvisColor && (
                        <button
                          onClick={() => {
                            setJarvisColor('');
                            localStorage.removeItem('jarvis-text-color');
                            showToast('Text color reset!');
                          }}
                          style={{
                            background: 'rgba(255,51,102,0.08)',
                            border: '1px solid rgba(255,51,102,0.3)',
                            borderRadius: '20px',
                            color: '#ff5577',
                            fontSize: '12px',
                            fontWeight: '600',
                            fontFamily: "'Space Grotesk', sans-serif",
                            cursor: 'pointer',
                            padding: '7px 14px',
                            transition: 'all 0.25s ease',
                          }}
                        >
                          Reset Color
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="settings-section">
                  <div className="section-label-row">
                    <label className="section-label">4. Text Size</label>
                    <span className="size-value-display">{jarvisFontSize}px</span>
                  </div>
                  <input
                    type="range"
                    min="24"
                    max="300"
                    step="1"
                    value={jarvisFontSize}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      setJarvisFontSize(val);
                      localStorage.setItem('jarvis-text-size', val);
                    }}
                    className="size-slider-input"
                  />
                </div>

                <div className="settings-section">
                  <label className="section-label">5. Position Settings</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div className="drag-action-row">
                      <button
                        className={`btn-drag-toggle ${isTextDraggable ? 'active' : ''}`}
                        onClick={() => setIsTextDraggable(!isTextDraggable)}
                        style={{ flex: 1 }}
                      >
                        {isTextDraggable ? 'Dragging Text Active' : `Drag ${assistantName} Text`}
                      </button>
                      {isTextDraggable && (
                        <button className="btn-save-pos" onClick={handleSaveTextPosition}>
                          Save Position
                        </button>
                      )}
                    </div>
                    <button className="btn-reset-pos" onClick={handleResetTextPosition}>
                      Attach to Orb (Default)
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 3: INTERFACE MODE (SYS-03) */}
            <div className={`settings-column ${isInterfaceSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsInterfaceSectionOpen(!isInterfaceSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-03</span>
                  <h4>Interface Settings</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isInterfaceSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isInterfaceSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isInterfaceSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0' }}>
                  <label className="section-label">1. Transparent Glass Theme</label>
                  <div className="theme-toggle-container">
                    <button 
                      className={`btn-theme-toggle ${settingsTheme === 'dark' ? 'active' : ''}`}
                      onClick={() => {
                        setSettingsTheme('dark');
                        localStorage.setItem('jarvis-settings-theme', 'dark');
                      }}
                    >
                      Dark Glass
                    </button>
                    <button 
                      className={`btn-theme-toggle ${settingsTheme === 'light' ? 'active' : ''}`}
                      onClick={() => {
                        setSettingsTheme('light');
                        localStorage.setItem('jarvis-settings-theme', 'light');
                      }}
                    >
                      Light Glass
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 4: TERMINAL CONFIGURATION (SYS-04) */}
            <div className={`settings-column ${isTerminalSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsTerminalSectionOpen(!isTerminalSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-04</span>
                  <h4>Terminal Config</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isTerminalSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isTerminalSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isTerminalSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                <div className="settings-section">
                  <label className="section-label">1. Terminal Theme Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <span className="picker-label" style={{ fontSize: '13px', color: 'var(--text)' }}>Choose Color:</span>
                    <input
                      type="color"
                      value={terminalSettings.colorTheme}
                      onChange={(e) => {
                        updateTerminalSetting('colorTheme', e.target.value);
                      }}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {terminalSettings.colorTheme.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="settings-section">
                  <div className="section-label-row">
                    <label className="section-label">2. Panel Dimensions</label>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Width:</span>
                      <span className="size-value-display">{terminalSettings.width}px</span>
                    </div>
                    <input
                      type="range"
                      min="320"
                      max="1200"
                      step="10"
                      value={terminalSettings.width}
                      onChange={(e) => updateTerminalSetting('width', parseInt(e.target.value))}
                      className="size-slider-input"
                    />
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Height:</span>
                      <span className="size-value-display">{terminalSettings.height}px</span>
                    </div>
                    <input
                      type="range"
                      min="50"
                      max="400"
                      step="5"
                      value={terminalSettings.height}
                      onChange={(e) => updateTerminalSetting('height', parseInt(e.target.value))}
                      className="size-slider-input"
                    />
                  </div>
                </div>

                <div className="settings-section">
                  <div className="section-label-row">
                    <label className="section-label">3. Shape & Aesthetics</label>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Corner Radius:</span>
                      <span className="size-value-display">{terminalSettings.borderRadius}px</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="30"
                      value={terminalSettings.borderRadius}
                      onChange={(e) => updateTerminalSetting('borderRadius', parseInt(e.target.value))}
                      className="size-slider-input"
                    />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Opacity:</span>
                      <span className="size-value-display">{Math.round(terminalSettings.bgOpacity * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.20"
                      max="1.00"
                      step="0.05"
                      value={terminalSettings.bgOpacity}
                      onChange={(e) => updateTerminalSetting('bgOpacity', parseFloat(e.target.value))}
                      className="size-slider-input"
                    />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Glow Intensity:</span>
                      <span className="size-value-display">{Math.round(terminalSettings.borderGlow * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="1.00"
                      step="0.05"
                      value={terminalSettings.borderGlow}
                      onChange={(e) => updateTerminalSetting('borderGlow', parseFloat(e.target.value))}
                      className="size-slider-input"
                      style={{ marginBottom: '8px' }}
                    />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Font Family:</span>
                    </div>
                    <select
                      value={terminalSettings.fontFamily || "'Share Tech Mono', monospace"}
                      onChange={(e) => updateTerminalSetting('fontFamily', e.target.value)}
                      className="settings-select"
                      style={{ width: '100%', marginTop: '4px', boxSizing: 'border-box' }}
                    >
                      <option value="'Share Tech Mono', monospace">Share Tech Mono (HUD)</option>
                      <option value="'Orbitron', sans-serif">Orbitron (Futuristic)</option>
                      <option value="'Space Grotesk', sans-serif">Space Grotesk (Tech)</option>
                      <option value="'Syne', sans-serif">Syne (Modern Bold)</option>
                      <option value="'Bruno Ace SC', sans-serif">Bruno Ace SC (Cyberpunk)</option>
                      <option value="'Major Mono Display', monospace">Major Mono (Abstract)</option>
                    </select>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                      <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>4. Positioning Settings</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                      <button
                        className={`btn-drag-toggle ${terminalSettings.draggable ? 'active' : ''}`}
                        onClick={() => updateTerminalSetting('draggable', !terminalSettings.draggable)}
                        style={{
                          width: '100%',
                          padding: '10px',
                          borderRadius: '10px',
                          background: terminalSettings.draggable ? 'var(--terminal-theme-color, #00ff66)' : 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          color: terminalSettings.draggable ? '#000' : '#fff',
                          fontWeight: 'bold',
                          cursor: 'pointer',
                          transition: 'all 0.25s ease'
                        }}
                      >
                        {terminalSettings.draggable ? 'Dragging Panel Active' : 'Enable Draggable Panel'}
                      </button>
                      {terminalSettings.position && (
                        <button
                          onClick={() => {
                            updateTerminalSetting('position', null);
                            showToast('Terminal position reset!');
                          }}
                          style={{
                            width: '100%',
                            padding: '8px',
                            borderRadius: '8px',
                            background: 'rgba(255, 51, 102, 0.1)',
                            border: '1px solid rgba(255, 51, 102, 0.3)',
                            color: '#ff5577',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          Reset Position to Default
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 5: STATUS MATRIX CONFIGURATION (SYS-05) */}
            <div className={`settings-column ${isStatusSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsStatusSectionOpen(!isStatusSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-05</span>
                  <h4>Status Matrix Config</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isStatusSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isStatusSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isStatusSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                {/* 1. Header Title Text */}
                <div className="settings-section">
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>1. Custom Title Text</label>
                  <input
                    type="text"
                    value={statusSettings.titleText}
                    onChange={(e) => updateStatusSetting('titleText', e.target.value)}
                    placeholder="SYSTEM STATUS MATRIX"
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '10px',
                      color: '#fff',
                      padding: '8px 12px',
                      fontSize: '13px',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                {/* 2. Status Capsule Theme Color */}
                <div className="settings-section">
                  <label className="section-label">2. Matrix Theme Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <input
                      type="color"
                      value={statusSettings.colorTheme}
                      onChange={(e) => updateStatusSetting('colorTheme', e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {statusSettings.colorTheme.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* 3. Status Text Color */}
                <div className="settings-section">
                  <label className="section-label">3. Text Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <input
                      type="color"
                      value={statusSettings.textColor}
                      onChange={(e) => updateStatusSetting('textColor', e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {statusSettings.textColor.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* 4. Drag & Position Status capsule */}
                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0' }}>
                  <label className="section-label">4. Positioning Settings</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                    <button
                      className={`btn-drag-toggle ${statusSettings.draggable ? 'active' : ''}`}
                      onClick={() => updateStatusSetting('draggable', !statusSettings.draggable)}
                      style={{
                        width: '100%',
                        padding: '10px',
                        borderRadius: '10px',
                        background: statusSettings.draggable ? 'var(--terminal-theme-color, #00ff66)' : 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: statusSettings.draggable ? '#000' : '#fff',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        transition: 'all 0.25s ease'
                      }}
                    >
                      {statusSettings.draggable ? 'Dragging Panel Active' : 'Enable Draggable Panel'}
                    </button>
                    {statusSettings.position && (
                      <button
                        onClick={() => {
                          updateStatusSetting('position', null);
                          showToast('Position reset to top-right!');
                        }}
                        style={{
                          width: '100%',
                          padding: '8px',
                          borderRadius: '8px',
                          background: 'rgba(255, 51, 102, 0.1)',
                          border: '1px solid rgba(255, 51, 102, 0.3)',
                          color: '#ff5577',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        Reset Position to Default
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 7: ENVIRONMENT HUD CONFIGURATION (SYS-07) */}
            <div className={`settings-column ${isEnvSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsEnvSectionOpen(!isEnvSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-07</span>
                  <h4>Env HUD Config</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isEnvSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isEnvSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isEnvSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                {/* Title Text */}
                <div className="settings-section">
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>1. Custom Title Text</label>
                  <input
                    type="text"
                    value={envWidgetSettings.titleText}
                    onChange={(e) => updateEnvWidgetSetting('titleText', e.target.value)}
                    placeholder="ENVIRONMENT MATRIX"
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '10px',
                      color: '#fff',
                      padding: '8px 12px',
                      fontSize: '13px',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                {/* Theme Color */}
                <div className="settings-section">
                  <label className="section-label">2. Widget Theme Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <input
                      type="color"
                      value={envWidgetSettings.colorTheme || statusSettings.colorTheme}
                      onChange={(e) => updateEnvWidgetSetting('colorTheme', e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {(envWidgetSettings.colorTheme || statusSettings.colorTheme).toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Text Color */}
                <div className="settings-section">
                  <label className="section-label">3. Text Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <input
                      type="color"
                      value={envWidgetSettings.textColor || statusSettings.textColor}
                      onChange={(e) => updateEnvWidgetSetting('textColor', e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {(envWidgetSettings.textColor || statusSettings.textColor).toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Drag & Drop Toggle + Position Controls */}
                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0' }}>
                  <label className="section-label">4. Drag & Position</label>

                  {/* Drag toggle */}
                  <button
                    className={`btn-drag-toggle ${envWidgetSettings.draggable ? 'active' : ''}`}
                    onClick={() => updateEnvWidgetSetting('draggable', !envWidgetSettings.draggable)}
                    style={{
                      width: '100%',
                      padding: '10px',
                      marginTop: '8px',
                      marginBottom: '12px',
                      borderRadius: '10px',
                      background: envWidgetSettings.draggable
                        ? 'rgba(0,255,102,0.18)'
                        : 'rgba(255,255,255,0.04)',
                      border: envWidgetSettings.draggable
                        ? '1px solid rgba(0,255,102,0.5)'
                        : '1px solid rgba(255,255,255,0.1)',
                      color: envWidgetSettings.draggable ? '#00ff66' : 'rgba(255,255,255,0.5)',
                      fontWeight: 'bold',
                      fontSize: '12px',
                      fontFamily: 'var(--mono)',
                      letterSpacing: '1px',
                      cursor: 'pointer',
                      transition: 'all 0.25s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                    }}
                  >
                    <span style={{ fontSize: '14px' }}>{envWidgetSettings.draggable ? '⊙' : '⊕'}</span>
                    {envWidgetSettings.draggable ? 'DRAG MODE ON — Click to Lock' : 'Enable Drag & Drop'}
                  </button>

                  {/* Mini drag-map */}
                  <div
                    style={{
                      position: 'relative',
                      width: '100%',
                      height: '90px',
                      background: 'rgba(0,255,102,0.04)',
                      border: '1px solid rgba(0,255,102,0.2)',
                      borderRadius: '10px',
                      cursor: 'crosshair',
                      overflow: 'hidden',
                      userSelect: 'none',
                      opacity: 1
                    }}
                    ref={envMapRef}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setIsDraggingEnvMap(true);
                      const rect = envMapRef.current.getBoundingClientRect();
                      const px = Math.round(((e.clientX - rect.left) / rect.width) * (window.innerWidth - 200));
                      const py = Math.round(((e.clientY - rect.top) / rect.height) * (window.innerHeight - 200));
                      setEnvPosAndSync({ x: Math.max(0, px), y: Math.max(0, py) });
                    }}
                    onMouseMove={(e) => {
                      if (!isDraggingEnvMap) return;
                      const rect = envMapRef.current.getBoundingClientRect();
                      const px = Math.round(((e.clientX - rect.left) / rect.width) * (window.innerWidth - 200));
                      const py = Math.round(((e.clientY - rect.top) / rect.height) * (window.innerHeight - 200));
                      setEnvPosAndSync({ x: Math.max(0, px), y: Math.max(0, py) });
                    }}
                    onMouseUp={() => setIsDraggingEnvMap(false)}
                    onMouseLeave={() => setIsDraggingEnvMap(false)}
                  >
                    {/* Grid lines */}
                    <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,255,102,0.06) 0px, rgba(0,255,102,0.06) 1px, transparent 1px, transparent 18px), repeating-linear-gradient(90deg, rgba(0,255,102,0.06) 0px, rgba(0,255,102,0.06) 1px, transparent 1px, transparent 18px)', pointerEvents: 'none' }} />
                    {/* Corner labels */}
                    <span style={{ position: 'absolute', top: 3, left: 5, fontSize: '8px', color: 'rgba(0,255,102,0.35)', fontFamily: 'var(--mono)', pointerEvents: 'none' }}>0,0</span>
                    <span style={{ position: 'absolute', bottom: 3, right: 5, fontSize: '8px', color: 'rgba(0,255,102,0.35)', fontFamily: 'var(--mono)', pointerEvents: 'none' }}>W,H</span>
                    {/* Draggable dot */}
                    <div
                      style={{
                        position: 'absolute',
                        width: '14px',
                        height: '14px',
                        borderRadius: '50%',
                        background: 'rgba(0,255,102,0.9)',
                        boxShadow: '0 0 8px rgba(0,255,102,0.8)',
                        border: '2px solid #fff',
                        transform: 'translate(-50%, -50%)',
                        left: `${Math.min(100, (envPos.x / (window.innerWidth - 200)) * 100)}%`,
                        top: `${Math.min(100, (envPos.y / (window.innerHeight - 200)) * 100)}%`,
                        pointerEvents: 'none',
                        transition: isDraggingEnvMap ? 'none' : 'left 0.15s, top 0.15s'
                      }}
                    />
                    {/* Crosshair lines */}
                    <div style={{
                      position: 'absolute',
                      left: `${Math.min(100, (envPos.x / (window.innerWidth - 200)) * 100)}%`,
                      top: 0, bottom: 0,
                      width: '1px',
                      background: 'rgba(0,255,102,0.25)',
                      pointerEvents: 'none',
                      transition: isDraggingEnvMap ? 'none' : 'left 0.15s'
                    }} />
                    <div style={{
                      position: 'absolute',
                      top: `${Math.min(100, (envPos.y / (window.innerHeight - 200)) * 100)}%`,
                      left: 0, right: 0,
                      height: '1px',
                      background: 'rgba(0,255,102,0.25)',
                      pointerEvents: 'none',
                      transition: isDraggingEnvMap ? 'none' : 'top 0.15s'
                    }} />
                  </div>

                  {/* X / Y inputs */}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    {[['X', 'x', window.innerWidth - 200], ['Y', 'y', window.innerHeight - 200]].map(([label, axis, maxVal]) => (
                      <div key={axis} style={{ flex: 1 }}>
                        <div style={{ fontSize: '10px', color: 'rgba(0,255,102,0.6)', fontFamily: 'var(--mono)', marginBottom: '3px' }}>{label} PX</div>
                        <input
                          type="number"
                          min={0}
                          max={maxVal}
                          value={envPos[axis]}
                          onChange={(e) => {
                            const val = Math.max(0, Math.min(maxVal, parseInt(e.target.value) || 0));
                            setEnvPosAndSync({ ...envPos, [axis]: val });
                          }}
                          style={{
                            width: '100%',
                            background: 'rgba(0,255,102,0.05)',
                            border: '1px solid rgba(0,255,102,0.2)',
                            borderRadius: '6px',
                            color: '#00ff66',
                            padding: '5px 8px',
                            fontSize: '12px',
                            fontFamily: 'var(--mono)',
                            outline: 'none',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Coordinate readout + reset */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: 'rgba(0,255,102,0.5)' }}>
                      [{envPos.x}, {envPos.y}] px
                    </span>
                    <button
                      onClick={() => {
                        const defaultPos = { x: 24, y: 110 };
                        setEnvPosAndSync(defaultPos);
                        showToast('Env position reset!');
                      }}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        background: 'rgba(255, 51, 102, 0.1)',
                        border: '1px solid rgba(255, 51, 102, 0.3)',
                        color: '#ff5577',
                        cursor: 'pointer',
                        fontSize: '10px'
                      }}
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Widget Size */}
                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0' }}>
                  <label className="section-label">5. Widget Size</label>
                  <div style={{ marginTop: '10px' }}>
                    <input
                      type="range"
                      min={0.5}
                      max={2}
                      step={0.05}
                      value={envWidgetSettings.scale ?? 1}
                      onChange={(e) => updateEnvWidgetSetting('scale', parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: '#00ff66', cursor: 'pointer' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                      <span style={{ fontSize: '9px', color: 'rgba(0,255,102,0.4)', fontFamily: 'var(--mono)' }}>0.5×</span>
                      <span style={{ fontSize: '11px', color: '#00ff66', fontFamily: 'var(--mono)', fontWeight: 'bold' }}>
                        {(envWidgetSettings.scale ?? 1).toFixed(2)}×
                      </span>
                      <span style={{ fontSize: '9px', color: 'rgba(0,255,102,0.4)', fontFamily: 'var(--mono)' }}>2×</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 8: HARDWARE STATE WIDGET CONFIGURATION (SYS-08) */}
            <div className={`settings-column ${isConnSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsConnSectionOpen(!isConnSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-08</span>
                  <h4>Hardware HUD Config</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isConnSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isConnSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isConnSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                {/* Title Text */}
                <div className="settings-section">
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>1. Custom Title Text</label>
                  <input
                    type="text"
                    value={connWidgetSettings.titleText}
                    onChange={(e) => updateConnWidgetSetting('titleText', e.target.value)}
                    placeholder="HARDWARE LINK STATE"
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '10px',
                      color: '#fff',
                      padding: '8px 12px',
                      fontSize: '13px',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                {/* Theme Color */}
                <div className="settings-section">
                  <label className="section-label">2. Widget Theme Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <input
                      type="color"
                      value={connWidgetSettings.colorTheme || statusSettings.colorTheme}
                      onChange={(e) => updateConnWidgetSetting('colorTheme', e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {(connWidgetSettings.colorTheme || statusSettings.colorTheme).toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Text Color */}
                <div className="settings-section">
                  <label className="section-label">3. Text Color</label>
                  <div className="custom-color-picker-container" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                    <input
                      type="color"
                      value={connWidgetSettings.textColor || statusSettings.textColor}
                      onChange={(e) => updateConnWidgetSetting('textColor', e.target.value)}
                      className="custom-color-input"
                      style={{
                        border: '1px solid rgba(255,255,255,0.2)',
                        background: 'transparent',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        padding: '0'
                      }}
                    />
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--accent)', fontWeight: 'bold' }}>
                      {(connWidgetSettings.textColor || statusSettings.textColor).toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Drag toggle + Position Controls - Conn */}
                <div className="settings-section">
                  <label className="section-label">4. Drag & Position</label>

                  {/* Drag toggle */}
                  <button
                    className={`btn-drag-toggle ${connWidgetSettings.draggable ? 'active' : ''}`}
                    onClick={() => updateConnWidgetSetting('draggable', !connWidgetSettings.draggable)}
                    style={{
                      width: '100%',
                      padding: '10px',
                      marginTop: '8px',
                      marginBottom: '12px',
                      borderRadius: '10px',
                      background: connWidgetSettings.draggable
                        ? 'rgba(0,180,255,0.18)'
                        : 'rgba(255,255,255,0.04)',
                      border: connWidgetSettings.draggable
                        ? '1px solid rgba(0,180,255,0.5)'
                        : '1px solid rgba(255,255,255,0.1)',
                      color: connWidgetSettings.draggable ? '#00b4ff' : 'rgba(255,255,255,0.5)',
                      fontWeight: 'bold',
                      fontSize: '12px',
                      fontFamily: 'var(--mono)',
                      letterSpacing: '1px',
                      cursor: 'pointer',
                      transition: 'all 0.25s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                    }}
                  >
                    <span style={{ fontSize: '14px' }}>{connWidgetSettings.draggable ? '⊙' : '⊕'}</span>
                    {connWidgetSettings.draggable ? 'DRAG MODE ON — Click to Lock' : 'Enable Drag & Drop'}
                  </button>

                  {/* Mini drag-map */}
                  <div
                    style={{
                      position: 'relative',
                      width: '100%',
                      height: '90px',
                      marginTop: '10px',
                      background: 'rgba(0,180,255,0.04)',
                      border: '1px solid rgba(0,180,255,0.2)',
                      borderRadius: '10px',
                      cursor: 'crosshair',
                      overflow: 'hidden',
                      userSelect: 'none'
                    }}
                    ref={connMapRef}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setIsDraggingConnMap(true);
                      const rect = connMapRef.current.getBoundingClientRect();
                      const px = Math.round(((e.clientX - rect.left) / rect.width) * (window.innerWidth - 200));
                      const py = Math.round(((e.clientY - rect.top) / rect.height) * (window.innerHeight - 200));
                      setConnPosAndSync({ x: Math.max(0, px), y: Math.max(0, py) });
                    }}
                    onMouseMove={(e) => {
                      if (!isDraggingConnMap) return;
                      const rect = connMapRef.current.getBoundingClientRect();
                      const px = Math.round(((e.clientX - rect.left) / rect.width) * (window.innerWidth - 200));
                      const py = Math.round(((e.clientY - rect.top) / rect.height) * (window.innerHeight - 200));
                      setConnPosAndSync({ x: Math.max(0, px), y: Math.max(0, py) });
                    }}
                    onMouseUp={() => setIsDraggingConnMap(false)}
                    onMouseLeave={() => setIsDraggingConnMap(false)}
                  >
                    {/* Grid */}
                    <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,180,255,0.06) 0px, rgba(0,180,255,0.06) 1px, transparent 1px, transparent 18px), repeating-linear-gradient(90deg, rgba(0,180,255,0.06) 0px, rgba(0,180,255,0.06) 1px, transparent 1px, transparent 18px)', pointerEvents: 'none' }} />
                    <span style={{ position: 'absolute', top: 3, left: 5, fontSize: '8px', color: 'rgba(0,180,255,0.35)', fontFamily: 'var(--mono)', pointerEvents: 'none' }}>0,0</span>
                    <span style={{ position: 'absolute', bottom: 3, right: 5, fontSize: '8px', color: 'rgba(0,180,255,0.35)', fontFamily: 'var(--mono)', pointerEvents: 'none' }}>W,H</span>
                    {/* Dot */}
                    <div style={{
                      position: 'absolute',
                      width: '14px', height: '14px',
                      borderRadius: '50%',
                      background: 'rgba(0,180,255,0.9)',
                      boxShadow: '0 0 8px rgba(0,180,255,0.8)',
                      border: '2px solid #fff',
                      transform: 'translate(-50%, -50%)',
                      left: `${Math.min(100, (connPos.x / (window.innerWidth - 200)) * 100)}%`,
                      top: `${Math.min(100, (connPos.y / (window.innerHeight - 200)) * 100)}%`,
                      pointerEvents: 'none',
                      transition: isDraggingConnMap ? 'none' : 'left 0.15s, top 0.15s'
                    }} />
                    {/* Crosshairs */}
                    <div style={{
                      position: 'absolute',
                      left: `${Math.min(100, (connPos.x / (window.innerWidth - 200)) * 100)}%`,
                      top: 0, bottom: 0, width: '1px',
                      background: 'rgba(0,180,255,0.25)', pointerEvents: 'none',
                      transition: isDraggingConnMap ? 'none' : 'left 0.15s'
                    }} />
                    <div style={{
                      position: 'absolute',
                      top: `${Math.min(100, (connPos.y / (window.innerHeight - 200)) * 100)}%`,
                      left: 0, right: 0, height: '1px',
                      background: 'rgba(0,180,255,0.25)', pointerEvents: 'none',
                      transition: isDraggingConnMap ? 'none' : 'top 0.15s'
                    }} />
                  </div>

                  {/* X / Y inputs */}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    {[['X', 'x', window.innerWidth - 200], ['Y', 'y', window.innerHeight - 200]].map(([label, axis, maxVal]) => (
                      <div key={axis} style={{ flex: 1 }}>
                        <div style={{ fontSize: '10px', color: 'rgba(0,180,255,0.6)', fontFamily: 'var(--mono)', marginBottom: '3px' }}>{label} PX</div>
                        <input
                          type="number"
                          min={0}
                          max={maxVal}
                          value={connPos[axis]}
                          onChange={(e) => {
                            const val = Math.max(0, Math.min(maxVal, parseInt(e.target.value) || 0));
                            setConnPosAndSync({ ...connPos, [axis]: val });
                          }}
                          style={{
                            width: '100%',
                            background: 'rgba(0,180,255,0.05)',
                            border: '1px solid rgba(0,180,255,0.2)',
                            borderRadius: '6px',
                            color: '#00b4ff',
                            padding: '5px 8px',
                            fontSize: '12px',
                            fontFamily: 'var(--mono)',
                            outline: 'none',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Readout + reset */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: 'rgba(0,180,255,0.5)' }}>
                      [{connPos.x}, {connPos.y}] px
                    </span>
                    <button
                      onClick={() => {
                        const defaultPos = { x: 24, y: 395 };
                        setConnPosAndSync(defaultPos);
                        showToast('Hardware position reset!');
                      }}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        background: 'rgba(255, 51, 102, 0.1)',
                        border: '1px solid rgba(255, 51, 102, 0.3)',
                        color: '#ff5577',
                        cursor: 'pointer',
                        fontSize: '10px'
                      }}
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Widget Size */}
                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0' }}>
                  <label className="section-label">5. Widget Size</label>
                  <div style={{ marginTop: '10px' }}>
                    <input
                      type="range"
                      min={0.5}
                      max={2}
                      step={0.05}
                      value={connWidgetSettings.scale ?? 1}
                      onChange={(e) => updateConnWidgetSetting('scale', parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: '#00b4ff', cursor: 'pointer' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                      <span style={{ fontSize: '9px', color: 'rgba(0,180,255,0.4)', fontFamily: 'var(--mono)' }}>0.5×</span>
                      <span style={{ fontSize: '11px', color: '#00b4ff', fontFamily: 'var(--mono)', fontWeight: 'bold' }}>
                        {(connWidgetSettings.scale ?? 1).toFixed(2)}×
                      </span>
                      <span style={{ fontSize: '9px', color: 'rgba(0,180,255,0.4)', fontFamily: 'var(--mono)' }}>2×</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* COLUMN 6: VOICE SETTINGS (SYS-06) */}
            <div className={`settings-column ${isVoiceSectionOpen ? 'open' : 'collapsed'}`}>
              <button 
                className="column-accordion-header"
                onClick={() => setIsVoiceSectionOpen(!isVoiceSectionOpen)}
              >
                <div className="header-text-group">
                  <span className="module-tag">SYS-06</span>
                  <h4>Voice Settings</h4>
                </div>
                <div className="header-status-indicator">
                  <span className="status-label">{isVoiceSectionOpen ? 'ONLINE' : 'STANDBY'}</span>
                  <span className={`status-dot ${isVoiceSectionOpen ? 'online' : 'standby'}`}></span>
                  <span className="chevron-icon">{isVoiceSectionOpen ? '▼' : '▲'}</span>
                </div>
              </button>
              
              <div className="column-accordion-content">
                <div className="settings-section">
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>1. Assistant Voice</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        className={`voice-gender-btn ${voiceGender === 'Female' ? 'active' : ''}`}
                        onClick={() => updateVoiceGender('Female')}
                        style={{
                          flex: 1,
                          padding: '10px',
                          background: voiceGender === 'Female' ? 'rgba(0, 229, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                          border: voiceGender === 'Female' ? '1px solid #00e5ff' : '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                          color: '#fff',
                          cursor: 'pointer',
                          fontFamily: 'var(--mono)',
                          fontSize: '12px',
                          fontWeight: 'bold',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        FEMALE
                      </button>
                      <button
                        className={`voice-gender-btn ${voiceGender === 'Male' ? 'active' : ''}`}
                        onClick={() => updateVoiceGender('Male')}
                        style={{
                          flex: 1,
                          padding: '10px',
                          background: voiceGender === 'Male' ? 'rgba(0, 229, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                          border: voiceGender === 'Male' ? '1px solid #00e5ff' : '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                          color: '#fff',
                          cursor: 'pointer',
                          fontFamily: 'var(--mono)',
                          fontSize: '12px',
                          fontWeight: 'bold',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        MALE
                      </button>
                    </div>
                  </div>
                </div>

                <div className="settings-section" style={{ marginTop: '14px' }}>
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>2. Voice Language</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', fontFamily: 'var(--mono)', lineHeight: '1.4', marginBottom: '6px' }}>
                      Selects the TTS voice language independently of Display or Listening language.
                    </div>
                    <select
                      value={voiceLanguage}
                      onChange={(e) => updateVoiceLanguage(e.target.value)}
                      style={{
                        background: settingsTheme === 'light' ? 'rgba(255, 255, 255, 0.95)' : 'rgba(10, 12, 16, 0.95)',
                        border: settingsTheme === 'light' ? '1px solid rgba(0, 0, 0, 0.15)' : '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '10px',
                        color: settingsTheme === 'light' ? '#000' : '#fff',
                        padding: '8px 12px',
                        fontSize: '13px',
                        outline: 'none',
                        cursor: 'pointer',
                        width: '100%'
                      }}
                    >
                      <option value="auto">Auto (follows response language)</option>
                      <option value="english">English</option>
                      <option value="hinglish">Hinglish (Indian English)</option>
                      <option value="hindi">हिन्दी (Hindi)</option>
                      <option value="odia">ଓଡ଼ିଆ (Odia)</option>
                      <option value="telugu">తెలుగు (Telugu)</option>
                      <option value="tamil">தமிழ் (Tamil)</option>
                      <option value="kannada">ಕನ್ನಡ (Kannada)</option>
                      <option value="malayalam">മലയാളം (Malayalam)</option>
                      <option value="bengali">বাংলা (Bengali)</option>
                      <option value="gujarati">ગુજરાતી (Gujarati)</option>
                      <option value="punjabi">ਪੰਜਾਬੀ (Punjabi)</option>
                      <option value="marathi">मराठी (Marathi)</option>
                    </select>
                    {voiceLanguage !== 'auto' && (
                      <div style={{ fontSize: '11px', color: '#00e5ff', fontFamily: 'var(--mono)', marginTop: '4px' }}>
                        ✓ TTS locked to: <strong>{voiceLanguage.charAt(0).toUpperCase() + voiceLanguage.slice(1)}</strong>
                      </div>
                    )}
                  </div>
                </div>

                <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: '0', marginTop: '14px' }}>
                  <label className="section-label" style={{ display: 'block', marginBottom: '8px' }}>3. Active Display Language</label>
                  <div style={{ 
                    background: 'rgba(255,255,255,0.03)', 
                    border: '1px solid rgba(255,255,255,0.1)', 
                    padding: '12px', 
                    borderRadius: '10px' 
                  }}>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', fontFamily: 'var(--mono)', textTransform: 'uppercase' }}>
                      Current Display Language
                    </div>
                    <div style={{ fontSize: '15px', color: '#00e5ff', fontWeight: 'bold', marginTop: '4px' }}>
                      {localStorage.getItem('jarvis-display-lang') || 'English'}
                    </div>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '8px', lineHeight: '1.3' }}>
                      Set in the Terminal header. When Voice Language is "Auto", TTS follows this language.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {toastMessage && (
            <div className="settings-toast">
              {toastMessage}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
