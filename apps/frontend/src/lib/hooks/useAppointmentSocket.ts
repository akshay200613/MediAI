'use client'

import { useEffect, useRef, useCallback } from 'react'

export interface AppointmentWSEvent {
  event: 'appointment_created' | 'appointment_updated' | 'appointment_cancelled' | 'doctor_updated' | 'doctor_password_reset_requested'
  data?: any
  message?: string
}

const getWsBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const hostname = window.location.hostname || 'localhost'
    return `${protocol}//${hostname}:8000/api/v1/medai/ws/appointments`
  }
  return 'ws://localhost:8000/api/v1/medai/ws/appointments'
}

export function useAppointmentSocket(onEvent?: (event: AppointmentWSEvent) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const savedCallback = useRef(onEvent)

  useEffect(() => {
    savedCallback.current = onEvent
  }, [onEvent])

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return

    const token = sessionStorage.getItem('access_token')
    if (!token) return

    // Clean up existing socket if any
    if (wsRef.current) {
      wsRef.current.close(1000, 'Reconnecting')
      wsRef.current = null
    }

    const wsUrl = getWsBaseUrl()
    const fullUrl = `${wsUrl}?token=${encodeURIComponent(token)}`

    try {
      const ws = new WebSocket(fullUrl)
      wsRef.current = ws

      ws.onopen = () => {
        // Send initial ping to keep-alive
        try {
          ws.send('ping')
        } catch {}

        // Setup 20-second continuous heartbeat to prevent idle connection timeout
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send('ping')
            } catch {}
          }
        }, 20000)
      }

      ws.onmessage = (event) => {
        if (event.data === 'pong') return
        try {
          const parsed: AppointmentWSEvent = JSON.parse(event.data)
          if (parsed.event && savedCallback.current) {
            savedCallback.current(parsed)
          }
        } catch (err) {
          console.error('Failed to parse WebSocket event', err)
        }
      }

      ws.onclose = (e) => {
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }
        // Automatically reconnect after 3 seconds if not intentionally closed
        if (e.code !== 1000) {
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, 3000)
        }
      }

      ws.onerror = (err) => {
        console.warn('WebSocket connection error:', err)
        try {
          ws.close()
        } catch {}
      }
    } catch (err) {
      console.error('Failed to create WebSocket instance', err)
    }
  }, [])

  useEffect(() => {
    connect()

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted')
        wsRef.current = null
      }
    }
  }, [connect])

  return {
    socket: wsRef.current,
  }
}
