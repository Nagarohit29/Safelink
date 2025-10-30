import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import authService from '../lib/auth'

export default function Register() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    // Clear error for this field
    setErrors({
      ...errors,
      [e.target.name]: ''
    })
  }

  const validate = () => {
    const newErrors = {}

    if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters'
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    return newErrors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    const validationErrors = validate()
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)
    setErrors({})

    try {
      const result = await authService.register(
        formData.username,
        formData.email,
        formData.password
      )
      if (result.success) {
        navigate('/login')
      } else {
        setErrors({
          submit: result.error || 'Registration failed. Please try again.'
        })
      }
    } catch (err) {
      setErrors({
        submit: err.response?.data?.detail || 'Registration failed. Please try again.'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-card__header">
          <div className="brand">
            <div className="brand__logo">SL</div>
            <div>
              <div className="brand__name">SafeLink</div>
              <div className="brand__tagline">Network Defense Center</div>
            </div>
          </div>
          <h2>Create Account</h2>
          <p>Register for SafeLink access</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {errors.submit && (
            <div className="alert alert--error">
              {errors.submit}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              autoFocus
              disabled={loading}
              className={`form-control ${errors.username ? 'form-control--error' : ''}`}
            />
            {errors.username && (
              <span className="form-error">{errors.username}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              disabled={loading}
              className={`form-control ${errors.email ? 'form-control--error' : ''}`}
            />
            {errors.email && (
              <span className="form-error">{errors.email}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              disabled={loading}
              className={`form-control ${errors.password ? 'form-control--error' : ''}`}
            />
            {errors.password && (
              <span className="form-error">{errors.password}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              disabled={loading}
              className={`form-control ${errors.confirmPassword ? 'form-control--error' : ''}`}
            />
            {errors.confirmPassword && (
              <span className="form-error">{errors.confirmPassword}</span>
            )}
          </div>

          <button 
            type="submit" 
            className="button button--primary button--full-width"
            disabled={loading}
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>

          <div className="auth-form__footer">
            <p>Already have an account? <Link to="/login">Sign in</Link></p>
          </div>
        </form>
      </div>
    </div>
  )
}
