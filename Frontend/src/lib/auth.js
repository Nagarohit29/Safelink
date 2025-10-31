// Authentication service for SafeLink
import api from './api'

const TOKEN_KEY = 'safelink_token'
const REFRESH_TOKEN_KEY = 'safelink_refresh_token'
const USER_KEY = 'safelink_user'

class AuthService {
  constructor() {
    this.token = localStorage.getItem(TOKEN_KEY)
    this.refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    this.user = JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  }

  async login(username, password) {
    try {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      const { access_token, refresh_token } = response.data
      this.setToken(access_token)
      this.setRefreshToken(refresh_token)

      // Fetch user info
      await this.fetchUserInfo()

      return { success: true, user: this.user }
    } catch (error) {
      console.error('Login error:', error)
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      }
    }
  }

  async register(username, email, password, full_name = null) {
    try {
      const userData = {
        username,
        email,
        password,
        full_name
      }
      const response = await api.post('/auth/register', userData)
      return { success: true, user: response.data }
    } catch (error) {
      console.error('Registration error:', error)
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      }
    }
  }

  async fetchUserInfo() {
    try {
      const response = await api.get('/auth/me', {
        headers: this.getAuthHeader()
      })
      this.user = response.data
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      return this.user
    } catch (error) {
      console.error('Fetch user info error:', error)
      this.logout()
      throw error
    }
  }

  logout() {
    this.token = null
    this.refreshToken = null
    this.user = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  setToken(token) {
    this.token = token
    localStorage.setItem(TOKEN_KEY, token)
  }

  setRefreshToken(token) {
    this.refreshToken = token
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  }

  getToken() {
    return this.token
  }

  getRefreshToken() {
    return this.refreshToken
  }

  getAuthHeader() {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {}
  }

  isAuthenticated() {
    return !!this.token && !!this.user
  }

  getUser() {
    return this.user
  }

  hasPermission(permission) {
    if (!this.user || !this.user.roles) return false
    
    const permissionMap = {
      admin: ['read', 'write', 'delete', 'configure', 'mitigate'],
      operator: ['read', 'mitigate'],
      viewer: ['read']
    }

    return this.user.roles.some(role => {
      const permissions = permissionMap[role] || []
      return permissions.includes(permission)
    })
  }

  hasRole(role) {
    if (!this.user || !this.user.roles) return false
    return this.user.roles.includes(role)
  }

  isAdmin() {
    return this.hasRole('admin')
  }

  canMitigate() {
    return this.hasPermission('mitigate')
  }

  canConfigure() {
    return this.hasPermission('configure')
  }
}

// Singleton instance
const authService = new AuthService()

// Setup axios interceptor to add auth header
api.interceptors.request.use(
  config => {
    const token = authService.getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Setup response interceptor for auth errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      authService.logout()
      // Redirect to login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default authService
