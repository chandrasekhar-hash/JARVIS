import React, { useEffect, useRef } from 'react';
import { cameraController } from '../services/CameraController';

export function CameraSessionOverlay({
  isSessionActive,
  activeFocus,
  statusText,
  sceneChanged,
  latestAnalysis,
  error,
  isProcessing,
  onStartSession,
  onEndSession,
  onSendPrompt
}) {
  const videoContainerRef = useRef(null);

  useEffect(() => {
    if (isSessionActive && cameraController.videoElement && videoContainerRef.current) {
      videoContainerRef.current.innerHTML = '';
      cameraController.videoElement.style.width = '100%';
      cameraController.videoElement.style.height = '100%';
      cameraController.videoElement.style.objectFit = 'cover';
      cameraController.videoElement.style.borderRadius = '12px';
      videoContainerRef.current.appendChild(cameraController.videoElement);
    }
  }, [isSessionActive]);

  if (!isSessionActive) {
    return (
      <div style={{ padding: '16px', background: 'rgba(20, 20, 25, 0.85)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h4 style={{ margin: 0, color: '#e0e0e5' }}>Vision Session (V7 Camera)</h4>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#a0a0b0' }}>Conversational Camera Assistant</p>
          </div>
          <button
            onClick={onStartSession}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              background: '#00e5ff',
              color: '#000',
              fontWeight: 'bold',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            Start Camera Session
          </button>
        </div>
        {error && <p style={{ color: '#ff5252', fontSize: '12px', marginTop: '8px' }}>{error}</p>}
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', background: 'rgba(15, 15, 20, 0.95)', borderRadius: '16px', border: '1px solid rgba(0, 229, 255, 0.3)', padding: '16px', boxSizing: 'border-box' }}>
      {/* Video Preview Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: sceneChanged ? '#ff9100' : '#00e676', display: 'inline-block' }}></span>
          <span style={{ color: '#fff', fontSize: '13px', fontWeight: '500' }}>{statusText}</span>
        </div>
        {activeFocus && (
          <div style={{ background: 'rgba(0, 229, 255, 0.15)', color: '#00e5ff', padding: '4px 10px', borderRadius: '20px', fontSize: '12px', border: '1px solid rgba(0, 229, 255, 0.4)' }}>
            Focus: {activeFocus}
          </div>
        )}
        <button
          onClick={onEndSession}
          style={{
            padding: '6px 12px',
            borderRadius: '6px',
            background: 'rgba(255, 82, 82, 0.2)',
            color: '#ff5252',
            border: '1px solid rgba(255, 82, 82, 0.4)',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          End Session
        </button>
      </div>

      {/* Video Stream Container */}
      <div
        ref={videoContainerRef}
        style={{
          width: '100%',
          height: '240px',
          background: '#000',
          borderRadius: '12px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      />

      {/* Latest Analysis Output */}
      {latestAnalysis && (
        <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '8px', color: '#e0e0e5', fontSize: '13px' }}>
          <strong style={{ color: '#00e5ff' }}>J.A.R.V.I.S.:</strong> {latestAnalysis.text}
        </div>
      )}
    </div>
  );
}
