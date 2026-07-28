import React, { useState, useEffect } from 'react';
import './Scheduler.css';

const API_BASE = 'http://localhost:8000';

export default function Scheduler() {
  const [metrics, setMetrics] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState('');
  const [scheduleExpr, setScheduleExpr] = useState('Every day at 08:00');
  const [jobDescription, setJobDescription] = useState('');
  const [historyJobId, setHistoryJobId] = useState(null);
  const [historyRecords, setHistoryRecords] = useState([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [actionMessage, setActionMessage] = useState('');

  const fetchSchedulerData = async () => {
    try {
      setLoading(true);
      const [resStatus, resJobs, resTasks] = await Promise.all([
        fetch(`${API_BASE}/api/scheduler/status`),
        fetch(`${API_BASE}/api/scheduler/jobs`),
        fetch(`${API_BASE}/api/scheduler/tasks`)
      ]);

      if (resStatus.ok) {
        const dataStatus = await resStatus.json();
        setMetrics(dataStatus);
      }
      if (resJobs.ok) {
        const dataJobs = await resJobs.json();
        setJobs(dataJobs.jobs || []);
      }
      if (resTasks.ok) {
        const dataTasks = await resTasks.json();
        setTasks(dataTasks.tasks || []);
        if (dataTasks.tasks?.length > 0 && !selectedTask) {
          setSelectedTask(dataTasks.tasks[0].name);
        }
      }
    } catch (err) {
      console.error('Error fetching scheduler data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedulerData();
    const timer = setInterval(fetchSchedulerData, 10000);
    return () => clearInterval(timer);
  }, []);

  const handleCreateJob = async (e) => {
    e.preventDefault();
    if (!selectedTask) return;

    try {
      const res = await fetch(`${API_BASE}/api/scheduler/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_name: selectedTask,
          schedule_expression: scheduleExpr,
          description: jobDescription || undefined
        })
      });
      if (res.ok) {
        setActionMessage('✅ Scheduled job created successfully!');
        setJobDescription('');
        fetchSchedulerData();
        setTimeout(() => setActionMessage(''), 3000);
      }
    } catch (err) {
      setActionMessage(`❌ Error creating job: ${err.message}`);
    }
  };

  const handleRunNow = async (jobId) => {
    try {
      setActionMessage(`⚡ Executing job ${jobId}...`);
      const res = await fetch(`${API_BASE}/api/scheduler/jobs/${jobId}/run`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`✅ Execution finished: Status ${data.execution?.status}`);
        fetchSchedulerData();
        setTimeout(() => setActionMessage(''), 4000);
      }
    } catch (err) {
      setActionMessage(`❌ Execution failed: ${err.message}`);
    }
  };

  const handleTogglePause = async (jobId, isPaused) => {
    const endpoint = isPaused ? 'resume' : 'pause';
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/jobs/${jobId}/${endpoint}`, { method: 'POST' });
      if (res.ok) {
        fetchSchedulerData();
      }
    } catch (err) {
      console.error(`Error toggling ${endpoint}:`, err);
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!window.confirm(`Are you sure you want to delete job '${jobId}'?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/jobs/${jobId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchSchedulerData();
      }
    } catch (err) {
      console.error('Error deleting job:', err);
    }
  };

  const handleViewHistory = async (jobId) => {
    try {
      setHistoryJobId(jobId);
      const res = await fetch(`${API_BASE}/api/scheduler/jobs/${jobId}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryRecords(data.history || []);
        setShowHistoryModal(true);
      }
    } catch (err) {
      console.error('Error fetching history:', err);
    }
  };

  const formatNextRun = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };

  return (
    <div className="scheduler-container">
      <div className="scheduler-header">
        <h2>⚡ Persistent Autonomous Scheduler</h2>
        <p>Proactive Intelligence & Proactive Background Workflow Automation</p>
        {actionMessage && <div className="scheduler-alert">{actionMessage}</div>}
      </div>

      {/* Metrics Header Cards */}
      {metrics && (
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-title">Total Jobs</span>
            <span className="metric-value">{metrics.total_jobs}</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Running Now</span>
            <span className="metric-value text-accent">{metrics.running_jobs}</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Completed</span>
            <span className="metric-value text-success">{metrics.completed_jobs}</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Failed</span>
            <span className="metric-value text-danger">{metrics.failed_jobs}</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Avg Latency</span>
            <span className="metric-value">{metrics.average_duration_seconds}s</span>
          </div>
        </div>
      )}

      {/* Schedule Creation Form */}
      <div className="scheduler-card">
        <h3>➕ Schedule Proactive Task</h3>
        <form onSubmit={handleCreateJob} className="scheduler-form">
          <div className="form-group">
            <label>Select Proactive Task:</label>
            <select value={selectedTask} onChange={(e) => setSelectedTask(e.target.value)}>
              {tasks.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name} ({t.category})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Schedule Expression (Natural Language or Interval):</label>
            <input
              type="text"
              value={scheduleExpr}
              onChange={(e) => setScheduleExpr(e.target.value)}
              placeholder="e.g. Every morning at 8, Every 30 minutes, Every weekday"
              required
            />
          </div>

          <div className="form-group">
            <label>Custom Description (Optional):</label>
            <input
              type="text"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Custom description for this scheduled job..."
            />
          </div>

          <button type="submit" className="btn-primary">
            Schedule Job
          </button>
        </form>
      </div>

      {/* Scheduled Jobs List */}
      <div className="scheduler-card">
        <h3>📋 Scheduled Jobs</h3>
        {loading && jobs.length === 0 ? (
          <div className="loading-spinner">Loading scheduler jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="empty-state">No scheduled jobs configured.</div>
        ) : (
          <div className="jobs-table-wrapper">
            <table className="jobs-table">
              <thead>
                <tr>
                  <th>Job ID / Task</th>
                  <th>Schedule</th>
                  <th>Status</th>
                  <th>Next Execution</th>
                  <th>Last Run</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id}>
                    <td>
                      <div className="job-name">{job.task_name}</div>
                      <div className="job-desc">{job.description}</div>
                    </td>
                    <td>
                      <span className="badge-expression">
                        {job.trigger?.expression || `${job.trigger?.interval_seconds}s`}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge status-${job.status}`}>
                        {job.status.toUpperCase()}
                      </span>
                    </td>
                    <td>{formatNextRun(job.next_run)}</td>
                    <td>{job.last_run ? formatNextRun(job.last_run) : 'Never'}</td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-action btn-run" onClick={() => handleRunNow(job.job_id)}>
                          Run Now
                        </button>
                        <button
                          className="btn-action btn-pause"
                          onClick={() => handleTogglePause(job.job_id, job.status === 'paused')}
                        >
                          {job.status === 'paused' ? 'Resume' : 'Pause'}
                        </button>
                        <button className="btn-action btn-history" onClick={() => handleViewHistory(job.job_id)}>
                          History
                        </button>
                        <button className="btn-action btn-delete" onClick={() => handleDeleteJob(job.job_id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* History Modal Overlay */}
      {showHistoryModal && (
        <div className="modal-overlay" onClick={() => setShowHistoryModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Execution History for {historyJobId}</h3>
              <button className="btn-close" onClick={() => setShowHistoryModal(false)}>
                ✖
              </button>
            </div>
            <div className="modal-body">
              {historyRecords.length === 0 ? (
                <p>No execution history logged for this job yet.</p>
              ) : (
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Started</th>
                      <th>Duration</th>
                      <th>Summary / Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyRecords.map((r) => (
                      <tr key={r.execution_id}>
                        <td>
                          <span className={`status-badge status-${r.status}`}>{r.status}</span>
                        </td>
                        <td>{formatNextRun(r.start_time)}</td>
                        <td>{r.duration_seconds ? `${r.duration_seconds}s` : 'N/A'}</td>
                        <td>{r.error_message || r.result_summary || 'Completed'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
