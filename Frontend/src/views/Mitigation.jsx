import React, { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'
import authService from '../lib/auth'

const formatDateTime = (val) => {
  if (!val) return '—'
  try {
    return new Date(val).toLocaleString()
  } catch (err) {
    return val
  }
}

export default function Mitigation() {
  const [actions, setActions] = useState([])
  const [whitelist, setWhitelist] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('actions')
  const [showRequestModal, setShowRequestModal] = useState(false)
  const [showWhitelistModal, setShowWhitelistModal] = useState(false)
  const [requestForm, setRequestForm] = useState({
    ip_address: '',
    reason: '',
    backend: 'snmp'
  })
  const [whitelistForm, setWhitelistForm] = useState({
    ip_address: '',
    reason: ''
  })

  const canManageMitigation = authService.hasPermission('mitigation:create')
  const canApproveMitigation = authService.hasPermission('mitigation:approve')

  const fetchActions = useCallback(() => {
    api
      .get('/mitigation/actions')
      .then((r) => setActions(r.data))
      .catch(() => setActions([]))
      .finally(() => setLoading(false))
  }, [])

  const fetchWhitelist = useCallback(() => {
    api
      .get('/mitigation/whitelist')
      .then((r) => setWhitelist(r.data))
      .catch(() => setWhitelist([]))
  }, [])

  useEffect(() => {
    fetchActions()
    fetchWhitelist()
    const interval = setInterval(() => {
      fetchActions()
      fetchWhitelist()
    }, 10000)
    return () => clearInterval(interval)
  }, [fetchActions, fetchWhitelist])

  const handleRequestSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/mitigation/request', requestForm)
      setShowRequestModal(false)
      setRequestForm({ ip_address: '', reason: '', backend: 'snmp' })
      fetchActions()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create mitigation request')
    }
  }

  const handleApprove = async (actionId) => {
    try {
      await api.post(`/mitigation/approve/${actionId}`)
      fetchActions()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to approve mitigation')
    }
  }

  const handleExecute = async (actionId) => {
    try {
      await api.post(`/mitigation/execute/${actionId}`)
      fetchActions()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to execute mitigation')
    }
  }

  const handleWhitelistSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/mitigation/whitelist', whitelistForm)
      setShowWhitelistModal(false)
      setWhitelistForm({ ip_address: '', reason: '' })
      fetchWhitelist()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add to whitelist')
    }
  }

  const handleRemoveWhitelist = async (whitelistId) => {
    if (!window.confirm('Remove this IP from whitelist?')) return
    try {
      await api.delete(`/mitigation/whitelist/${whitelistId}`)
      fetchWhitelist()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to remove from whitelist')
    }
  }

  return (
    <section className="page">
      <div className="page__header">
        <div>
          <h2>Threat Mitigation</h2>
          <p>Manage automated blocking and isolation of threats</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          {canManageMitigation && (
            <>
              <button className="button button--ghost" onClick={() => setShowWhitelistModal(true)}>
                Add Whitelist
              </button>
              <button className="button button--primary" onClick={() => setShowRequestModal(true)}>
                Request Mitigation
              </button>
            </>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'actions' ? 'tab--active' : ''}`}
            onClick={() => setActiveTab('actions')}
          >
            Mitigation Actions
          </button>
          <button
            className={`tab ${activeTab === 'whitelist' ? 'tab--active' : ''}`}
            onClick={() => setActiveTab('whitelist')}
          >
            Whitelist
          </button>
        </div>

        {activeTab === 'actions' && (
          <div>
            {loading ? (
              <div className="empty-state">Loading actions...</div>
            ) : actions.length === 0 ? (
              <div className="empty-state">No mitigation actions yet.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Backend</th>
                    <th>Status</th>
                    <th>Requested</th>
                    <th>Reason</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {actions.map((action) => (
                    <tr key={action.id}>
                      <td>{action.ip_address}</td>
                      <td>
                        <span className="chip">{action.backend}</span>
                      </td>
                      <td>
                        <span className={`chip chip--${
                          action.status === 'completed' ? 'success' :
                          action.status === 'failed' ? 'error' :
                          action.status === 'approved' ? 'accent' :
                          'default'
                        }`}>
                          {action.status}
                        </span>
                      </td>
                      <td>{formatDateTime(action.requested_at)}</td>
                      <td>{action.reason}</td>
                      <td>
                        {action.status === 'pending' && canApproveMitigation && (
                          <button
                            className="button button--small button--primary"
                            onClick={() => handleApprove(action.id)}
                          >
                            Approve
                          </button>
                        )}
                        {action.status === 'approved' && canManageMitigation && (
                          <button
                            className="button button--small button--accent"
                            onClick={() => handleExecute(action.id)}
                          >
                            Execute
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'whitelist' && (
          <div>
            {whitelist.length === 0 ? (
              <div className="empty-state">Whitelist is empty.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Added</th>
                    <th>Reason</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {whitelist.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.ip_address}</td>
                      <td>{formatDateTime(entry.added_at)}</td>
                      <td>{entry.reason}</td>
                      <td>
                        {canManageMitigation && (
                          <button
                            className="button button--small button--ghost"
                            onClick={() => handleRemoveWhitelist(entry.id)}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Request Mitigation Modal */}
      {showRequestModal && (
        <div className="modal-overlay" onClick={() => setShowRequestModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3>Request Mitigation Action</h3>
              <button className="modal__close" onClick={() => setShowRequestModal(false)}>×</button>
            </div>
            <form onSubmit={handleRequestSubmit}>
              <div className="form-group">
                <label>IP Address</label>
                <input
                  type="text"
                  className="form-control"
                  value={requestForm.ip_address}
                  onChange={(e) => setRequestForm({ ...requestForm, ip_address: e.target.value })}
                  placeholder="192.168.1.100"
                  required
                />
              </div>
              <div className="form-group">
                <label>Mitigation Backend</label>
                <select
                  className="form-control"
                  value={requestForm.backend}
                  onChange={(e) => setRequestForm({ ...requestForm, backend: e.target.value })}
                >
                  <option value="snmp">SNMP (Switch Port Disable)</option>
                  <option value="ssh">SSH (Router/Switch Config)</option>
                  <option value="firewall">Firewall API</option>
                </select>
              </div>
              <div className="form-group">
                <label>Reason</label>
                <textarea
                  className="form-control"
                  value={requestForm.reason}
                  onChange={(e) => setRequestForm({ ...requestForm, reason: e.target.value })}
                  placeholder="ARP spoofing detected from this IP"
                  rows="3"
                  required
                />
              </div>
              <div className="modal__footer">
                <button type="button" className="button button--ghost" onClick={() => setShowRequestModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="button button--primary">
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Whitelist Modal */}
      {showWhitelistModal && (
        <div className="modal-overlay" onClick={() => setShowWhitelistModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3>Add to Whitelist</h3>
              <button className="modal__close" onClick={() => setShowWhitelistModal(false)}>×</button>
            </div>
            <form onSubmit={handleWhitelistSubmit}>
              <div className="form-group">
                <label>IP Address</label>
                <input
                  type="text"
                  className="form-control"
                  value={whitelistForm.ip_address}
                  onChange={(e) => setWhitelistForm({ ...whitelistForm, ip_address: e.target.value })}
                  placeholder="192.168.1.1"
                  required
                />
              </div>
              <div className="form-group">
                <label>Reason</label>
                <textarea
                  className="form-control"
                  value={whitelistForm.reason}
                  onChange={(e) => setWhitelistForm({ ...whitelistForm, reason: e.target.value })}
                  placeholder="Gateway router - should never be blocked"
                  rows="3"
                  required
                />
              </div>
              <div className="modal__footer">
                <button type="button" className="button button--ghost" onClick={() => setShowWhitelistModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="button button--primary">
                  Add to Whitelist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  )
}
