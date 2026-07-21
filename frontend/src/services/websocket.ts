import type { WsMessage } from '../types'

type Listener = (msg: WsMessage) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private listeners: Set<Listener> = new Set()
  private pingInterval: ReturnType<typeof setInterval> | null = null
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private reconnectDelay = 2000
  private shouldReconnect = true

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    this.ws = new WebSocket(`${protocol}//${host}/ws/live`)

    this.ws.onopen = () => {
      console.log('[SafetyIQ WS] Connected')
      this.reconnectDelay = 2000
      this.pingInterval = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send('ping')
        }
      }, 20000)
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        this.listeners.forEach(l => l(msg))
      } catch (e) {
        console.error('[SafetyIQ WS] Parse error', e)
      }
    }

    this.ws.onclose = () => {
      console.log('[SafetyIQ WS] Disconnected')
      this._cleanup()
      if (this.shouldReconnect) {
        this.reconnectTimeout = setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000)
          this.connect()
        }, this.reconnectDelay)
      }
    }

    this.ws.onerror = (err) => {
      console.error('[SafetyIQ WS] Error', err)
    }
  }

  disconnect() {
    this.shouldReconnect = false
    this._cleanup()
    this.ws?.close()
    this.ws = null
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private _cleanup() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsService = new WebSocketService()