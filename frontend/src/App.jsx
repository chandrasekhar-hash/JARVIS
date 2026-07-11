import React, { useState } from 'react';
import Navbar from './component/Navbar';
import Bob from './component/bob';
import Terminal from './component/Terminal';
import { AssistantConfigProvider } from './context/AssistantConfigContext';
import './App.css';

function App() {
  // 1. Color State (Default: Hyper Cyan Theme, loads from storage if set)
  const [blobColor, setBlobColor] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-color');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return {
      name: 'Hyper Cyan',
      deep: '#001433',
      mid: '#0084ff',
      bright: '#00ffe1',
      shell: '#0066ff'
    };
  });

  // 2. Size State (Default: 240px, loads from storage if set)
  const [blobSize, setBlobSize] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-size');
    if (saved) {
      const val = parseInt(saved, 10);
      if (!isNaN(val)) return val;
    }
    return 240;
  });

  // 3. Drag Settings State
  const [isDraggable, setIsDraggable] = useState(false);
  const [blobPosition, setBlobPosition] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-position');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return null; // Calculated on mount inside bob.jsx
  });

  // 4. J.A.R.V.I.S Text Customizations
  const [jarvisFont, setJarvisFont] = useState(() => {
    return localStorage.getItem('jarvis-text-font') || "'Orbitron', sans-serif";
  });

  const [jarvisColor, setJarvisColor] = useState(() => {
    return localStorage.getItem('jarvis-text-color') || '';
  });

  const [jarvisFontSize, setJarvisFontSize] = useState(() => {
    const saved = localStorage.getItem('jarvis-text-size');
    if (saved) {
      const val = parseInt(saved, 10);
      if (!isNaN(val)) return val;
    }
    return 24; // Default font size
  });

  const [jarvisTextPosition, setJarvisTextPosition] = useState(() => {
    const saved = localStorage.getItem('jarvis-text-position');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return null; // Null means relatively attached to the blob
  });

  const [isTextDraggable, setIsTextDraggable] = useState(false);

  // 5. Blob Audio Sensitivity (Default: 3.6, loads from storage if set)
  const [blobSensitivity, setBlobSensitivity] = useState(() => {
    const saved = localStorage.getItem('jarvis-blob-sensitivity');
    if (saved) {
      const val = parseFloat(saved);
      if (!isNaN(val)) return val;
    }
    return 3.6;
  });

  // 6. Terminal Settings State
  const [terminalSettings, setTerminalSettings] = useState(() => {
    const saved = localStorage.getItem('jarvis-terminal-settings');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return {
          width: 720,
          height: 60,
          borderRadius: 12,
          bgOpacity: 0.85,
          borderGlow: 0.45,
          draggable: true,
          position: null,
          colorTheme: '#00ff66',
          ...parsed
        };
      } catch (e) {}
    }
    return {
      width: 720,
      height: 60,
      borderRadius: 12,
      bgOpacity: 0.85,
      borderGlow: 0.45,
      draggable: true,
      position: null,
      colorTheme: '#00ff66'
    };
  });

  return (
    <AssistantConfigProvider>
      <div className="app-wrapper">
        {/* Dynamic Cosmic Background Elements */}
        <div className="cosmic-glow cosmic-glow-1"></div>
        <div className="cosmic-glow cosmic-glow-2"></div>

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
    </AssistantConfigProvider>
  );
}

export default App;

