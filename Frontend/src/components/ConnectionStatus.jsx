import React, { useEffect, useState } from 'react'
import wsClient from '../lib/websocket'

/**
 * Connection Status Indicator
 * 
 * Displays real-time WebSocket connection status:
 * - Green: Connected
 * - Yellow: Connecting/Reconnecting
 * - Red: Disconnected
 */
export default function ConnectionStatus() {
  const [status, setStatus] = useState('connecting') // 'connected' | 'connecting' | 'disconnected'
  const [reconnectAttempts, setReconnectAttempts] = useState(0)

  useEffect(() => {
    // Check initial state
    if (wsClient.isConnected()) {
      setStatus('connected')
    } else {
      setStatus('connecting')
      // Attempt connection
      wsClient.connect()
    }

    // Event handlers
    const handleConnect = () => {
      setStatus('connected')
      setReconnectAttempts(0)
    }

    const handleDisconnect = () => {
      setStatus('disconnected')
    }

    const handleReconnecting = (attempt) => {
      setStatus('connecting')
      setReconnectAttempts(attempt || 0)
    }

    const handleError = (error) => {
      console.error('WebSocket error:', error)
      setStatus('disconnected')
    }

    // Subscribe to events
    wsClient.on('connected', handleConnect)
    wsClient.on('disconnected', handleDisconnect)
    wsClient.on('reconnecting', handleReconnecting)
    wsClient.on('error', handleError)

    // Cleanup
    return () => {
      wsClient.off('connected', handleConnect)
      wsClient.off('disconnected', handleDisconnect)
      wsClient.off('reconnecting', handleReconnecting)
      wsClient.off('error', handleError)
    }
  }, [])

  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          color: 'success',
          icon: '🟢',
          text: 'Live',
          title: 'WebSocket connected'
        }
      case 'connecting':
        return {
          color: 'warning',
          icon: '🟡',
          text: reconnectAttempts > 0 ? `Reconnecting (${reconnectAttempts})...` : 'Connecting...',
          title: `Attempting to connect${reconnectAttempts > 0 ? ` (attempt ${reconnectAttempts})` : ''}`
        }
      case 'disconnected':
        return {
          color: 'error',
          icon: '🔴',
          text: 'Disconnected',
          title: 'WebSocket disconnected - Click to reconnect'
        }
      default:
        return {
          color: 'default',
          icon: '⚪',
          text: 'Unknown',
          title: 'Connection status unknown'
        }
    }
  }

  const handleClick = () => {
    if (status === 'disconnected') {
      wsClient.connect()
      setStatus('connecting')
    }
  }

  const config = getStatusConfig()

  return (
    <span
      className={`chip chip--${config.color}`}
      title={config.title}
      onClick={handleClick}
      style={{ 
        cursor: status === 'disconnected' ? 'pointer' : 'default',
        userSelect: 'none'
      }}
    >
      {config.icon} {config.text}
    </span>
  )
}
