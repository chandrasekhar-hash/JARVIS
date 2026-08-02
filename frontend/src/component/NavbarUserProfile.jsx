import React from 'react';
import { useAXLAuth } from '../axl/context/AXLAuthContext';
import { useAXLRouter, ROUTE_STATES } from '../axl/context/AXLRouterContext';
import './NavbarUserProfile.css';

export default function NavbarUserProfile() {
  const { user } = useAXLAuth();
  const { currentRoute, navigateTo } = useAXLRouter();

  const handleUserClick = () => {
    if (currentRoute === ROUTE_STATES.PROFILE) {
      navigateTo(ROUTE_STATES.AUTHENTICATED);
    } else {
      navigateTo(ROUTE_STATES.PROFILE);
    }
  };

  const displayName = user?.display_name || user?.displayName || user?.username || 'User';

  const getInitials = (name) => {
    if (!name || typeof name !== 'string') return 'J';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const initials = getInitials(displayName);
  const isActive = currentRoute === ROUTE_STATES.PROFILE;

  return (
    <div className="nav-user-profile-wrapper">
      <button
        type="button"
        className={`nav-user-btn ${isActive ? 'active' : ''}`}
        onClick={handleUserClick}
        aria-label="User profile page"
        title={`View profile for ${displayName}`}
      >
        <div className="user-avatar-circle">
          <span>{initials}</span>
        </div>
        <span className="user-display-name">{displayName}</span>
        <svg
          className={`user-caret ${isActive ? 'open' : ''}`}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </div>
  );
}
