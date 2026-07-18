import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAssistantConfig } from '../context/AssistantConfigContext';
import { invoke } from '@tauri-apps/api/core';
import './Widgets.css';

// ── Reverse geocode lat/lon → city + country using Nominatim ─────────────────
async function reverseGeocode(lat, lon) {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
      { headers: { 'Accept-Language': 'en' } }
    );
    if (!res.ok) return null;
    const data = await res.json();
    const addr = data.address || {};
    return {
      city: addr.city || addr.town || addr.village || addr.county || addr.state || 'Unknown',
      country: addr.country || 'Unknown',
      countryCode: (addr.country_code || 'XX').toUpperCase(),
      lat,
      lon,
    };
  } catch {
    return null;
  }
}

export default function Widgets() {
  const { statusSettings, envWidgetSettings, connWidgetSettings } = useAssistantConfig();
  const [systemData, setSystemData] = useState(null);
  const [localTime, setLocalTime] = useState(new Date());
  const [ping, setPing] = useState(null);

  // ── Geolocation state ─────────────────────────────────────────────────────
  // 'idle' | 'requesting' | 'granted' | 'denied' | 'unavailable'
  const [geoStatus, setGeoStatus] = useState('idle');
  const [geoLocation, setGeoLocation] = useState(null); // { city, country, countryCode, lat, lon }
  const [isRefreshing, setIsRefreshing] = useState(false);

  // ── Env Widget Position ───────────────────────────────────────────────────
  const [posEnv, setPosEnv] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis-widget-env-pos');
      return saved ? JSON.parse(saved) : { x: 24, y: 110 };
    } catch { return { x: 24, y: 110 }; }
  });
  const posEnvRef = useRef(posEnv);
  const isDraggingEnvRef = useRef(false);
  const dragOffsetEnvRef = useRef({ x: 0, y: 0 });
  const [isDraggingEnv, setIsDraggingEnv] = useState(false);

  // ── Conn Widget Position ──────────────────────────────────────────────────
  const [posConn, setPosConn] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis-widget-conn-pos');
      return saved ? JSON.parse(saved) : { x: 24, y: 395 };
    } catch { return { x: 24, y: 395 }; }
  });
  const posConnRef = useRef(posConn);
  const isDraggingConnRef = useRef(false);
  const dragOffsetConnRef = useRef({ x: 0, y: 0 });
  const [isDraggingConn, setIsDraggingConn] = useState(false);

  // ── Request browser geolocation ───────────────────────────────────────────
  const requestGeoLocation = useCallback(async () => {
    if (!navigator.geolocation) {
      setGeoStatus('unavailable');
      return;
    }
    setGeoStatus('requesting');
    setIsRefreshing(true);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        const result = await reverseGeocode(latitude, longitude);
        if (result) {
          setGeoLocation(result);
          setGeoStatus('granted');
        } else {
          // Geocode failed but we have coords
          setGeoLocation({
            city: 'Unknown',
            country: 'Unknown',
            countryCode: 'XX',
            lat: latitude,
            lon: longitude,
          });
          setGeoStatus('granted');
        }
        setIsRefreshing(false);
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setGeoStatus('denied');
        } else {
          setGeoStatus('unavailable');
        }
        setIsRefreshing(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }, []);

  // Auto-request on mount (will silently fail if denied)
  useEffect(() => {
    // Check existing permission state first
    if (navigator.permissions) {
      navigator.permissions.query({ name: 'geolocation' }).then((result) => {
        if (result.state === 'granted') {
          requestGeoLocation();
        } else if (result.state === 'denied') {
          setGeoStatus('denied');
        } else {
          // 'prompt' — try requesting (browser will show dialog)
          requestGeoLocation();
        }
        result.onchange = () => {
          if (result.state === 'granted') requestGeoLocation();
          else if (result.state === 'denied') setGeoStatus('denied');
        };
      }).catch(() => {
        // permissions API not supported — try anyway
        requestGeoLocation();
      });
    } else {
      requestGeoLocation();
    }
  }, [requestGeoLocation]);

  // ── Fetch system info (IP-based fallback location + hardware) ────────────
  useEffect(() => {
    const fetchSystemInfo = async () => {
      const isTauri = typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__;
      try {
        const tStart = Date.now();
        let data = null;
        if (isTauri) {
          data = await invoke('get_system_info');
        } else {
          const res = await fetch('http://localhost:8000/api/system_info');
          if (res.ok) {
            data = await res.json();
          }
        }
        if (data) {
          setSystemData(data);
          setPing(Date.now() - tStart);
        }
      } catch (err) {
        console.warn('Transient backend system_info query log (backend may still be booting):', err);
      }
    };
    fetchSystemInfo();
    const interval = setInterval(fetchSystemInfo, 6000);
    return () => clearInterval(interval);
  }, []);

  // ── Clock ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    const clockInterval = setInterval(() => setLocalTime(new Date()), 1000);
    return () => clearInterval(clockInterval);
  }, []);

  // ── Custom event: sync pos from settings panel ────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (!e.detail) return;
      posEnvRef.current = e.detail;
      setPosEnv(e.detail);
    };
    window.addEventListener('jarvis-env-pos-change', handler);
    return () => window.removeEventListener('jarvis-env-pos-change', handler);
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (!e.detail) return;
      posConnRef.current = e.detail;
      setPosConn(e.detail);
    };
    window.addEventListener('jarvis-conn-pos-change', handler);
    return () => window.removeEventListener('jarvis-conn-pos-change', handler);
  }, []);

  // ── Global drag listeners (ref-based, no stale closure) ──────────────────
  useEffect(() => {
    const onMouseMove = (e) => {
      if (isDraggingEnvRef.current) {
        const newPos = {
          x: e.clientX - dragOffsetEnvRef.current.x,
          y: e.clientY - dragOffsetEnvRef.current.y,
        };
        posEnvRef.current = newPos;
        setPosEnv({ ...newPos });
      }
      if (isDraggingConnRef.current) {
        const newPos = {
          x: e.clientX - dragOffsetConnRef.current.x,
          y: e.clientY - dragOffsetConnRef.current.y,
        };
        posConnRef.current = newPos;
        setPosConn({ ...newPos });
      }
    };
    const onMouseUp = () => {
      if (isDraggingEnvRef.current) {
        isDraggingEnvRef.current = false;
        setIsDraggingEnv(false);
        localStorage.setItem('jarvis-widget-env-pos', JSON.stringify(posEnvRef.current));
      }
      if (isDraggingConnRef.current) {
        isDraggingConnRef.current = false;
        setIsDraggingConn(false);
        localStorage.setItem('jarvis-widget-conn-pos', JSON.stringify(posConnRef.current));
      }
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  // ── Drag mousedown handlers ───────────────────────────────────────────────
  const handleMouseDownEnv = (e) => {
    if (!envWidgetSettings.draggable) return;           // locked when drag mode off
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.target.closest('.geo-location-btn')) return;
    isDraggingEnvRef.current = true;
    setIsDraggingEnv(true);
    dragOffsetEnvRef.current = {
      x: e.clientX - posEnvRef.current.x,
      y: e.clientY - posEnvRef.current.y,
    };
    e.preventDefault();
  };

  const handleMouseDownConn = (e) => {
    if (!connWidgetSettings.draggable) return;          // locked when drag mode off
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    isDraggingConnRef.current = true;
    setIsDraggingConn(true);
    dragOffsetConnRef.current = {
      x: e.clientX - posConnRef.current.x,
      y: e.clientY - posConnRef.current.y,
    };
    e.preventDefault();
  };

  // ── Computed location: prefer GPS, fall back to IP ───────────────────────
  const ipLocation = systemData?.location || { city: 'Bengaluru', country: 'India', countryCode: 'IN', lat: 12.9716, lon: 77.5946 };
  const location = geoLocation || ipLocation;
  const usingGPS = !!geoLocation;

  // ── Style helpers ─────────────────────────────────────────────────────────
  const themeColorEnv  = envWidgetSettings.colorTheme  || statusSettings.colorTheme || '#00ff66';
  const textColorEnv   = envWidgetSettings.textColor   || statusSettings.textColor  || '#ffffff';
  const scaleEnv       = envWidgetSettings.scale       ?? 1;
  const dragEnv        = envWidgetSettings.draggable   ?? false;

  const themeColorConn = connWidgetSettings.colorTheme || statusSettings.colorTheme || '#00ff66';
  const textColorConn  = connWidgetSettings.textColor  || statusSettings.textColor  || '#ffffff';
  const scaleConn      = connWidgetSettings.scale      ?? 1;
  const dragConn       = connWidgetSettings.draggable  ?? false;

  const envStyle = {
    position: 'fixed',
    left: `${posEnv.x}px`,
    top:  `${posEnv.y}px`,
    zIndex: 998,
    cursor: dragEnv ? (isDraggingEnv ? 'grabbing' : 'grab') : 'default',
    transform: `scale(${scaleEnv})`,
    transformOrigin: 'top left',
    '--widget-theme-color': themeColorEnv,
    '--widget-text-color':  textColorEnv,
    borderColor: `${themeColorEnv}44`,
    boxShadow: `0 0 15px rgba(0,0,0,0.6), 0 0 15px ${themeColorEnv}1a inset, 0 0 10px ${themeColorEnv}0d`,
  };

  const connStyle = {
    position: 'fixed',
    left: `${posConn.x}px`,
    top:  `${posConn.y}px`,
    zIndex: 998,
    cursor: dragConn ? (isDraggingConn ? 'grabbing' : 'grab') : 'default',
    transform: `scale(${scaleConn})`,
    transformOrigin: 'top left',
    '--widget-theme-color': themeColorConn,
    '--widget-text-color':  textColorConn,
    borderColor: `${themeColorConn}44`,
    boxShadow: `0 0 15px rgba(0,0,0,0.6), 0 0 15px ${themeColorConn}1a inset, 0 0 10px ${themeColorConn}0d`,
  };

  const formatTime = (t) => t.toTimeString().split(' ')[0];
  const formatDate = (t) => {
    const options = { day: '2-digit', month: 'short', year: 'numeric' };
    return t.toLocaleDateString('en-US', options).toUpperCase();
  };

  // ── Geo status indicator ─────────────────────────────────────────────────
  const geoIcon = {
    idle:        '◌',
    requesting:  '⟳',
    granted:     '⊕',
    denied:      '⊗',
    unavailable: '⊘',
  }[geoStatus] || '◌';

  const geoIconColor = {
    idle:        'rgba(255,255,255,0.3)',
    requesting:  themeColorEnv,
    granted:     themeColorEnv,
    denied:      '#ff5577',
    unavailable: '#ffaa00',
  }[geoStatus] || 'rgba(255,255,255,0.3)';

  const geoTooltip = {
    idle:        'Location not requested',
    requesting:  'Acquiring GPS...',
    granted:     `GPS · ${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}`,
    denied:      'Location denied — click to request',
    unavailable: 'Location unavailable — click to retry',
  }[geoStatus] || '';

  const battery  = systemData?.battery  || { percent: 100, power_plugged: true };
  const network  = systemData?.network  || { wifi: { connected: true, ssid: 'Secure Connection' }, bluetooth: { enabled: true } };

  return (
    <>
      {/* 1. ENVIRONMENT HUD WIDGET */}
      <div
        className={`sci-fi-widget-container${dragEnv ? ' draggable-active' : ''}`}
        style={envStyle}
        onMouseDown={handleMouseDownEnv}
      >
        <div className="sci-fi-widget-capsule">
          <div className="widget-scanline" />
          <div className="widget-header">
            <span className="widget-header-text" style={{ color: 'var(--widget-theme-color)' }}>
              {envWidgetSettings.titleText || 'ENVIRONMENT MATRIX'}
            </span>
            <span className="widget-header-sub" style={{ color: 'var(--widget-theme-color)', opacity: 0.7 }}>SYS-05</span>
          </div>

          <div className="widget-content" style={{ color: 'var(--widget-text-color)' }}>
            <div className="clock-display font-mono" style={{ color: 'var(--widget-theme-color)' }}>
              {formatTime(localTime)}
            </div>
            <div className="date-display font-mono">
              {formatDate(localTime)}
            </div>

            <div className="divider-glow" style={{ background: `linear-gradient(90deg, transparent, ${themeColorEnv}66, transparent)` }} />

            <div className="info-grid">
              {/* Location row — clickable to request/refresh geo */}
              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>LOCATION:</span>
                <button
                  className="geo-location-btn"
                  title={geoTooltip}
                  onClick={(e) => {
                    e.stopPropagation();
                    requestGeoLocation();
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: '0',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: 'var(--widget-text-color)',
                    fontFamily: 'inherit',
                    fontSize: '10.5px',
                    fontWeight: 600,
                  }}
                >
                  <span
                    className="font-mono"
                    style={{
                      fontSize: '10.5px',
                      color: (geoStatus === 'denied' || geoStatus === 'unavailable')
                        ? '#ff9999'
                        : 'var(--widget-text-color)',
                    }}
                  >
                    {location.city.toUpperCase()}, {location.countryCode}
                  </span>
                  <span
                    style={{
                      fontSize: '9px',
                      color: geoIconColor,
                      animation: isRefreshing ? 'radarSweepSpin 0.8s linear infinite' : 'none',
                      display: 'inline-block',
                      lineHeight: 1,
                    }}
                    title={geoTooltip}
                  >
                    {geoIcon}
                  </span>
                </button>
              </div>

              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>LATITUDE:</span>
                <span className="info-value font-mono">
                  {Math.abs(location.lat).toFixed(4)}° {location.lat >= 0 ? 'N' : 'S'}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>LONGITUDE:</span>
                <span className="info-value font-mono">
                  {Math.abs(location.lon).toFixed(4)}° {location.lon >= 0 ? 'E' : 'W'}
                </span>
              </div>

              {/* GPS source badge */}
              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>SRC:</span>
                <span
                  className="info-value font-mono"
                  style={{
                    fontSize: '8.5px',
                    color: usingGPS ? themeColorEnv : '#ffaa00',
                    letterSpacing: '1px',
                  }}
                >
                  {usingGPS ? '● GPS LOCK' : '● IP APPROX'}
                </span>
              </div>
            </div>

            {/* Radar hud visualizer */}
            <div className="radar-wrapper">
              <div className="radar-circle" style={{ borderColor: `${themeColorEnv}33` }}>
                <div className="radar-sweep" style={{ background: `conic-gradient(from 0deg at 50% 50%, transparent 60%, ${themeColorEnv}55 100%)` }} />
                <div className="radar-center-dot" style={{ backgroundColor: themeColorEnv, boxShadow: `0 0 6px ${themeColorEnv}` }} />
                <div className="radar-grid-line h" style={{ backgroundColor: `${themeColorEnv}22` }} />
                <div className="radar-grid-line v" style={{ backgroundColor: `${themeColorEnv}22` }} />
                <div className="radar-ping" style={{ borderColor: themeColorEnv, boxShadow: `0 0 8px ${themeColorEnv}` }} />
              </div>
              <div className="radar-coordinates font-mono" style={{ color: themeColorEnv }}>
                {geoStatus === 'granted'
                  ? `${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}`
                  : geoStatus === 'requesting'
                    ? 'ACQUIRING LOCK...'
                    : geoStatus === 'denied'
                      ? 'ACCESS DENIED'
                      : 'SCANNING SIGNAL LOCK'
                }
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. HARDWARE LINK STATE WIDGET */}
      <div
        className={`sci-fi-widget-container${dragConn ? ' draggable-active' : ''}`}
        style={connStyle}
        onMouseDown={handleMouseDownConn}
      >
        <div className="sci-fi-widget-capsule">
          <div className="widget-scanline" />
          <div className="widget-header">
            <span className="widget-header-text" style={{ color: 'var(--widget-theme-color)' }}>
              {connWidgetSettings.titleText || 'HARDWARE LINK STATE'}
            </span>
            <span className="widget-header-sub" style={{ color: 'var(--widget-theme-color)', opacity: 0.7 }}>SYS-06</span>
          </div>

          <div className="widget-content" style={{ color: 'var(--widget-text-color)' }}>
            {/* Battery percentage */}
            <div className="battery-section">
              <div className="widget-info-header">
                <span className="info-label" style={{ opacity: 0.6 }}>POWER MODULE</span>
                <span className="info-value font-mono" style={{ color: themeColorConn }}>{battery.percent}%</span>
              </div>
              <div className="battery-bar-container" style={{ borderColor: `${themeColorConn}44` }}>
                <div
                  className={`battery-level-bar ${battery.power_plugged ? 'charging' : ''}`}
                  style={{
                    width: `${battery.percent}%`,
                    backgroundColor: battery.percent < 20 ? '#ff3366' : battery.percent < 50 ? '#ffcc00' : themeColorConn,
                    boxShadow: `0 0 8px ${battery.percent < 20 ? '#ff3366' : battery.percent < 50 ? '#ffcc00' : themeColorConn}aa`
                  }}
                />
                {battery.power_plugged && (
                  <span className="charging-lightning font-mono" style={{ color: themeColorConn }}>⚡ CONNECTED</span>
                )}
              </div>
            </div>

            <div className="divider-glow" style={{ background: `linear-gradient(90deg, transparent, ${themeColorConn}66, transparent)`, margin: '12px 0 8px 0' }} />

            {/* WiFi and Bluetooth stats */}
            <div className="info-grid">
              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>WI-FI LINK:</span>
                <span className={`info-value font-mono ${network.wifi.connected ? 'status-green' : 'status-red'}`}>
                  {network.wifi.connected ? 'ACTIVE' : 'OFFLINE'}
                </span>
              </div>
              {network.wifi.connected && (
                <div className="info-row">
                  <span className="info-label" style={{ paddingLeft: '8px', opacity: 0.4 }}>SSID:</span>
                  <span className="info-value font-mono text-truncate" style={{ maxWidth: '110px' }}>
                    {network.wifi.ssid}
                  </span>
                </div>
              )}

              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>BLUETOOTH:</span>
                <span className={`info-value font-mono ${network.bluetooth.enabled ? 'status-green' : 'status-orange'}`}>
                  {network.bluetooth.enabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>

              <div className="info-row">
                <span className="info-label" style={{ opacity: 0.6 }}>GATEWAY PING:</span>
                <span className="info-value font-mono status-cyan">
                  {ping ? `${ping} MS` : 'CALCULATING...'}
                </span>
              </div>
            </div>

            {/* Transmission rates bar simulation */}
            <div className="metrics-readout font-mono">
              <div className="metric-bar-group">
                <span className="label" style={{ opacity: 0.5 }}>DATA TX:</span>
                <div className="mini-progress-bar" style={{ backgroundColor: `${themeColorConn}22` }}>
                  <div className="bar" style={{ width: '42%', backgroundColor: themeColorConn }} />
                </div>
              </div>
              <div className="metric-bar-group">
                <span className="label" style={{ opacity: 0.5 }}>DATA RX:</span>
                <div className="mini-progress-bar" style={{ backgroundColor: `${themeColorConn}22` }}>
                  <div className="bar" style={{ width: '71%', backgroundColor: themeColorConn }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
