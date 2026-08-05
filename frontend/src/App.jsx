import React, { useState, lazy, Suspense } from 'react';
import Navbar from './component/Navbar';
import Bob from './component/bob';
import Terminal from './component/Terminal';
import Status from './component/Status';
import Widgets from './component/Widgets';
import { AssistantConfigProvider } from './context/AssistantConfigContext';

// Product 1.11 AXL Imports
import { AXLErrorBoundary } from './axl/components/AXLErrorBoundary';
import { AXLRouterProvider, useAXLRouter, ROUTE_STATES } from './axl/context/AXLRouterContext';
import { AXLAuthProvider } from './axl/context/AXLAuthContext';
import { AXLFeatureFlagProvider } from './axl/context/AXLFeatureFlagContext';
import { AXLStartupProvider } from './axl/context/AXLStartupContext';
import SplashScreen from './axl/components/SplashScreen';

// Code-split heavy views with React.lazy
const UserProfileView = lazy(() => import('./component/UserProfileView'));
const AuthView = lazy(() => import('./axl/components/AuthView'));
const SetupWizard = lazy(() => import('./axl/components/SetupWizard'));
const MaintenanceView = lazy(() => import('./axl/components/MaintenanceView'));
const DiagnosticsView = lazy(() => import('./axl/components/DiagnosticsView'));

import './App.css';

function MainDashboard({ 
  blobColor, setBlobColor, 
  blobSize, setBlobSize, 
  isDraggable, setIsDraggable, 
  blobPosition, setBlobPosition, 
  jarvisFont, setJarvisFont, 
  jarvisColor, setJarvisColor, 
  jarvisFontSize, setJarvisFontSize, 
  jarvisTextPosition, setJarvisTextPosition, 
  isTextDraggable, setIsTextDraggable, 
  blobSensitivity, setBlobSensitivity, 
  terminalSettings, setTerminalSettings 
}) {
  return (
    <div className="app-wrapper">
      {/* Dynamic Cosmic Background Elements */}
      <div className="cosmic-glow cosmic-glow-1"></div>
      <div className="cosmic-glow cosmic-glow-2"></div>

      <Status />
      <Widgets />

      <Navbar 
        blobColor={blobColor}
        setBlobColor={setBlobColor}
        blobSize={blobSize}
        setBlobSize={setBlobSize}
        isDraggable={isDraggable}
        setIsDraggable={setIsDraggable}
        blobPosition={blobPosition}
        setBlobPosition={setBlobPosition}
        jarvisFont={jarvisFont}
        setJarvisFont={setJarvisFont}
        jarvisColor={jarvisColor}
        setJarvisColor={setJarvisColor}
        jarvisFontSize={jarvisFontSize}
        setJarvisFontSize={setJarvisFontSize}
        jarvisTextPosition={jarvisTextPosition}
        setJarvisTextPosition={setJarvisTextPosition}
        isTextDraggable={isTextDraggable}
        setIsTextDraggable={setIsTextDraggable}
        blobSensitivity={blobSensitivity}
        setBlobSensitivity={setBlobSensitivity}
        terminalSettings={terminalSettings}
        setTerminalSettings={setTerminalSettings}
      />

      <main id="center" style={{ marginTop: '140px', padding: '0 24px' }}>
        <Bob 
          blobColor={blobColor}
          blobSize={blobSize}
          isDraggable={isDraggable}
          setIsDraggable={setIsDraggable}
          blobPosition={blobPosition}
          setBlobPosition={setBlobPosition}
          jarvisFont={jarvisFont}
          jarvisColor={jarvisColor}
          jarvisFontSize={jarvisFontSize}
          jarvisTextPosition={jarvisTextPosition}
          setJarvisTextPosition={setJarvisTextPosition}
          isTextDraggable={isTextDraggable}
          setIsTextDraggable={setIsTextDraggable}
          blobSensitivity={blobSensitivity}
        />
      </main>

      <footer className="app-footer">
        <div className="ticks"></div>
      </footer>

      {/* JARVIS Terminal — live speech recognition panel */}
      <Terminal 
        terminalSettings={terminalSettings}
        setTerminalSettings={setTerminalSettings}
      />
    </div>
  );
}

