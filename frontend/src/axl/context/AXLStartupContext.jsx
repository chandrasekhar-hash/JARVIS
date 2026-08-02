import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAXLRouter, ROUTE_STATES } from './AXLRouterContext';
import { useAXLAuth } from './AXLAuthContext';
import { fetchWithAuth } from '../services/apiInterceptor';

const AXLStartupContext = createContext();

export const AXLStartupProvider = ({ children }) => {
  const { navigateTo } = useAXLRouter();
  const { checkSession } = useAXLAuth();

  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Initializing Application Experience Layer...');
  const [subsystemStates, setSubsystemStates] = useState({});

  const startBootPipeline = async () => {
    try {
      // Phase 1: Pre-Flight Health Check & Maintenance Check
      setStatusMessage('Checking backend health & version compatibility...');
      setProgress(15);

      const healthRes = await fetchWithAuth('/health');
      if (healthRes.status === 503) {
        const mData = await healthRes.json();
        navigateTo(ROUTE_STATES.MAINTENANCE, { maintenance: mData });
        return;
      }

      if (!healthRes.ok) {
        throw new Error('Backend health check failed. System unreachable.');
      }

      const healthData = await healthRes.json();
      setSubsystemStates(healthData.subsystems || {});
      setProgress(30);

      // Phase 2: Session Restoration
      setStatusMessage('Restoring authentication session...');
      const hasValidSession = await checkSession();
      setProgress(50);

      if (!hasValidSession) {
        navigateTo(ROUTE_STATES.UNAUTHENTICATED);
        return;
      }

      // Phase 3: Ingest Parallel Core Subsystems
      setStatusMessage('Loading core subsystems (Memory, Plugins, Workspace)...');
      setProgress(75);

      await Promise.allSettled([
        fetchWithAuth('/identity'),
        fetchWithAuth('/plugins'),
        fetchWithAuth('/desktop/apps')
      ]);

      // Phase 4: Finalize & Open Dashboard
      setStatusMessage('Finalizing engines & rendering dashboard...');
      setProgress(100);

      setTimeout(() => {
        navigateTo(ROUTE_STATES.AUTHENTICATED);
      }, 400);

    } catch (err) {
      console.error('AXL Startup Pipeline Error:', err);
      navigateTo(ROUTE_STATES.DIAGNOSTICS_ERROR, { error: err.message });
    }
  };

  useEffect(() => {
    startBootPipeline();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AXLStartupContext.Provider value={{ progress, statusMessage, subsystemStates, retryBoot: startBootPipeline }}>
      {children}
    </AXLStartupContext.Provider>
  );
};

export const useAXLStartup = () => useContext(AXLStartupContext);
