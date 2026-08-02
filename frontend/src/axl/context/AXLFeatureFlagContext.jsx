import React, { createContext, useContext, useState } from 'react';

const AXLFeatureFlagContext = createContext();

export const AXLFeatureFlagProvider = ({ children }) => {
  const [flags, setFlags] = useState({
    ENABLE_VOICE: true,
    ENABLE_WORKSPACE: true,
    ENABLE_AUTOMATION: true,
    ENABLE_KNOWLEDGE: true,
    ENABLE_REASONING: true
  });

  const toggleFlag = (flagName) => {
    setFlags(prev => ({ ...prev, [flagName]: !prev[flagName] }));
  };

  const isEnabled = (flagName) => flags[flagName] ?? false;

  return (
    <AXLFeatureFlagContext.Provider value={{ flags, setFlags, toggleFlag, isEnabled }}>
      {children}
    </AXLFeatureFlagContext.Provider>
  );
};

export const useAXLFeatureFlags = () => useContext(AXLFeatureFlagContext);
