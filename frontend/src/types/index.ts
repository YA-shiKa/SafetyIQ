// ─── Sensor Types ─────────────────────────────────────────────────────────────

export interface SensorReading {
  sensor_id: string
  zone: string
  sensor_type: string
  value: number
  unit: string
  threshold_warning: number
  threshold_critical: number
  trend: 'rising' | 'falling' | 'stable'
  timestamp: string
  alarm_state: 'NORMAL' | 'WARNING' | 'CRITICAL'
  acknowledged: boolean
  last_calibration?: string
}

export interface SensorHistory {
  sensor_id: string
  sensor_type: string
  zone: string
  unit: string
  readings: Array<{ timestamp: string; value: number }>
  threshold_warning: number
  threshold_critical: number
  statistics: {
    min: number
    max: number
    mean: number
    trend_slope_per_minute: number
    time_to_critical_minutes: number | null
  }
}

// ─── Zone Types ───────────────────────────────────────────────────────────────

export type RiskStatus = 'SAFE' | 'CAUTION' | 'ELEVATED' | 'DANGER' | 'CRITICAL'

export interface Zone {
  zone_id: string
  zone_name: string
  risk_score: number
  status: RiskStatus
  active_workers: number
  active_permits: number
  alert_count?: number
  sensor_count?: number
}

// ─── Alert Types ──────────────────────────────────────────────────────────────

export interface Alert {
  alert_id: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  alert_type: 'COMPOUND_RISK' | 'PERMIT' | 'MAINTENANCE' | 'COMPLIANCE' | 'GAS' | 'PRESSURE'
  title: string
  description: string
  zone: string
  compound_factors: string[]
  timestamp: string
  acknowledged: boolean
}

// ─── Permit Types ─────────────────────────────────────────────────────────────

export type PermitType = 'HOT_WORK' | 'CONFINED_SPACE' | 'ELECTRICAL_ISOLATION' | 'HEIGHT_WORK' | 'EXCAVATION' | 'RADIOGRAPHY' | 'CHEMICAL_HANDLING'
export type PermitDecision = 'APPROVED' | 'CONDITIONAL' | 'SUSPENDED' | 'DENIED'

export interface PermitValidationResult {
  permit_id: string
  approved: boolean
  risk_level: string
  decision?: PermitDecision
  conditions: string[]
  blocking_issues: string[]
  simops_conflicts?: string[]
  checklist_gaps?: string[]
  ai_recommendation: string
  regulatory_refs: string[]
  estimated_safe_window?: string | null
  officer_action_required?: string
  validation_timestamp?: string
}

export interface ActivePermit {
  permit_id: string
  type: PermitType
  zone: string
  workers: number
  issued_by: string
  start_time: string
  end_time: string
  status: 'ACTIVE' | 'SUSPENDED' | 'COMPLETED' | 'DENIED'
  isolation_confirmed: boolean
}

// ─── Compliance Types ─────────────────────────────────────────────────────────

export interface ComplianceStatus {
  overall_score: number
  oisd_score: number
  factory_act_score: number
  dgms_score: number
  open_findings: number
  critical_gaps: string[]
  last_audit: string
  next_audit: string
}

export interface ComplianceFinding {
  finding_id: string
  standard_ref: string
  title: string
  description: string
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR'
  zone: string
  days_overdue: number
  corrective_actions: string[]
  due_date: string | null
}

// ─── Incident Types ───────────────────────────────────────────────────────────

export interface IncidentPattern {
  pattern_id: string
  pattern_name: string
  description: string
  recurrence_count: number
  severity_potential: 'FATAL' | 'SERIOUS_INJURY' | 'DANGEROUS_OCCURRENCE'
  current_condition_match: number
  similar_incidents: string[]
  regulatory_gaps: string[]
  prevention_priorities: string[]
  ai_analysis: string
  timestamp: string
}

export interface IncidentRecord {
  id: string
  date: string
  type: 'NEAR_MISS' | 'INJURY' | 'FATALITY' | 'DANGEROUS_OCCURRENCE'
  zone: string
  description: string
}

// ─── Analysis Types ───────────────────────────────────────────────────────────

export interface CompoundRiskEvent {
  event_id: string
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'SAFE'
  title: string
  description: string
  zone: string
  contributing_factors: string[]
  recommended_actions: string[]
  confidence_score: number
  lead_time_hours: number
  regulatory_refs: string[]
  predicted_escalation_time?: string | null
  ai_analysis?: string
  timestamp: string
}

export interface AnalysisResult {
  analysis_id: string
  timestamp: string
  plant_risk_score: number
  compound_risks: CompoundRiskEvent[]
  incident_patterns: IncidentPattern[]
}

// ─── Emergency Types ──────────────────────────────────────────────────────────

export interface EmergencyResponse {
  response_id: string
  status: string
  message: string
  actions_initiated: string[]
  estimated_completion_seconds: number
  incident_report_id: string
}

// ─── WebSocket Types ──────────────────────────────────────────────────────────

export interface WsMessage {
  type: 'SENSOR_UPDATE' | 'CONNECTED' | 'ALERT' | 'RISK_UPDATE' | 'pong'
  timestamp?: string
  sensors?: SensorReading[]
  plant_risk_score?: number
  message?: string
}