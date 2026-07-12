import React, { createContext, useContext, useState, useEffect } from 'react';

const AssistantConfigContext = createContext();

export function AssistantConfigProvider({ children }) {
  // Load assistantName from localStorage (using 'jarvis-text-content' for full backwards compatibility)
  const [assistantName, setAssistantName] = useState(() => {
    return localStorage.getItem('jarvis-text-content') || 'J.A.R.V.I.S';
  });

  // Load wakeWordRequired setting
  const [wakeWordRequired, setWakeWordRequiredState] = useState(() => {
    return localStorage.getItem('jarvis-wake-word-required') === 'true';
  });

  // Automatically derive wakeWords list whenever assistantName changes
  const [wakeWords, setWakeWords] = useState([]);

  useEffect(() => {
    const nameLower = assistantName.toLowerCase().replace(/[.\s]+/g, '').trim();
    if (!nameLower) {
      setWakeWords([]);
      return;
    }
    // Generate derived variations of the wake phrase
    const derived = [
      nameLower,
      `hey ${nameLower}`,
      `ok ${nameLower}`,
      `hello ${nameLower}`,
      `hi ${nameLower}`,
      `hey${nameLower}`,
      `ok${nameLower}`,
      `hi${nameLower}`
    ];
    setWakeWords(derived);
  }, [assistantName]);

  const [voiceStatus, setVoiceStatus] = useState('standby');

  const [statusSettings, setStatusSettingsState] = useState(() => {
    const saved = localStorage.getItem('jarvis-status-settings');
    if (saved) {
      try {
        return {
          draggable: false,
          position: null,
          colorTheme: '#00ff66',
          titleText: 'SYSTEM STATUS MATRIX',
          textColor: '#ffffff',
          ...JSON.parse(saved)
        };
      } catch (e) {}
    }
    return {
      draggable: false,
      position: null,
      colorTheme: '#00ff66',
      titleText: 'SYSTEM STATUS MATRIX',
      textColor: '#ffffff'
    };
  });

  const updateStatusSetting = (key, value) => {
    setStatusSettingsState(prev => {
      const updated = { ...prev, [key]: value };
      localStorage.setItem('jarvis-status-settings', JSON.stringify(updated));
      return updated;
    });
  };

  const [visualizerMode, setVisualizerModeState] = useState(() => {
    return localStorage.getItem('jarvis-visualizer-mode') || 'real';
  });

  const setVisualizerMode = (mode) => {
    setVisualizerModeState(mode);
    localStorage.setItem('jarvis-visualizer-mode', mode);
  };

  const updateAssistantName = (newName) => {
    setAssistantName(newName);
    localStorage.setItem('jarvis-text-content', newName);
  };

  const setWakeWordRequired = (required) => {
    setWakeWordRequiredState(required);
    localStorage.setItem('jarvis-wake-word-required', required ? 'true' : 'false');
  };

  return (
    <AssistantConfigContext.Provider value={{
      assistantName,
      updateAssistantName,
      wakeWordRequired,
      setWakeWordRequired,
      wakeWords,
      voiceStatus,
      setVoiceStatus,
      statusSettings,
      updateStatusSetting,
      visualizerMode,
      setVisualizerMode
    }}>
      {children}
    </AssistantConfigContext.Provider>
  );
}

export function useAssistantConfig() {
  const context = useContext(AssistantConfigContext);
  if (!context) {
    throw new Error('useAssistantConfig must be used within an AssistantConfigProvider');
  }
  return context;
}
