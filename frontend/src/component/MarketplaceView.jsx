import React, { useState, useEffect } from 'react';

const MarketplaceView = () => {
  const [activeTab, setActiveTab] = useState('store');
  const [plugins, setPlugins] = useState([
    {
      id: 'plg_github_assistant',
      name: 'GitHub Copilot Assistant',
      version: '1.2.0',
      category: 'developer',
      author: 'JARVIS Official',
      rating: 4.9,
      downloads: 1420,
      description: 'Automates pull request reviews, commit summaries, and repository context sync.',
      capabilities: ['fs:read', 'net:outbound'],
      installed: true
    },
    {
      id: 'plg_slack_notifier',
      name: 'Slack Notification Dispatcher',
      version: '1.0.4',
      category: 'productivity',
      author: 'JARVIS Official',
      rating: 4.8,
      downloads: 980,
      description: 'Dispatches real-time assistant notifications and task completion alerts to Slack channels.',
      capabilities: ['net:outbound'],
      installed: false
    },
    {
      id: 'plg_notion_sync',
      name: 'Notion Workspace Sync',
      version: '2.0.1',
      category: 'productivity',
      author: 'Community',
      rating: 4.7,
      downloads: 750,
      description: 'Syncs notes, tasks, and memory summaries directly into Notion databases.',
      capabilities: ['fs:read', 'net:outbound', 'memory:read'],
      installed: false
    }
  ]);

  const [developerKeys, setDeveloperKeys] = useState([
    { id: 'key_1', name: 'Desktop CLI Key', prefix: 'jrv_live_a1b2', scopes: ['read:memory', 'write:tasks'], created: '2026-07-28' }
  ]);

  const [newKeyName, setNewKeyName] = useState('');

  const handleInstall = (pluginId) => {
    setPlugins(plugins.map(p => p.id === pluginId ? { ...p, installed: true, downloads: p.downloads + 1 } : p));
  };

  const handleUninstall = (pluginId) => {
    setPlugins(plugins.map(p => p.id === pluginId ? { ...p, installed: false } : p));
  };

  const handleCreateKey = () => {
    if (!newKeyName) return;
    const keyItem = {
      id: `key_${Date.now()}`,
      name: newKeyName,
      prefix: `jrv_live_${Math.random().toString(36).substring(2, 6)}`,
      scopes: ['read:memory', 'write:tasks'],
      created: new Date().toISOString().split('T')[0]
    };
    setDeveloperKeys([...developerKeys, keyItem]);
    setNewKeyName('');
  };

  return (
    <div style={{ padding: '24px', color: '#e0e6ed', fontFamily: 'Inter, sans-serif', maxWidth: '1100px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '700', color: '#00D8FF' }}>J.A.R.V.I.S. Ecosystem & Marketplace</h2>
          <p style={{ margin: '4px 0 0', color: '#8b9bb4', fontSize: '14px' }}>Discover plugins, manage permissions, and configure developer API keys.</p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '12px', borderBottom: '1px solid #1e293b', paddingBottom: '12px', marginBottom: '24px' }}>
        {['store', 'installed', 'webhooks', 'developer'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              textTransform: 'capitalize',
              backgroundColor: activeTab === tab ? '#00D8FF' : '#1e293b',
              color: activeTab === tab ? '#090d16' : '#94a3b8'
            }}
          >
            {tab === 'store' ? 'Marketplace Store' : tab === 'installed' ? 'Installed Plugins' : tab === 'webhooks' ? 'Outbound Webhooks' : 'Developer API Keys'}
          </button>
        ))}
      </div>

      {/* Store Tab */}
      {activeTab === 'store' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          {plugins.map(p => (
            <div key={p.id} style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h3 style={{ margin: 0, fontSize: '16px', color: '#f8fafc' }}>{p.name}</h3>
                  <span style={{ fontSize: '12px', backgroundColor: '#1e293b', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px' }}>v{p.version}</span>
                </div>
                <p style={{ fontSize: '13px', color: '#94a3b8', margin: '0 0 12px', height: '40px', overflow: 'hidden' }}>{p.description}</p>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
                  {p.capabilities.map(cap => (
                    <span key={cap} style={{ fontSize: '11px', backgroundColor: '#0284c715', color: '#38bdf8', border: '1px solid #0284c730', padding: '2px 6px', borderRadius: '4px' }}>{cap}</span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #1e293b' }}>
                <span style={{ fontSize: '12px', color: '#64748b' }}>⭐ {p.rating} | {p.downloads} downloads</span>
                {p.installed ? (
                  <button onClick={() => handleUninstall(p.id)} style={{ padding: '6px 12px', backgroundColor: '#ef444420', color: '#f87171', border: '1px solid #ef444440', borderRadius: '6px', cursor: 'pointer' }}>Uninstall</button>
                ) : (
                  <button onClick={() => handleInstall(p.id)} style={{ padding: '6px 12px', backgroundColor: '#00D8FF', color: '#090d16', fontWeight: '600', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>Install</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Installed Tab */}
      {activeTab === 'installed' && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', padding: '20px' }}>
          <h3 style={{ marginTop: 0, color: '#f8fafc' }}>Installed Plugins ({plugins.filter(p => p.installed).length})</h3>
          {plugins.filter(p => p.installed).map(p => (
            <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #1e293b' }}>
              <div>
                <strong style={{ color: '#f8fafc' }}>{p.name}</strong> <span style={{ color: '#64748b', fontSize: '12px' }}>(v{p.version})</span>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>Granted Capabilities: {p.capabilities.join(', ')}</div>
              </div>
              <button onClick={() => handleUninstall(p.id)} style={{ padding: '6px 12px', backgroundColor: '#ef444420', color: '#f87171', border: '1px solid #ef444440', borderRadius: '6px', cursor: 'pointer' }}>Disable / Uninstall</button>
            </div>
          ))}
        </div>
      )}

      {/* Webhooks Tab */}
      {activeTab === 'webhooks' && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', padding: '20px' }}>
          <h3 style={{ marginTop: 0, color: '#f8fafc' }}>Outbound Event Webhooks</h3>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Configure HMAC-SHA256 signed event dispatch endpoints for Zapier, Slack, or custom web services.</p>
          <div style={{ padding: '16px', backgroundColor: '#1e293b', borderRadius: '8px', color: '#38bdf8', fontSize: '13px' }}>
            Active Subscription: <strong>https://api.myapp.com/webhooks/jarvis</strong> (Events: <code>task_completed</code>, <code>sync_delta</code>)
          </div>
        </div>
      )}

      {/* Developer API Keys Tab */}
      {activeTab === 'developer' && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', padding: '20px' }}>
          <h3 style={{ marginTop: 0, color: '#f8fafc' }}>Developer API Keys</h3>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <input
              type="text"
              placeholder="Key Name (e.g. CLI Script Key)"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              style={{ flex: 1, padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc' }}
            />
            <button onClick={handleCreateKey} style={{ padding: '8px 16px', backgroundColor: '#00D8FF', color: '#090d16', fontWeight: '600', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>Generate API Key</button>
          </div>

          <div>
            {developerKeys.map(k => (
              <div key={k.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', backgroundColor: '#1e293b', borderRadius: '8px', marginBottom: '10px' }}>
                <div>
                  <strong style={{ color: '#f8fafc' }}>{k.name}</strong>
                  <div style={{ fontSize: '12px', color: '#38bdf8', marginTop: '2px' }}>Prefix: <code>{k.prefix}...</code></div>
                </div>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Created {k.created}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketplaceView;
