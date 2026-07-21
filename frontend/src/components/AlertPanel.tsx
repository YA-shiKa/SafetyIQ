import { useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, ChevronDown, ChevronUp, X } from 'lucide-react'
import { useSafetyStore } from '../store/safetyStore'
import type { Alert } from '../types'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const SEVERITY_STYLES: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  CRITICAL: { border: 'border-l-red-600',   bg: 'bg-red-950/30',   text: 'text-red-400',    dot: 'bg-red-500' },
  HIGH:     { border: 'border-l-orange-500', bg: 'bg-orange-950/20', text: 'text-orange-400', dot: 'bg-orange-500' },
  MEDIUM:   { border: 'border-l-yellow-500', bg: 'bg-yellow-950/20', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  LOW:      { border: 'border-l-blue-500',   bg: 'bg-blue-950/20',   text: 'text-blue-400',   dot: 'bg-blue-500' },
}

function AlertCard({ alert }: { alert: Alert }) {
  const [expanded, setExpanded] = useState(false)
  const { acknowledgeAlert } = useSafetyStore()
  const style = SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.LOW
  const isCritical = alert.severity === 'CRITICAL'

  return (
    <div
      className={clsx(
        'glass-card border-l-4 p-3 transition-all duration-200',
        style.border,
        style.bg,
        alert.acknowledged && 'opacity-50',
        isCritical && !alert.acknowledged && 'critical-pulse'
      )}
    >
      <div className="flex items-start gap-2">
        {/* Dot indicator */}
        <div className="mt-1.5 flex-shrink-0">
          <div className={clsx('w-2 h-2 rounded-full', style.dot, isCritical && !alert.acknowledged && 'animate-pulse')} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={clsx('mono text-xs font-bold', style.text)}>{alert.severity}</span>
                <span className="text-gray-500 text-xs">·</span>
                <span className="text-gray-500 text-xs mono">{alert.zone}</span>
                <span className="text-gray-500 text-xs">·</span>
                <span className="text-gray-600 text-xs">
                  {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                </span>
              </div>
              <p className="text-white text-sm font-medium mt-0.5 leading-snug">{alert.title}</p>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              {!alert.acknowledged && (
                <button
                  onClick={() => acknowledgeAlert(alert.alert_id)}
                  className="p-1 rounded hover:bg-white/10 text-gray-500 hover:text-green-400 transition-colors"
                  title="Acknowledge"
                >
                  <CheckCircle size={14} />
                </button>
              )}
              <button
                onClick={() => setExpanded(!expanded)}
                className="p-1 rounded hover:bg-white/10 text-gray-500 transition-colors"
              >
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>
          </div>

          {expanded && (
            <div className="mt-2 space-y-2">
              <p className="text-gray-300 text-xs leading-relaxed">{alert.description}</p>
              {alert.compound_factors.length > 0 && (
                <div>
                  <p className="text-gray-500 text-xs font-medium mb-1">COMPOUND FACTORS</p>
                  <ul className="space-y-0.5">
                    {alert.compound_factors.map((f, i) => (
                      <li key={i} className="text-gray-400 text-xs flex gap-1.5">
                        <span className="text-gray-600">·</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function AlertPanel() {
  const alerts = useSafetyStore(s => s.alerts)
  const [filter, setFilter] = useState<'ALL' | 'UNACK'>('UNACK')

  const displayed = filter === 'UNACK'
    ? alerts.filter(a => !a.acknowledged)
    : alerts

  const unackCount = alerts.filter(a => !a.acknowledged).length
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL' && !a.acknowledged).length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bell size={15} className="text-orange-400" />
          <span className="font-semibold text-sm text-white">Active Alerts</span>
          {unackCount > 0 && (
            <span className="mono text-xs px-1.5 py-0.5 bg-red-600 text-white rounded-full font-bold">
              {unackCount}
            </span>
          )}
          {criticalCount > 0 && (
            <span className="mono text-xs px-1.5 py-0.5 bg-red-900/50 text-red-400 rounded-full border border-red-700 animate-pulse">
              {criticalCount} CRITICAL
            </span>
          )}
        </div>
        <div className="flex gap-1">
          {(['UNACK', 'ALL'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                'mono text-xs px-2 py-0.5 rounded transition-colors',
                filter === f
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {displayed.length === 0 ? (
          <div className="text-center py-8 text-gray-600">
            <CheckCircle size={24} className="mx-auto mb-2 text-green-700" />
            <p className="text-sm">No {filter === 'UNACK' ? 'unacknowledged ' : ''}alerts</p>
          </div>
        ) : (
          displayed.map(alert => (
            <AlertCard key={alert.alert_id} alert={alert} />
          ))
        )}
      </div>
    </div>
  )
}