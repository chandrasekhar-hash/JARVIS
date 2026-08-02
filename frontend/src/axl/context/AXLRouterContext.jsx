/* oxlint-disable react/only-export-components */
import React, { createContext, useContext, useState, useEffect } from 'react';

export const ROUTE_STATES = {
  BOOTING: 'BOOTING',
  WIZARD: 'WIZARD',
  UNAUTHENTICATED: 'UNAUTHENTICATED',
  MAINTENANCE: 'MAINTENANCE',
  AUTHENTICATED: 'AUTHENTICATED',
  PROFILE: 'PROFILE',
  DIAGNOSTICS_ERROR: 'DIAGNOSTICS_ERROR'
};

const AXLRouterContext = createContext();

export const AXLRouterProvider = ({ children }) => {
  const [currentRoute, setCurrentRoute] = useState(ROUTE_STATES.BOOTING);
  const [maintenanceInfo, setMaintenanceInfo] = useState(null);
  const [diagnosticsError, setDiagnosticsError] = useState(null);

  const navigateTo = (route, meta = {}) => {
    if (meta.maintenance) setMaintenanceInfo(meta.maintenance);
    if (meta.error) setDiagnosticsError(meta.error);

    if (route === ROUTE_STATES.PROFILE) {
      if (window.location.hash !== '#profile') {
        window.history.pushState({ route: ROUTE_STATES.PROFILE }, '', '#profile');
      }
    } else if (route === ROUTE_STATES.AUTHENTICATED) {
      if (window.location.hash === '#profile') {
        window.history.pushState({ route: ROUTE_STATES.AUTHENTICATED }, '', window.location.pathname);
      }
    }

    setCurrentRoute(route);
  };

  useEffect(() => {
    const handlePopState = (event) => {
      const stateRoute = event.state?.route;
      const hash = window.location.hash;

      if (stateRoute === ROUTE_STATES.PROFILE || hash === '#profile') {
        setCurrentRoute((prev) => (prev === ROUTE_STATES.AUTHENTICATED || prev === ROUTE_STATES.PROFILE ? ROUTE_STATES.PROFILE : prev));
      } else if (stateRoute === ROUTE_STATES.AUTHENTICATED || !hash) {
        setCurrentRoute((prev) => (prev === ROUTE_STATES.PROFILE ? ROUTE_STATES.AUTHENTICATED : prev));
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return (
    <AXLRouterContext.Provider value={{ currentRoute, navigateTo, maintenanceInfo, diagnosticsError }}>
      {children}
    </AXLRouterContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAXLRouter = () => useContext(AXLRouterContext);
