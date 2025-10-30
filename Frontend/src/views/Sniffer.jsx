import React, { useEffect, useState, useCallback } from 'react'
import api from '../lib/api'
import wsClient from '../lib/websocket'
import ConnectionStatus from '../components/ConnectionStatus'

const prettySeconds = (seconds) => {
  if (!seconds) return '—'
  const minutes = Math.floor(seconds / 60)
  const hrs = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (hrs > 0) return `${hrs}h ${mins}m`
  if (mins > 0) return `${mins}m`
  return `${Math.floor(seconds)}s`
}

const formatDateTime = (value) => {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch (err) {
    return value
  }
}

export default function Sniffer() {
  const [status, setStatus] = useState(null)
  const [iface, setIface] = useState('')
  const [liveFeed, setLiveFeed] = useState([])
  const [loadingFeed, setLoadingFeed] = useState(true)

  const fetchStatus = useCallback(() => {
    api
      .get('/sniffer/status')
      .then((r) => setStatus(r.data))
      .catch(() => setStatus(null))
  }, [])

  const fetchLiveFeed = useCallback(() => {
    setLoadingFeed(true)
    api
      .get('/live-feed', { params: { limit: 10 } })
      .then((r) => {
        const items = Array.isArray(r.data) ? r.data : []
        // Ensure newest first by timestamp (descending)
        items.sort((a, b) => {
          const ta = a?.timestamp ? new Date(a.timestamp).getTime() : 0
          const tb = b?.timestamp ? new Date(b.timestamp).getTime() : 0
          return tb - ta
        })
        setLiveFeed(items)
      })
      .catch(() => setLiveFeed([]))
      .finally(() => setLoadingFeed(false))
  }, [])

  const start = () => {
    api
      .post('/sniffer/start', { interface: iface || null })
      .then((r) => setStatus(r.data))
      .catch((e) => alert(`Start failed: ${e.response?.data?.detail || e.message}`))
  }

  const stop = () => {
    api
      .post('/sniffer/stop')
      .then(() => fetchStatus())
      .catch((e) => alert(`Stop failed: ${e.response?.data?.detail || e.message}`))
  }

  useEffect(() => {
    fetchStatus()
    fetchLiveFeed()
    
    // Connect WebSocket
    wsClient.connect()
    
    // Listen for new alerts - add to live feed in real-time
    const handleNewAlert = (alert) => {
      console.log('New alert received:', alert)
      setLiveFeed((prev) => {
        // Add new alert to the top, keep max 10
        const updated = [alert, ...prev].slice(0, 10)
        return updated
      })
    }
    
    // Listen for sniffer status updates
    const handleSnifferStatus = (newStatus) => {
      setStatus(newStatus)
    }
    
    wsClient.on('alert', handleNewAlert)
    wsClient.on('sniffer_status', handleSnifferStatus)
    
    // Reduced polling frequency since WebSocket provides real-time updates
    const statusInterval = setInterval(fetchStatus, 10000)
    const feedInterval = setInterval(fetchLiveFeed, 15000)
    
    return () => {
      clearInterval(statusInterval)
      clearInterval(feedInterval)
      wsClient.off('alert', handleNewAlert)
      wsClient.off('sniffer_status', handleSnifferStatus)
    }
  }, [fetchStatus, fetchLiveFeed])

  const running = Boolean(status?.running)

  return (
    <section className="page">
      <div className="page__header">
        <div>
          <h2>Sniffer Orchestration</h2>
          <p>Control the real-time sniffer and inspect the latest packets flagged by SafeLink.</p>
        </div>
        <ConnectionStatus />
      </div>

      <div className="layout-vertical">
        <div className="panel panel--scrollx">
          <div className="panel__title">Controller</div>
          <div className="input-field">
            <label htmlFor="iface" style={{ fontWeight: 500 }}>
              Interface
            </label>
            <input
              id="iface"
              value={iface}
              onChange={(e) => setIface(e.target.value)}
              placeholder="e.g. vEthernet (External Switch)"
            />
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="button button--primary" onClick={start}>
              Start Sniffer
            </button>
            <button className="button button--muted" onClick={stop}>
              Stop Sniffer
            </button>
            <button className="button button--ghost" onClick={fetchStatus}>
              Check Status
            </button>
          </div>

          <div style={{ marginTop: '1.5rem' }}>
            <div className="panel__title" style={{ marginBottom: '1rem' }}>
              Current Status
            </div>
            <div className="status-box">
              <div className="status-row">
                <span>State</span>
                <span className={`chip ${running ? 'chip--success' : 'chip--muted'}`}>
                  {running ? 'Running' : 'Stopped'}
                </span>
              </div>
              <div className="status-row">
                <span>Interface</span>
                <strong>{status?.interface || 'Default'}</strong>
              </div>
              <div className="status-row">
                <span>Started</span>
                <span>{formatDateTime(status?.started_at)}</span>
              </div>
              <div className="status-row">
                <span>Uptime</span>
                <span>{prettySeconds(status?.uptime_seconds)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel__title">Recent Alert Feed</div>
          {loadingFeed && liveFeed.length === 0 ? (
            <div className="empty-state">Collecting packets…</div>
          ) : liveFeed.length === 0 ? (
            <div className="empty-state">No alerts captured yet.</div>
          ) : (
            <div className="table-scroll-x" role="region" aria-label="Recent alerts" tabIndex="0">
            <table className="table-feed">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Module</th>
                  <th>IP</th>
                  <th>MAC</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {liveFeed.map((entry) => (
                  <tr key={entry.id}>
                    <td title={entry.timestamp || ''}>{formatDateTime(entry.timestamp)}</td>
                    <td>{entry.module}</td>
                    <td>{entry.src_ip || '—'}</td>
                    <td className="mac-cell" title={entry.src_mac || ''}>{entry.src_mac || '—'}</td>
                    <td><div className="reason-text" title={entry.reason || ''}>{entry.reason}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
