import { create } from 'zustand'
import type { SensorReading, Zone, Alert, ComplianceStatus } from '../types'

interface SafetyStore {
  // Connection
  wsConnected: boolean
  setWsConnected: (v: boolean) => void

  // Sensors
  sensors: SensorReading[]
  setSensors: (sensors: SensorReading[]) => void

  // Zones
  zones: Zone[]
  setZones: (zones: Zone[]) => void

  // Plant risk
  plantRiskScore: number
  setPlantRiskScore: (score: number) => void

  // Alerts
  alerts: Alert[]
  setAlerts: (alerts: Alert[]) => void
  acknowledgeAlert: (id: string) => void

  // Compliance
  compliance: ComplianceStatus | null
  setCompliance: (c: ComplianceStatus) => void

  // Emergency active
  emergencyActive: boolean
  emergencyZone: string
  triggerEmergency: (zone: string) => void
  clearEmergency: () => void

  // Last analysis time
  lastAnalysisAt: string | null
  setLastAnalysisAt: (t: string) => void
}

export const useSafetyStore = create<SafetyStore>((set) => ({
  wsConnected: false,
  setWsConnected: (v) => set({ wsConnected: v }),

  sensors: [],
  setSensors: (sensors) => set({ sensors }),

  zones: [],
  setZones: (zones) => set({ zones }),

  plantRiskScore: 0,
  setPlantRiskScore: (score) => set({ plantRiskScore: score }),

  alerts: [],
  setAlerts: (alerts) => set({ alerts }),
  acknowledgeAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.alert_id === id ? { ...a, acknowledged: true } : a
      ),
    })),

  compliance: null,
  setCompliance: (compliance) => set({ compliance }),

  emergencyActive: false,
  emergencyZone: '',
  triggerEmergency: (zone) => set({ emergencyActive: true, emergencyZone: zone }),
  clearEmergency: () => set({ emergencyActive: false, emergencyZone: '' }),

  lastAnalysisAt: null,
  setLastAnalysisAt: (t) => set({ lastAnalysisAt: t }),
}))