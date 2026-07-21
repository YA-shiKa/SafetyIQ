import { useEffect } from 'react'
import { api } from '../services/api'
import { useSafetyStore } from '../store/safetyStore'

export function useRiskScore(intervalMs = 10000) {
  const { setZones, setAlerts, setCompliance } = useSafetyStore()

  useEffect(() => {
    const fetch = async () => {
      try {
        const [zones, alertData, compliance] = await Promise.allSettled([
          api.zones.getAll(),
          api.alerts.getAll(),
          api.compliance.getStatus(),
        ])

        if (zones.status === 'fulfilled') setZones(zones.value)
        if (alertData.status === 'fulfilled') setAlerts(alertData.value.alerts)
        if (compliance.status === 'fulfilled') setCompliance(compliance.value)
      } catch (e) {
        console.error('Risk score fetch error', e)
      }
    }

    fetch()
    const interval = setInterval(fetch, intervalMs)
    return () => clearInterval(interval)
  }, [intervalMs, setZones, setAlerts, setCompliance])
}