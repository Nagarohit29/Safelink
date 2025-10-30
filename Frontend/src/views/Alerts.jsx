import React, { useEffect, useState, useCallback } from 'react'
import api, { API_BASE_URL } from '../lib/api'
import wsClient from '../lib/websocket'

const formatDateTime = (val) => {
  if (!val) return '—'
  try {
    return new Date(val).toLocaleString()
  } catch (err) {
    return val
  }
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)
  const [archiveAfterDownload, setArchiveAfterDownload] = useState(true)
  const [stats, setStats] = useState(null)
  const [showArchived, setShowArchived] = useState(false)
  const [archivedAlerts, setArchivedAlerts] = useState([])

  const fetchAlerts = useCallback(() => {
    setLoading(true)
    api
      .get('/alerts/latest', { params: { limit: 50 } })
      .then((r) => setAlerts(r.data))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false))
  }, [])

  const fetchStats = useCallback(() => {
    api
      .get('/alerts/stats/management')
      .then((r) => setStats(r.data))
      .catch((e) => console.error('Failed to fetch stats:', e))
  }, [])

  const fetchArchivedAlerts = useCallback((daysBack = 30) => {
    setLoading(true)
    api
      .get('/alerts/archived', { params: { days_back: daysBack, limit: 1000 } })
      .then((r) => setArchivedAlerts(r.data.alerts || []))
      .catch((e) => {
        console.error('Failed to fetch archived alerts:', e)
        setArchivedAlerts([])
      })
      .finally(() => setLoading(false))
  }, [])

  const handleDownloadCSV = () => {
    const url = `${API_BASE_URL}/alerts/download?archive_after_download=${archiveAfterDownload}`
    window.open(url, '_blank')
    
    if (archiveAfterDownload) {
      setTimeout(() => {
        fetchAlerts()
        fetchStats()
      }, 1000)
    }
  }

  const handleArchiveAll = () => {
    // Check if there are any alerts to archive
    if (alerts.length === 0) {
      alert('No alerts to archive. The logs are empty.')
      return
    }
    
    if (!confirm('Archive all current alerts? They will be moved to the archive table.')) return
    
    api.post('/alerts/archive', { archive_reason: 'manual_clear' })
      .then(() => {
        alert('All alerts archived successfully!')
        fetchAlerts()
        fetchStats()
      })
      .catch((e) => alert('Failed to archive alerts: ' + e.message))
  }

  const handleRotateOld = () => {
    const days = prompt('Archive alerts older than how many days?', '30')
    if (!days) return
    
    api.post('/alerts/rotate', null, { params: { days_to_keep: parseInt(days) } })
      .then((r) => {
        alert(`Archived ${r.data.archived} old alerts!`)
        fetchAlerts()
        fetchStats()
      })
      .catch((e) => alert('Failed to rotate alerts: ' + e.message))
  }

  const toggleArchivedView = () => {
    if (!showArchived) {
      fetchArchivedAlerts()
    }
    setShowArchived(!showArchived)
  }

  useEffect(() => {
    fetchAlerts()
    fetchStats()
    
    // Connect WebSocket for real-time alerts
    wsClient.connect()
    
    // Check initial connection state
    setWsConnected(wsClient.isConnected())
    
    const handleConnect = () => setWsConnected(true)
    const handleDisconnect = () => setWsConnected(false)
    
    // Add new alert to the top of the list when received
    const handleNewAlert = (alert) => {
      setAlerts((prev) => [alert, ...prev.slice(0, 49)])
      fetchStats() // Update stats when new alert arrives
    }
    
    wsClient.on('connected', handleConnect)
    wsClient.on('disconnected', handleDisconnect)
    wsClient.on('alert', handleNewAlert)
    
    // Fallback polling (less frequent)
    const id = setInterval(() => {
      fetchAlerts()
      fetchStats()
    }, 30000)
    
    return () => {
      clearInterval(id)
      wsClient.off('connected', handleConnect)
      wsClient.off('disconnected', handleDisconnect)
      wsClient.off('alert', handleNewAlert)
      // Don't disconnect WebSocket - it's a singleton used across all pages
    }
  }, [])

  const currentAlerts = showArchived ? archivedAlerts : alerts

  return (
    <section className="page">
      <div className="page__header">
        <div>
          <h2>Live Alert Feed</h2>
          <p>Real-time alerts via WebSocket connection.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span className={`chip ${wsConnected ? 'chip--success' : 'chip--error'}`}>
            {wsConnected ? '🟢 Live' : '🔴 Disconnected'}
          </span>
          <button className="button button--ghost" onClick={fetchAlerts}>
            Refresh
          </button>
        </div>
      </div>

      {/* Alert Management Panel */}
      <div className="panel" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>Alert Management</h3>
        
        {/* Statistics */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ padding: '1rem', background: '#f0f7ff', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e40af' }}>{stats.active_count}</div>
              <div style={{ color: '#64748b' }}>Active Alerts</div>
            </div>
            <div style={{ padding: '1rem', background: '#f0fdf4', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#15803d' }}>{stats.archived_count}</div>
              <div style={{ color: '#64748b' }}>Archived Alerts</div>
            </div>
            <div style={{ padding: '1rem', background: '#fef3f2', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc2626' }}>{stats.total_count}</div>
              <div style={{ color: '#64748b' }}>Total Alerts</div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <button className="button button--primary" onClick={handleDownloadCSV}>
            📥 Download CSV
          </button>
          <button className="button button--ghost" onClick={handleArchiveAll}>
            📦 Archive All Alerts
          </button>
          <button className="button button--ghost" onClick={handleRotateOld}>
            🔄 Rotate Old Alerts
          </button>
          <button className="button button--ghost" onClick={toggleArchivedView}>
            {showArchived ? '📋 View Active' : '📚 View Archived'}
          </button>
        </div>

        {/* Archive Option Toggle */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={archiveAfterDownload}
            onChange={(e) => setArchiveAfterDownload(e.target.checked)}
          />
          <span>Archive alerts after downloading CSV (recommended for production)</span>
        </label>
      </div>

      {/* Alerts Table */}
      <div className="panel">
        <div style={{ marginBottom: '1rem', fontWeight: 'bold' }}>
          {showArchived ? '📚 Archived Alerts' : '📋 Active Alerts'} ({currentAlerts.length})
        </div>

        {loading && currentAlerts.length === 0 ? (
          <div className="empty-state">Loading alerts…</div>
        ) : currentAlerts.length === 0 ? (
          <div className="empty-state">
            {showArchived ? 'No archived alerts found.' : 'No active alerts. System is monitoring...'}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Module</th>
                <th>Source IP</th>
                <th>Source MAC</th>
                <th>Reason</th>
                {showArchived && <th>Archived At</th>}
              </tr>
            </thead>
            <tbody>
              {currentAlerts.map((alert, idx) => (
                <tr key={alert.id || idx}>
                  <td>{formatDateTime(alert.timestamp)}</td>
                  <td>
                    <span className="chip chip--accent">{alert.module}</span>
                  </td>
                  <td>{alert.src_ip || '—'}</td>
                  <td>{alert.src_mac || '—'}</td>
                  <td>{alert.reason}</td>
                  {showArchived && <td>{formatDateTime(alert.archived_at)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
