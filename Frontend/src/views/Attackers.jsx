import React, { useEffect, useState, useCallback } from 'react'
import api from '../lib/api'

const formatDateTime = (value) => {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch (err) {
    return value
  }
}

export default function Attackers() {
  const [attackers, setAttackers] = useState([])
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(() => {
    setLoading(true)
    Promise.all([
      api.get('/alerts/attackers', { params: { limit: 50 } }),
      api.get('/network/devices', { params: { limit: 50 } }),
    ])
      .then(([attackersRes, devicesRes]) => {
        setAttackers(attackersRes.data || [])
        setDevices(devicesRes.data || [])
      })
      .catch(() => {
        setAttackers([])
        setDevices([])
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return (
    <section className="page">
      <div className="page__header">
        <div>
          <h2>Adversary Intelligence</h2>
          <p>Identify repeating offenders and track every device that triggered an alert.</p>
        </div>
        <button className="button button--ghost" onClick={fetchData}>
          Refresh
        </button>
      </div>

      <div className="layout-split">
        <div className="panel">
          <div className="panel__title">Suspected Attackers</div>
          {loading && attackers.length === 0 ? (
            <div className="empty-state">Loading attacker details…</div>
          ) : attackers.length === 0 ? (
            <div className="empty-state">No suspicious actors detected yet.</div>
          ) : (
            <div className="table-scroll-x">
              <table className="table-attackers">
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>MAC</th>
                    <th>Alerts</th>
                    <th>Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {attackers.map((attacker) => (
                    <tr key={`${attacker.src_ip}-${attacker.src_mac}`}>
                      <td>{attacker.src_ip || '—'}</td>
                      <td>{attacker.src_mac || '—'}</td>
                      <td>
                        <span className="chip chip--warning">{attacker.count}</span>
                      </td>
                      <td>{formatDateTime(attacker.last_seen)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel__title">Devices On Watch</div>
          {loading && devices.length === 0 ? (
            <div className="empty-state">Gathering device list…</div>
          ) : devices.length === 0 ? (
            <div className="empty-state">No device activity recorded yet.</div>
          ) : (
            <div className="list-grid">
              {devices.map((device) => (
                <div key={`${device.ip}-${device.mac}`} className="list-grid__item">
                  <div>
                    <strong>{device.ip || 'Unknown IP'}</strong>
                    <div style={{ color: 'var(--text-secondary)' }}>{device.mac || 'Unknown MAC'}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div>{device.alerts} alerts</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                      {formatDateTime(device.last_seen)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
