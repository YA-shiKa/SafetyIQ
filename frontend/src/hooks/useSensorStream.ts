import { useEffect, useRef, useState } from 'react'
import { wsService } from '../services/websocket'
import { useSafetyStore } from '../store/safetyStore'

export function useSensorStream() {
  const { setSensors, setPlantRiskScore, setWsConnected } = useSafetyStore()
  const [connected, setConnected] = useState(false)
  const connCheckRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    wsService.connect()

    const unsub = wsService.subscribe((msg) => {
      if (msg.type === 'SENSOR_UPDATE' || msg.type === 'CONNECTED') {
        if (msg.sensors) setSensors(msg.sensors as any)
        if (msg.plant_risk_score !== undefined) setPlantRiskScore(msg.plant_risk_score)
      }
    })

    // Poll connection status
    connCheckRef.current = setInterval(() => {
      const c = wsService.isConnected
      setConnected(c)
      setWsConnected(c)
    }, 1000)

    return () => {
      unsub()
      if (connCheckRef.current) clearInterval(connCheckRef.current)
    }
  }, [setSensors, setPlantRiskScore, setWsConnected])

  return { connected }
}