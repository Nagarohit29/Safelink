import React, { useEffect, useState, useCallback } from 'react'
import api from '../lib/api'
import wsClient from '../lib/websocket'
import ConnectionStatus from '../components/ConnectionStatus'

const formatDateTime = (ts) => {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch (err) {
    return ts
  }
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)
  const [snifferStatus, setSnifferStatus] = useState(null)
  const [learningStatus, setLearningStatus] = useState(null)

  const fetchStats = useCallback(() => {
    setLoading(true)
    Promise.all([
      api.get('/alerts/stats'),
      api.get('/learning/status').catch(() => ({ data: null }))
    ])
      .then(([alertsRes, learningRes]) => {
        setStats(alertsRes.data)
        setLearningStatus(learningRes.data)
      })
      .catch(() => {
        setStats(null)
        setLearningStatus(null)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchStats()
    
    // Connect WebSocket
    wsClient.connect()
    
    // Check initial connection state
    setWsConnected(wsClient.isConnected())
    
    // Listen for connection status
    const handleConnect = () => setWsConnected(true)
    const handleDisconnect = () => setWsConnected(false)
    
    // Listen for new alerts - refresh stats when new alert arrives
    const handleNewAlert = (alert) => {
      console.log('New alert received:', alert)
      fetchStats()
    }
    
    // Listen for sniffer status updates
    const handleSnifferStatus = (status) => {
      setSnifferStatus(status)
    }
    
    wsClient.on('connected', handleConnect)
    wsClient.on('disconnected', handleDisconnect)
    wsClient.on('alert', handleNewAlert)
    wsClient.on('sniffer_status', handleSnifferStatus)
    
    // Fallback polling (less frequent since WebSocket provides real-time updates)
    const interval = setInterval(fetchStats, 30000)
    
    return () => {
      clearInterval(interval)
      wsClient.off('connected', handleConnect)
      wsClient.off('disconnected', handleDisconnect)
      wsClient.off('alert', handleNewAlert)
      wsClient.off('sniffer_status', handleSnifferStatus)
      // Don't disconnect WebSocket - it's a singleton used across all pages
    }
  }, [])

  return (
    <section className="page">
      <div className="page__header">
        <div>
          <h2>Threat Overview</h2>
          <p>Key indicators summarising detection activity across SafeLink.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <ConnectionStatus />
          <button className="button button--ghost" onClick={fetchStats}>
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="skeleton" aria-hidden />
      ) : (
        <div className="panel">
          <div className="card-grid">
            <div className="metric-card">
              <span className="metric-card__label">Total Alerts Logged</span>
              <span className="metric-card__value">{stats?.total_alerts ?? '—'}</span>
              <span className="chip chip--accent">Since deployment</span>
            </div>
            <div className="metric-card">
              <span className="metric-card__label">Latest Alert</span>
              <span className="metric-card__value" style={{ fontSize: '1.2rem' }}>
                {formatDateTime(stats?.latest_alert)}
              </span>
              <span className="chip">Timestamp of last incident</span>
            </div>
            <div className="metric-card">
              <span className="metric-card__label">Detection Sources</span>
              <span className="metric-card__value" style={{ fontSize: '1.3rem' }}>
                {stats?.by_module ? Object.keys(stats.by_module).length : '0'}
              </span>
              <span className="chip">Active detection modules</span>
            </div>
            {snifferStatus && (
              <div className="metric-card">
                <span className="metric-card__label">Packet Sniffer</span>
                <span className={`chip chip--${snifferStatus.running ? 'success' : 'default'}`}>
                  {snifferStatus.running ? 'Running' : 'Stopped'}
                </span>
                {snifferStatus.interface && (
                  <span className="chip">Interface: {snifferStatus.interface}</span>
                )}
              </div>
            )}
            {learningStatus && learningStatus.enabled && (
              <div className="metric-card">
                <span className="metric-card__label">Continuous Learning</span>
                <span className={`chip chip--${learningStatus.is_training ? 'warning' : 'success'}`}>
                  {learningStatus.is_training ? '🔄 Training...' : '🤖 Active'}
                </span>
                <span className="chip">
                  {learningStatus.total_training_cycles || 0} cycles
                </span>
              </div>
            )}
          </div>

          <div style={{ marginTop: '2rem' }}>
            <div className="panel__title">Module Breakdown</div>
            {stats?.by_module && Object.keys(stats.by_module).length > 0 ? (
              <div className="chip-row">
                {Object.entries(stats.by_module).map(([module, count]) => (
                  <span key={module} className="chip chip--accent">
                    {module}: {count}
                  </span>
                ))}
              </div>
            ) : (
              <div className="empty-state">No alerts recorded yet.</div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
