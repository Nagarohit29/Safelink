import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Dashboard from './views/Dashboard'
import Alerts from './views/Alerts'
import Attackers from './views/Attackers'
import Sniffer from './views/Sniffer'
import Login from './views/Login'
import Register from './views/Register'
import Profile from './views/Profile'
import Mitigation from './views/Mitigation'
import ProtectedRoute from './components/ProtectedRoute'
import authService from './lib/auth'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/attackers', label: 'Attackers' },
  { to: '/sniffer', label: 'Sniffer' },
  { to: '/mitigation', label: 'Mitigation' },
]

export default function App() {
  const isAuthenticated = authService.isAuthenticated()
  
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" replace /> : <Login />
        } />
        <Route path="/register" element={
          isAuthenticated ? <Navigate to="/" replace /> : <Register />
        } />
        
        {/* Protected routes */}
        <Route path="/*" element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}

function AppShell() {
  const handleLogout = () => {
    authService.logout()
    window.location.href = '/login'
  }
  
  return (
    <div className="shell">
      <aside className="shell__sidebar">
        <div className="brand">
          <div className="brand__logo">SL</div>
          <div>
            <div className="brand__name">SafeLink</div>
            <div className="brand__tagline">Network Defense Center</div>
          </div>
        </div>
        <nav className="nav">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav__link${isActive ? ' nav__link--active' : ''}`}
            >
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <NavLink to="/profile" className="nav__link">
            👤 Profile
          </NavLink>
          <button className="nav__link" onClick={handleLogout} style={{ border: 'none', background: 'none', cursor: 'pointer', width: '100%', textAlign: 'left' }}>
            🚪 Sign Out
          </button>
        </div>
      </aside>
      <div className="shell__main">
        <header className="shell__header">
          <h1>SafeLink Security Console</h1>
          <p>Monitor spoofing attempts, review attackers, and orchestrate the ARP sniffer in real time.</p>
        </header>
        <main className="shell__content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/attackers" element={<Attackers />} />
            <Route path="/sniffer" element={<Sniffer />} />
            <Route path="/mitigation" element={<Mitigation />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
