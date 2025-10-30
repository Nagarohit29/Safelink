import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import authService from '../lib/auth'

/**
 * Wrapper component that protects routes requiring authentication
 * Redirects to login if user is not authenticated
 */
export default function ProtectedRoute({ children, requiredPermission = null, requiredRole = null }) {
  const location = useLocation()
  const isAuthenticated = authService.isAuthenticated()
  
  if (!isAuthenticated) {
    // Redirect to login, saving the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Check for required permission
  if (requiredPermission && !authService.hasPermission(requiredPermission)) {
    return (
      <div className="page">
        <div className="alert alert--error">
          <h3>Access Denied</h3>
          <p>You do not have permission to view this page. Required permission: {requiredPermission}</p>
        </div>
      </div>
    )
  }

  // Check for required role
  if (requiredRole && !authService.hasRole(requiredRole)) {
    return (
      <div className="page">
        <div className="alert alert--error">
          <h3>Access Denied</h3>
          <p>You do not have the required role to view this page. Required role: {requiredRole}</p>
        </div>
      </div>
    )
  }

  return children
}