function AppContent() {
  const { currentRoute } = useAXLRouter();

  // State initialization for UI preferences
  const [blobColor, setBlobColor] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-color');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return { name: 'Hyper Cyan', deep: '#001433', mid: '#0084ff', bright: '#00ffe1', shell: '#0066ff' };
  });

  const [blobSize, setBlobSize] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-size');
    if (saved) { const val = parseInt(saved, 10); if (!isNaN(val)) return val; }
    return 240;
  });

  const [isDraggable, setIsDraggable] = useState(false);
  const [blobPosition, setBlobPosition] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-position');
    if (saved) { try { return JSON.parse(saved); } catch (e) {} }
    return null;
  });

  const [jarvisFont, setJarvisFont] = useState(() => localStorage.getItem('jarvis-text-font') || "'Orbitron', sans-serif");
  const [jarvisColor, setJarvisColor] = useState(() => localStorage.getItem('jarvis-text-color') || '');
  const [jarvisFontSize, setJarvisFontSize] = useState(() => {
    const saved = localStorage.getItem('jarvis-text-size');
    if (saved) { const val = parseInt(saved, 10); if (!isNaN(val)) return val; }
    return 24;
  });

  const [jarvisTextPosition, setJarvisTextPosition] = useState(() => {
    const saved = localStorage.getItem('jarvis-text-position');
    if (saved) { try { return JSON.parse(saved); } catch (e) {} }
    return null;
  });

  const [isTextDraggable, setIsTextDraggable] = useState(false);
  const [blobSensitivity, setBlobSensitivity] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-sensitivity');
    if (saved) { const val = parseFloat(saved); if (!isNaN(val)) return val; }
    return 3.6;
  });

  const [terminalSettings, setTerminalSettings] = useState(() => {
    const saved = localStorage.getItem('jarvis-terminal-settings');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { width: 720, height: 60, borderRadius: 12, bgOpacity: 0.85, borderGlow: 0.45, draggable: false, position: null, colorTheme: '#00ff66', ...parsed };
      } catch (e) {}
    }
    return { width: 720, height: 60, borderRadius: 12, bgOpacity: 0.85, borderGlow: 0.45, draggable: false, position: null, colorTheme: '#00ff66' };
  });

  switch (currentRoute) {
    case ROUTE_STATES.BOOTING:
      return <SplashScreen />;
    case ROUTE_STATES.WIZARD:
      return <SetupWizard />;
    case ROUTE_STATES.UNAUTHENTICATED:
      return <AuthView />;
    case ROUTE_STATES.MAINTENANCE:
      return <MaintenanceView />;
    case ROUTE_STATES.DIAGNOSTICS_ERROR:
      return <DiagnosticsView />;
    case ROUTE_STATES.PROFILE:
      return (
        <UserProfileView 
          blobColor={blobColor} setBlobColor={setBlobColor}
          blobSize={blobSize} setBlobSize={setBlobSize}
          isDraggable={isDraggable} setIsDraggable={setIsDraggable}
          blobPosition={blobPosition} setBlobPosition={setBlobPosition}
          jarvisFont={jarvisFont} setJarvisFont={setJarvisFont}
          jarvisColor={jarvisColor} setJarvisColor={setJarvisColor}
          jarvisFontSize={jarvisFontSize} setJarvisFontSize={setJarvisFontSize}
          jarvisTextPosition={jarvisTextPosition} setJarvisTextPosition={setJarvisTextPosition}
          isTextDraggable={isTextDraggable} setIsTextDraggable={setIsTextDraggable}
          blobSensitivity={blobSensitivity} setBlobSensitivity={setBlobSensitivity}
          terminalSettings={terminalSettings} setTerminalSettings={setTerminalSettings}
        />
      );
    case ROUTE_STATES.AUTHENTICATED:
    default:
      return (
        <MainDashboard 
          blobColor={blobColor} setBlobColor={setBlobColor}
          blobSize={blobSize} setBlobSize={setBlobSize}
          isDraggable={isDraggable} setIsDraggable={setIsDraggable}
          blobPosition={blobPosition} setBlobPosition={setBlobPosition}
          jarvisFont={jarvisFont} setJarvisFont={setJarvisFont}
          jarvisColor={jarvisColor} setJarvisColor={setJarvisColor}
          jarvisFontSize={jarvisFontSize} setJarvisFontSize={setJarvisFontSize}
          jarvisTextPosition={jarvisTextPosition} setJarvisTextPosition={setJarvisTextPosition}
          isTextDraggable={isTextDraggable} setIsTextDraggable={setIsTextDraggable}
          blobSensitivity={blobSensitivity} setBlobSensitivity={setBlobSensitivity}
          terminalSettings={terminalSettings} setTerminalSettings={setTerminalSettings}
        />
      );
  }
}

export default function App() {
  return (
    <AXLErrorBoundary>
      <AssistantConfigProvider>
        <AXLRouterProvider>
          <AXLAuthProvider>
            <AXLFeatureFlagProvider>
              <AXLStartupProvider>
                <Suspense fallback={<div style={{ color: '#00ff66', padding: 20 }}>Initializing...</div>}>
                  <AppContent />
                </Suspense>
              </AXLStartupProvider>
            </AXLFeatureFlagProvider>
          </AXLAuthProvider>
        </AXLRouterProvider>
      </AssistantConfigProvider>
    </AXLErrorBoundary>
  );
}
