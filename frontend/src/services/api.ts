import type {
  SensorReading, SensorHistory, Zone, Alert,
  ComplianceStatus, AnalysisResult, PermitValidationResult,
  EmergencyResponse, IncidentPattern
} from '../types'

const BASE = '/api/v1'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

// ─── Sensors ──────────────────────────────────────────────────────────────────

export const api = {
  sensors: {
    getAll:       () => get<SensorReading[]>('/sensors'),
    getById:      (id: string) => get<SensorHistory>(`/sensors/${id}`),
    getByZone:    (zone: string) => get<{ zone: string; sensors: SensorReading[] }>(`/sensors/zone/${zone}`),
    getAlerts:    (level: 'WARNING' | 'CRITICAL' = 'WARNING') =>
                    get<{ total_in_alarm: number; sensors: SensorReading[] }>(`/sensors/alerts/active?min_level=${level}`),
    acknowledge:  (id: string, by: string, reason: string) =>
                    post(`/sensors/${id}/ack`, { acknowledged_by: by, reason }),
  },

  zones: {
    getAll:  () => get<Zone[]>('/zones'),
    getById: (id: string) => get<Zone & { sensors: SensorReading[] }>(`/zones/${id}`),
  },

  alerts: {
    getAll: () => get<{ alerts: Alert[]; total: number; critical_count: number; unacknowledged_count: number }>('/alerts'),
  },

  analysis: {
    run: (zone?: string) => post<AnalysisResult>('/analyze', { zone, include_patterns: true, include_compliance: true }),
  },

  permits: {
    validate: (data: {
      permit_id: string
      permit_type: string
      zone: string
      requested_by: string
      planned_workers: number
      start_time: string
      duration_hours: number
    }) => post<PermitValidationResult>('/permits/validate', data),
    getActive: () => get<{ permits: unknown[] }>('/permits/active'),
  },

  emergency: {
    trigger: (data: {
      zone: string
      emergency_type: string
      description: string
      triggered_by?: string
      workers_in_zone?: number
    }) => post<EmergencyResponse>('/emergency', data),
  },

  compliance: {
    getStatus: () => get<ComplianceStatus>('/compliance'),
    getReport:  () => get<{ frameworks: unknown[] }>('/compliance/report'),
  },

  incidents: {
    getHistory:  () => get<{ total_incidents: number; top_patterns: unknown[]; recent_incidents: unknown[] }>('/incidents'),
    getPatterns: () => get<{ patterns: IncidentPattern[] }>('/incidents/patterns'),
  },

  health: () => get<{ status: string }>('/health'),
}