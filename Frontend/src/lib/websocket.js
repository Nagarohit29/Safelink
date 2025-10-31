// WebSocket client for real-time updates
import { API_BASE_URL } from './api'

class WebSocketClient {
  constructor() {
    this.ws = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.heartbeatInterval = null
  }

  connect(token = null) {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/updates'
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.emit('connected', { timestamp: new Date() })
      }
      
      this.ws.onmessage = (event) => {
        try {
          // Handle plain text messages (like "pong" for heartbeat)
          if (event.data === 'pong') {
            return // Ignore pong responses
          }
          
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.stopHeartbeat()
        this.emit('disconnected', { timestamp: new Date() })
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
    }
  }

  disconnect() {
    if (this.ws) {
      this.stopHeartbeat()
      this.ws.close()
      this.ws = null
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, 30000) // Send ping every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
      setTimeout(() => this.connect(), this.reconnectDelay)
    } else {
      console.error('Max reconnect attempts reached')
      this.emit('reconnect_failed', { attempts: this.reconnectAttempts })
    }
  }

  handleMessage(data) {
    const { type, data: payload } = data
    
    switch (type) {
      case 'new_alert':
        this.emit('alert', payload)
        break
      case 'sniffer_status':
        this.emit('sniffer_status', payload)
        break
      case 'mitigation_update':
        this.emit('mitigation', payload)
        break
      default:
        this.emit('message', data)
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in ${event} listener:`, error)
        }
      })
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

// Singleton instance
const wsClient = new WebSocketClient()

export default wsClient
