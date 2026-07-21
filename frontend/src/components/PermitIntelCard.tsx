import { useState } from 'react'
import { FileCheck, AlertTriangle, Clock, User, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { api } from '../services/api'
import type { PermitValidationResult, PermitType } from '../types'
import clsx from 'clsx'

const PERMIT_TYPES: PermitType[] = [
  'CONFINED_SPACE', 'HOT_WORK', 'ELECTRICAL_ISOLATION',
  'HEIGHT_WORK', 'EXCAVATION', 'CHEMICAL_HANDLING',
]

const ZONES = [
  'Coke Oven Battery A', 'Coke Oven Battery B', 'Blast Furnace Zone',
  'Hot Strip Mill', 'Confined Space B7', 'Chemical Storage', 'Raw Material Bay',
]

const DECISION_CONFIG = {
  APPROVED:    { icon: CheckCircle, color: 'text-green-400',  bg: 'bg-green-950/30',   border: 'border-green-700' },
  CONDITIONAL: { icon: AlertCircle, color: 'text-yellow-400', bg: 'bg-yellow-950/20',  border: 'border-yellow-700' },
  SUSPENDED:   { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-950/20', border: 'border-orange-700' },
  DENIED:      { icon: XCircle,     color: 'text-red-400',    bg: 'bg-red-950/30',     border: 'border-red-700' },
}

function ValidationResult({ result }: { result: PermitValidationResult }) {
  const decision = (result.decision ?? (result.approved ? 'APPROVED' : 'DENIED')) as keyof typeof DECISION_CONFIG
  const cfg = DECISION_CONFIG[decision] ?? DECISION_CONFIG.DENIED
  const Icon = cfg.icon

  return (
    <div className={clsx('glass-card p-4 border space-y-3', cfg.bg, cfg.border)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={18} className={cfg.color} />
          <span className={clsx('font-bold mono', cfg.color)}>{decision}</span>
        </div>
        <div className={clsx('mono text-xs px-2 py-0.5 rounded-full border', cfg.border, cfg.color)}>
          Risk: {result.risk_level}
        </div>
      </div>

      {/* AI Recommendation */}
      <div>
        <p className="text-gray-400 text-xs font-medium mb-1">AI RECOMMENDATION</p>
        <p className="text-white text-sm leading-relaxed">{result.ai_recommendation}</p>
      </div>

      {/* Blocking issues */}
      {result.blocking_issues.length > 0 && (
        <div>
          <p className="text-red-400 text-xs font-medium mb-1">⛔ BLOCKING ISSUES</p>
          <ul className="space-y-1">
            {result.blocking_issues.map((issue, i) => (
              <li key={i} className="text-red-300 text-xs flex gap-1.5">
                <span className="text-red-600 mt-0.5">·</span>
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Conditions */}
      {result.conditions.length > 0 && (
        <div>
          <p className="text-yellow-400 text-xs font-medium mb-1">⚠ CONDITIONS</p>
          <ul className="space-y-1">
            {result.conditions.slice(0, 4).map((c, i) => (
              <li key={i} className="text-yellow-300/80 text-xs flex gap-1.5">
                <span className="text-yellow-600 mt-0.5">·</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Regulatory basis */}
      {result.regulatory_refs.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs font-medium mb-1">REGULATORY BASIS</p>
          <div className="flex flex-wrap gap-1">
            {result.regulatory_refs.map((ref, i) => (
              <span key={i} className="mono text-xs text-blue-400 bg-blue-950/30 border border-blue-800/40 px-1.5 py-0.5 rounded">
                {ref}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.estimated_safe_window && (
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <Clock size={12} className="text-gray-600" />
          <span>Estimated safe window: <span className="text-white">{result.estimated_safe_window}</span></span>
        </div>
      )}
    </div>
  )
}

export function PermitIntelCard() {
  const [form, setForm] = useState({
    permit_id: `PTW-${Math.floor(Math.random() * 9000) + 1000}`,
    permit_type: 'CONFINED_SPACE' as PermitType,
    zone: 'Confined Space B7',
    requested_by: '',
    planned_workers: 2,
    start_time: new Date().toISOString().slice(0, 16),
    duration_hours: 4,
  })
  const [result, setResult] = useState<PermitValidationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleValidate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.permits.validate(form)
      setResult(res)
    } catch (e) {
      setError('Failed to validate permit. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <FileCheck size={16} className="text-blue-400" />
        <span className="font-semibold text-sm text-white">Permit Intelligence</span>
        <span className="mono text-xs text-gray-500 ml-auto">AI-powered PTW validation</span>
      </div>

      {/* Form */}
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-2">
          <label className="text-gray-500 text-xs mb-1 block">Permit Type</label>
          <select
            value={form.permit_type}
            onChange={e => setForm(f => ({ ...f, permit_type: e.target.value as PermitType }))}
            className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white mono"
          >
            {PERMIT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
        </div>

        <div className="col-span-2">
          <label className="text-gray-500 text-xs mb-1 block">Zone</label>
          <select
            value={form.zone}
            onChange={e => setForm(f => ({ ...f, zone: e.target.value }))}
            className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
          >
            {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
          </select>
        </div>

        <div>
          <label className="text-gray-500 text-xs mb-1 block">Requested By</label>
          <input
            type="text"
            placeholder="Officer name"
            value={form.requested_by}
            onChange={e => setForm(f => ({ ...f, requested_by: e.target.value }))}
            className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
          />
        </div>

        <div>
          <label className="text-gray-500 text-xs mb-1 block">Workers</label>
          <input
            type="number"
            min={1} max={20}
            value={form.planned_workers}
            onChange={e => setForm(f => ({ ...f, planned_workers: +e.target.value }))}
            className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white mono"
          />
        </div>

        <div>
          <label className="text-gray-500 text-xs mb-1 block">Start Time</label>
          <input
            type="datetime-local"
            value={form.start_time}
            onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
            className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-xs text-white"
          />
        </div>

        <div>
          <label className="text-gray-500 text-xs mb-1 block">Duration (hours)</label>
          <input
            type="number"
            min={0.5} max={12} step={0.5}
            value={form.duration_hours}
            onChange={e => setForm(f => ({ ...f, duration_hours: +e.target.value }))}
            className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white mono"
          />
        </div>
      </div>

      <button
        onClick={handleValidate}
        disabled={loading}
        className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 text-white text-sm font-semibold rounded transition-colors mono"
      >
        {loading ? 'Validating against live conditions...' : 'Validate Permit'}
      </button>

      {error && (
        <p className="text-red-400 text-xs">{error}</p>
      )}

      {result && <ValidationResult result={result} />}
    </div>
  )
}