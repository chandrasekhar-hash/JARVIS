import React, { useState, useEffect, useRef } from 'react';
import { useAssistantConfig } from '../context/AssistantConfigContext';
import './Status.css';

export default function Status() {
  const { assistantName, voiceStatus, statusSettings, updateStatusSetting } = useAssistantConfig();
  const [micPermission, setMicPermission] = useState('prompt');
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [localDragPosition, setLocalDragPosition] = useState(null);
  const localDragPositionRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!statusSettings.draggable && isDragging) {
      setIsDragging(false);
    }
  }, [statusSettings.draggable, isDragging]);

  // Check Groq API Connectivity
  const isApiConnected = !!import.meta.env.VITE_GROQ_API_KEY;

  // Track Microphone Browser Permission Status
  useEffect(() => {
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'microphone' })
        .then((permissionStatus) => {
          setMicPermission(permissionStatus.state);
          permissionStatus.onchange = () => {
            setMicPermission(permissionStatus.state);
          };
        })
        .catch(() => {
          setMicPermission('prompt');
        });
    } else {
      setMicPermission('prompt');
    }
  }, []);

  // Map Voice Status to human-readable strings and color classes
  const getAssistantStatusText = () => {
    switch (voiceStatus) {
      case 'standby': return 'STANDBY';
      case 'active': return 'ACTIVE';
      case 'processing': return 'PROCESSING';
      case 'responding': return 'RESPONDING';
      case 'paused': return 'MUTED';
      case 'error': return 'ERROR';
      default: return 'ONLINE';
    }
  };

  const getAssistantStatusClass = () => {
    switch (voiceStatus) {
      case 'standby': return 'status-green';
      case 'active': return 'status-cyan';
      case 'processing': return 'status-yellow';
      case 'responding': return 'status-blue';
      case 'paused': return 'status-orange';
      case 'error': return 'status-red';
      default: return 'status-green';
    }
  };

  const getMicStatusText = () => {
    if (voiceStatus === 'paused') return 'MUTED';
    if (voiceStatus === 'error') return 'OFFLINE';
    return 'LISTENING';
  };

  const getMicStatusClass = () => {
    if (voiceStatus === 'paused') return 'status-orange';
    if (voiceStatus === 'error') return 'status-red';
    return 'status-green';
  };

  // Dragging event handlers
  const handleMouseDown = (e) => {
    if (!statusSettings.draggable) return;
    // Don't drag if user is highlighting text in input/select
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'BUTTON') return;

    setIsDragging(true);
    
    // Fallback to top-right CSS positioning if position isn't saved yet
    const currentX = statusSettings.position ? statusSettings.position.x : (window.innerWidth - 250 - 24);
    const currentY = statusSettings.position ? statusSettings.position.y : 90;

    setDragStart({
      x: e.clientX - currentX,
      y: e.clientY - currentY
    });
    
    localDragPositionRef.current = { x: currentX, y: currentY };
    setLocalDragPosition({ x: currentX, y: currentY });
    
    e.preventDefault();
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      const x = e.clientX - dragStart.x;
      const y = e.clientY - dragStart.y;
      localDragPositionRef.current = { x, y };
      setLocalDragPosition({ x, y });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      if (localDragPositionRef.current) {
        updateStatusSetting('position', localDragPositionRef.current);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStart]);

  // Generate positioning style
  const positionStyle = (isDragging && localDragPosition)
    ? {
        position: 'fixed',
        left: `${localDragPosition.x}px`,
        top: `${localDragPosition.y}px`,
        right: 'auto',
        margin: 0
      }
    : statusSettings.position
    ? {
        position: 'fixed',
        left: `${statusSettings.position.x}px`,
        top: `${statusSettings.position.y}px`,
        right: 'auto',
        margin: 0
      }
    : {
        position: 'fixed',
        top: '90px',
        right: '24px'
      };

  const dragCursorStyle = statusSettings.draggable
    ? { cursor: isDragging ? 'grabbing' : 'grab' }
    : {};

  const capsuleStyle = {
    ...positionStyle,
    ...dragCursorStyle,
    '--status-theme-color': statusSettings.colorTheme || '#00ff66',
    '--status-text-color': statusSettings.textColor || '#ffffff',
    borderColor: statusSettings.colorTheme ? `${statusSettings.colorTheme}44` : undefined,
    boxShadow: statusSettings.colorTheme
      ? `0 0 15px rgba(0, 0, 0, 0.6), 
         0 0 15px ${statusSettings.colorTheme}1a inset, 
         0 0 10px ${statusSettings.colorTheme}0d`
      : undefined
  };

  return (
    <div 
      ref={containerRef}
      className={`sci-fi-status-container ${statusSettings.draggable ? 'draggable-active' : ''}`}
      style={capsuleStyle}
      onMouseDown={handleMouseDown}
    >
      <div className="sci-fi-status-capsule">
        <div className="status-scanline" />
        <div className="status-header">
          <span className="status-header-text" style={{ color: 'var(--status-theme-color)' }}>
            {statusSettings.titleText || 'SYSTEM STATUS MATRIX'}
          </span>
          <div className="status-header-glow" style={{ backgroundColor: 'var(--status-theme-color)' }} />
        </div>
        
        <div className="status-grid" style={{ color: 'var(--status-text-color)' }}>
          {/* 1. Core System */}
          <div className="status-item">
            <span className="status-label" style={{ color: 'var(--status-text-color)', opacity: 0.6 }}>SYS CORE</span>
            <div className="status-indicator-wrapper">
              <span className="status-value status-green font-mono">ONLINE</span>
              <span className="status-dot pulse-green" />
            </div>
          </div>

          {/* 2. J.A.R.V.I.S State */}
          <div className="status-item">
            <span className="status-label" style={{ color: 'var(--status-text-color)', opacity: 0.6 }}>{assistantName.toUpperCase()} MODULE</span>
            <div className="status-indicator-wrapper">
              <span className={`status-value font-mono ${getAssistantStatusClass()}`}>
                {getAssistantStatusText()}
              </span>
              <span className={`status-dot pulse-${getAssistantStatusClass().split('-')[1]}`} />
            </div>
          </div>

          {/* 3. Microphone Input */}
          <div className="status-item">
            <span className="status-label" style={{ color: 'var(--status-text-color)', opacity: 0.6 }}>AUDIO INPUT</span>
            <div className="status-indicator-wrapper">
              <span className={`status-value font-mono ${getMicStatusClass()}`}>
                {getMicStatusText()}
              </span>
              <span className={`status-dot pulse-${getMicStatusClass().split('-')[1]}`} />
            </div>
          </div>

          {/* 4. Mic Permission */}
          <div className="status-item">
            <span className="status-label" style={{ color: 'var(--status-text-color)', opacity: 0.6 }}>MIC ACCESS</span>
            <div className="status-indicator-wrapper">
              <span className={`status-value font-mono ${
                micPermission === 'granted' ? 'status-green' : 
                micPermission === 'denied' ? 'status-red' : 'status-yellow'
              }`}>
                {micPermission.toUpperCase()}
              </span>
              <span className={`status-dot ${
                micPermission === 'granted' ? 'pulse-green' : 
                micPermission === 'denied' ? 'pulse-red' : 'pulse-yellow'
              }`} />
            </div>
          </div>

          {/* 5. Groq API */}
          <div className="status-item">
            <span className="status-label" style={{ color: 'var(--status-text-color)', opacity: 0.6 }}>API GATEWAY</span>
            <div className="status-indicator-wrapper">
              <span className={`status-value font-mono ${isApiConnected ? 'status-green' : 'status-red'}`}>
                {isApiConnected ? 'AUTHORIZED' : 'MISSING'}
              </span>
              <span className={`status-dot ${isApiConnected ? 'pulse-green' : 'pulse-red'}`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
