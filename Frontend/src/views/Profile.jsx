import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import authService from '../lib/auth'

export default function Profile() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)

  useEffect(() => {
    const currentUser = authService.getUser()
    setUser(currentUser)
  }, [])

  const handleLogout = () => {
    authService.logout()
    navigate('/login')
  }

  if (!user) {
    return (
      <section className="page">
        <div className="empty-state">Loading profile...</div>
      </section>
    )
  }

  return (
    <section className="page">
      <div className="page__header">
        <div>
          <h2>User Profile</h2>
          <p>Your account information and permissions</p>
        </div>
        <button className="button button--ghost" onClick={handleLogout}>
          Sign Out
        </button>
      </div>

      <div className="panel">
        <div className="profile-section">
          <h3>Account Details</h3>
          <div className="profile-grid">
            <div className="profile-field">
              <label>Username</label>
              <span>{user.username}</span>
            </div>
            <div className="profile-field">
              <label>Email</label>
              <span>{user.email || 'Not set'}</span>
            </div>
            <div className="profile-field">
              <label>Account Status</label>
              <span className={`chip ${user.is_active ? 'chip--success' : 'chip--error'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </div>

        <div className="profile-section">
          <h3>Roles & Permissions</h3>
          <div className="chip-row">
            {user.roles && user.roles.length > 0 ? (
              user.roles.map((role) => (
                <span key={role} className="chip chip--accent">
                  {role}
                </span>
              ))
            ) : (
              <span className="chip">No roles assigned</span>
            )}
          </div>

          {user.roles && user.roles.includes('admin') && (
            <div className="alert alert--info" style={{ marginTop: '1rem' }}>
              <strong>Administrator Access</strong>
              <p>You have full access to all SafeLink features including user management and system configuration.</p>
            </div>
          )}

          {user.roles && user.roles.includes('operator') && (
            <div className="alert alert--info" style={{ marginTop: '1rem' }}>
              <strong>Operator Access</strong>
              <p>You can create and approve mitigation actions, manage alerts, and configure threat intelligence.</p>
            </div>
          )}

          {user.roles && user.roles.includes('viewer') && !user.roles.includes('admin') && !user.roles.includes('operator') && (
            <div className="alert alert--warning" style={{ marginTop: '1rem' }}>
              <strong>Viewer Access</strong>
              <p>You have read-only access. Contact an administrator to request additional permissions.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
