/* oxlint-disable react/only-export-components */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchWithAuth } from '../services/apiInterceptor';
import { useAXLRouter, ROUTE_STATES } from './AXLRouterContext';

const AXLAuthContext = createContext();

export const AXLAuthProvider = ({ children }) => {
  const { navigateTo } = useAXLRouter();
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [welcomePlayedThisSession, setWelcomePlayedThisSession] = useState(false);

  const updateVisitorHint = (userObj) => {
    if (!userObj) return;
    const name = userObj.display_name || userObj.displayName || userObj.username;
    if (name && typeof name === 'string' && name.trim()) {
      try {
        localStorage.setItem('jarvis_visitor_hint', JSON.stringify({
          displayName: name.trim(),
          knownUser: true
        }));
      } catch (_) {}
    }
  };

  const checkSession = async () => {
    try {
      setAuthLoading(true);
      const res = await fetchWithAuth('/session/refresh', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
        setIsAuthenticated(true);
        updateVisitorHint(data.user);
        return true;
      } else {
        setUser(null);
        setIsAuthenticated(false);
        return false;
      }
    } catch (e) {
      setUser(null);
      setIsAuthenticated(false);
      return false;
    } finally {
      setAuthLoading(false);
    }
  };

  const login = async (username, password, rememberMe = false) => {
    try {
      const res = await fetchWithAuth('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password, remember_me: rememberMe }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 403 && errData.detail && errData.detail.toLowerCase().includes('not verified')) {
          const customError = new Error(errData.detail);
          customError.isUnverified = true;
          customError.unverifiedEmail = errData.email || username;
          throw customError;
        }
        throw new Error(errData.detail || 'Invalid email/username or password.');
      }
      const data = await res.json();
      setUser(data.user);
      setIsAuthenticated(true);
      updateVisitorHint(data.user);
      return data;
    } catch (err) {
      if (err.isUnverified) {
        throw err;
      }
      if (err.message && (err.message.includes('unavailable') || err.message.includes('timed out'))) {
        throw err;
      }
      throw new Error(err.message || 'Invalid email/username or password.');
    }
  };

  const register = async (username, email, password) => {
    try {
      const res = await fetchWithAuth('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail;
        let msg = 'Registration failed.';
        if (typeof detail === 'string') {
          msg = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          msg = detail[0].msg || 'Registration failed.';
        }
        throw new Error(msg);
      }
      const data = await res.json();
      if (data && data.user) {
        updateVisitorHint(data.user);
      }
      return data;
    } catch (err) {
      if (err.message && (err.message.includes('unavailable') || err.message.includes('timed out'))) {
        throw err;
      }
      throw err;
    }
  };

  const forgotPassword = async (email) => {
    return { message: 'Account recovery is currently unavailable.' };
  };

  const updateProfile = async (displayName, newUsername) => {
    const body = {};
    if (displayName !== undefined && displayName !== null) body.display_name = displayName;
    if (newUsername !== undefined && newUsername !== null) body.username = newUsername;
    const res = await fetchWithAuth('/auth/profile', {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update profile.');
    }
    const data = await res.json();
    setUser(data.user);
    updateVisitorHint(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      await fetchWithAuth('/session/logout', { method: 'POST' });
    } catch (e) {}
    setUser(null);
    setIsAuthenticated(false);
    try {
      navigateTo(ROUTE_STATES.UNAUTHENTICATED);
    } catch (_) {}
  };

  return (
    <AXLAuthContext.Provider value={{
      user, 
      isAuthenticated, 
      authLoading, 
      welcomePlayedThisSession, 
      setWelcomePlayedThisSession, 
      checkSession, 
      login, 
      register, 
      forgotPassword,
      updateProfile,
      logout,
      fetchWithAuth
    }}>
      {children}
    </AXLAuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAXLAuth = () => useContext(AXLAuthContext);
