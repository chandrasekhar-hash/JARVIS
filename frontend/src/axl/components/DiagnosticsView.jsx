import React, { useState, useEffect } from 'react';
import { useAXLRouter, ROUTE_STATES } from '../context/AXLRouterContext';
import { fetchWithAuth } from '../services/apiInterceptor';
import './DiagnosticsView.css';

export default function DiagnosticsView() {
  const { diagnosticsError } = useAXLRouter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDiagnostics = async () => {
    try {
      setLoading(true);
      const res = await fetchWithAuth('/diagnostics/system');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  return (
    <div className="diag-wrapper">
      <div className="diag-card">
        <h2>SYSTEM DIAGNOSTICS & TELEMETRY</h2>
        
        {diagnosticsError && (
          <div className="diag-error-box">
            <strong>CRITICAL BOOT ERROR:</strong> {diagnosticsError}
          </div>
        )}

        {loading ? (
          <p>Gathering subsystem health diagnostics...</p>
        ) : data ? (
          <div className="diag-metrics">
            <div className="diag-section">
              <h3>System Resource Usage</h3>
              <p>CPU Utilization: {data.system.cpu_percent}%</p>
              <p>RAM Memory Used: {data.system.ram_used_mb} MB / {data.system.ram_total_mb} MB</p>
              <p>Disk Usage: {data.system.disk_used_percent}%</p>
            </div>

            <div className="diag-section">
              <h3>Subsystem Statuses</h3>
              <div className="subsystem-grid">
                {Object.entries(data.subsystems || {}).map(([key, status]) => (
                  <div key={key} className={`subsystem-badge ${status}`}>
                    <span>{key}</span>
                    <strong>{status}</strong>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p>Failed to retrieve backend telemetry.</p>
        )}

        <button className="diag-btn" onClick={() => window.location.reload()}>REBOOT APPLICATION</button>
      </div>
    </div>
  );
}
