import { useEffect, useState } from 'react'
import { BookOpen, AlertTriangle, TrendingUp, Shield } from 'lucide-react'
import { api } from '../services/api'
import type { IncidentPattern } from '../types'
import clsx from 'clsx'

const SEVERITY_CONFIG = {
  FATAL:                { color: 'text-red-400',    bg: 'bg-red-950/30',    label: 'FATAL' },
  SERIOUS_INJURY:       { color: 'text-orange-400', bg: 'bg-orange-950/20', label: 'SERIOUS' },
  DANGEROUS_OCCURRENCE: { color: 'text-yellow-400', bg: 'bg-yellow-950/20', label: 'DANGEROUS' },
}

function PatternCard({ pattern }: { pattern: IncidentPattern }) {
  const cfg = SEVERITY_CONFIG[pattern.severity_potential] ?? SEVERITY_CONFIG.DANGEROUS_OCCURRENCE
  const matchPct = Math.round(pattern.current_condition_match * 100)

  return (
    <div className="glass-card p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={clsx('mono text-xs font-bold px-1.5 py-0.5 rounded', cfg.color, cfg.bg)}>
              {cfg.label}
            </span>
            <span className="text-gray-500 text-xs">×{pattern.recurrence_count} recurrences</span>
          </div>
          <h4 className="text-white text-sm font-semibold leading-snug">{pattern.pattern_name}</h4>
        </div>
        {/* Match score ring */}
        <div className="flex-shrink-0 text-center">
          <div
            className="mono text-base font-bold"
            style={{ color: matchPct >= 80 ? '#EF4444' : matchPct >= 60 ? '#F97316' : '#EAB308' }}
          >
            {matchPct}%
          </div>
          <div className="text-gray-600 text-xs">match</div>
        </div>
      </div>

      <p className="text-gray-400 text-xs leading-relaxed">{pattern.description}</p>

      {pattern.prevention_priorities.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs font-medium mb-1">PREVENTION PRIORITIES</p>
          <ul className="space-y-0.5">
            {pattern.prevention_priorities.slice(0, 3).map((p, i) => (
              <li key={i} className="text-green-400/80 text-xs flex gap-1.5">
                <Shield size={10} className="mt-0.5 flex-shrink-0 text-green-600" />
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}

      {pattern.similar_incidents.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-gray-600 text-xs">Similar incidents:</span>
          {pattern.similar_incidents.map(id => (
            <span key={id} className="mono text-xs text-blue-400/70">{id}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export function IncidentTimeline() {
  const [patterns, setPatterns] = useState<IncidentPattern[]>([])
  const [stats, setStats] = useState<{
    total_incidents: number
    fatalities_ytd: number
    near_misses_ytd: number
    dangerous_occurrences_ytd: number
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [histData] = await Promise.all([api.incidents.getHistory()])
        setStats(histData as any)
      } catch (e) {
        console.error('Failed to load incident data', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Mock patterns for display (in prod: from /incidents/patterns)
  const mockPatterns: IncidentPattern[] = [
    {
      pattern_id: 'PAT-001',
      pattern_name: 'PTW-Sensor Disconnect',
      description: 'Permits issued without verifying adjacent zone sensor readings. Repeated across 7 incidents.',
      recurrence_count: 7,
      severity_potential: 'FATAL',
      current_condition_match: 0.91,
      similar_incidents: ['INC-2025-001', 'INC-2024-047'],
      regulatory_gaps: ['OISD 105 Section 6.1'],
      prevention_priorities: [
        'Automate cross-check between permit zone and live sensor readings before issuance',
        'Block PTW system if any adjacent zone sensor is in WARNING state',
      ],
      ai_analysis: '',
      timestamp: new Date().toISOString(),
    },
    {
      pattern_id: 'PAT-002',
      pattern_name: 'Shift Changeover Communication Gap',
      description: 'Critical safety information not fully transferred during shift handovers, especially involving active permits and sensor anomalies.',
      recurrence_count: 5,
      severity_potential: 'SERIOUS_INJURY',
      current_condition_match: 0.78,
      similar_incidents: ['INC-2024-047', 'INC-2023-031'],
      regulatory_gaps: ['DGMS Circular 2019-03'],
      prevention_priorities: [
        'Mandatory digital handover checklist with permit acknowledgement',
        'Delay shift changeover if active CRITICAL sensor alerts exist',
      ],
      ai_analysis: '',
      timestamp: new Date().toISOString(),
    },
    {
      pattern_id: 'PAT-003',
      pattern_name: 'Overdue Maintenance Under Load',
      description: 'Equipment operating beyond inspection intervals under elevated process conditions — detected in 5 incidents causing pressure vessel failures.',
      recurrence_count: 5,
      severity_potential: 'DANGEROUS_OCCURRENCE',
      current_condition_match: 0.82,
      similar_incidents: ['INC-2024-018'],
      regulatory_gaps: ['OISD 118 Section 8.4', 'Factory Act 1948 Section 31'],
      prevention_priorities: [
        'Auto-alert when overdue equipment operates above 75% design capacity',
        'Integrate CMMS inspection due dates with real-time SCADA pressure readings',
      ],
      ai_analysis: '',
      timestamp: new Date().toISOString(),
    },
  ]

  const displayPatterns = patterns.length > 0 ? patterns : mockPatterns

  return (
    <div className="space-y-4">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Incidents YTD', value: stats.total_incidents, color: 'text-gray-300' },
            { label: 'Fatalities',    value: stats.fatalities_ytd,  color: 'text-red-400' },
            { label: 'Near Misses',   value: stats.near_misses_ytd, color: 'text-yellow-400' },
            { label: 'Dangerous Occ.',value: stats.dangerous_occurrences_ytd, color: 'text-orange-400' },
          ].map(stat => (
            <div key={stat.label} className="glass-card p-2 text-center">
              <div className={clsx('mono font-bold text-lg', stat.color)}>{stat.value}</div>
              <div className="text-gray-600 text-xs">{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Patterns */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp size={14} className="text-orange-400" />
          <span className="text-sm font-semibold text-white">Recurring Patterns</span>
          <span className="mono text-xs text-gray-500 ml-auto">RAG-powered pattern detection</span>
        </div>
        <div className="space-y-2">
          {displayPatterns.map(p => <PatternCard key={p.pattern_id} pattern={p} />)}
        </div>
      </div>
    </div>
  )
}