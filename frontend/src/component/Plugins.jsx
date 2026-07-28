import React, { useState, useEffect } from 'react';
import './Plugins.css';

const API_BASE = 'http://localhost:8000/api';

const Plugins = () => {
  const [plugins, setPlugins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState({});

  const fetchPlugins = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/plugins`);
      if (!res.ok) throw new Error('Failed to fetch installed plugins');
      const data = await res.json();
      setPlugins(data.plugins || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
    const interval = setInterval(fetchPlugins, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleTogglePlugin = async (pluginId, currentEnabled) => {
    const action = currentEnabled ? 'disable' : 'enable';
    setActionLoading((prev) => ({ ...prev, [pluginId]: true }));
    try {
      const res = await fetch(`${API_BASE}/plugins/${pluginId}/${action}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`Failed to ${action} plugin ${pluginId}`);
      await fetchPlugins();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading((prev) => ({ ...prev, [pluginId]: false }));
    }
  };

  const handleReloadPlugin = async (pluginId) => {
    setActionLoading((prev) => ({ ...prev, [pluginId]: true }));
    try {
      const res = await fetch(`${API_BASE}/plugins/${pluginId}/reload`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`Failed to reload plugin ${pluginId}`);
      await fetchPlugins();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading((prev) => ({ ...prev, [pluginId]: false }));
    }
  };

  return (
    <div className="plugins-dashboard">
      <div className="plugins-header">
        <div className="plugins-title-container">
          <h2>🧩 Local Dynamic Plugin Framework</h2>
          <p className="plugins-subtitle">
            Manage locally installed J.A.R.V.I.S. plugin modules, permissions, and tool lifecycles.
          </p>
        </div>
        <button className="plugins-refresh-btn" onClick={fetchPlugins} disabled={loading}>
          {loading ? 'Refreshing...' : '🔄 Refresh Plugins'}
        </button>
      </div>

      {error && <div className="plugins-error-banner">⚠️ {error}</div>}

      {loading && plugins.length === 0 ? (
        <div className="plugins-loading-state">Loading installed plugins...</div>
      ) : plugins.length === 0 ? (
        <div className="plugins-empty-state">No local plugins installed under Backend/plugins_installed/</div>
      ) : (
        <div className="plugins-grid">
          {plugins.map((plugin) => {
            const manifest = plugin.manifest || {};
            const isEnabled = manifest.enabled;
            const isRunning = plugin.status === 'running' || plugin.status === 'loaded';
            const isFailed = plugin.status === 'failed';

            return (
              <div key={plugin.plugin_id} className={`plugin-card ${isFailed ? 'failed' : isEnabled ? 'active' : 'disabled'}`}>
                <div className="plugin-card-header">
                  <div className="plugin-info">
                    <span className="plugin-name">{manifest.name || plugin.plugin_id}</span>
                    <span className="plugin-version">v{manifest.version || '1.0.0'}</span>
                  </div>
                  <span className={`plugin-status-badge ${plugin.status}`}>
                    {plugin.status.toUpperCase()}
                  </span>
                </div>

                <p className="plugin-description">{manifest.description || 'No description provided.'}</p>

                <div className="plugin-metadata">
                  <div className="meta-row">
                    <span className="meta-label">Author:</span>
                    <span className="meta-value">{manifest.author || 'Local'}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-label">Category:</span>
                    <span className="meta-value badge-category">{manifest.category || 'utility'}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-label">Entry Point:</span>
                    <span className="meta-value code-font">{manifest.entry || 'main.py'}</span>
                  </div>
                </div>

                {manifest.permissions && manifest.permissions.length > 0 && (
                  <div className="plugin-permissions">
                    <span className="permissions-label">Permissions Required:</span>
                    <div className="permissions-tags">
                      {manifest.permissions.map((perm) => (
                        <span key={perm} className="permission-tag">
                          🔒 {perm}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {plugin.registered_tools && plugin.registered_tools.length > 0 && (
                  <div className="plugin-tools">
                    <span className="tools-label">Exported Tools:</span>
                    <div className="tools-tags">
                      {plugin.registered_tools.map((tool) => (
                        <span key={tool} className="tool-tag">
                          ⚙️ {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {plugin.error_message && (
                  <div className="plugin-error-msg">
                    ❌ <strong>Error:</strong> {plugin.error_message}
                  </div>
                )}

                <div className="plugin-actions">
                  <button
                    className={`plugin-btn toggle-btn ${isEnabled ? 'disable-btn' : 'enable-btn'}`}
                    onClick={() => handleTogglePlugin(plugin.plugin_id, isEnabled)}
                    disabled={actionLoading[plugin.plugin_id]}
                  >
                    {isEnabled ? '⏸️ Disable' : '▶️ Enable'}
                  </button>
                  <button
                    className="plugin-btn reload-btn"
                    onClick={() => handleReloadPlugin(plugin.plugin_id)}
                    disabled={actionLoading[plugin.plugin_id]}
                  >
                    🔄 Reload
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Plugins;
