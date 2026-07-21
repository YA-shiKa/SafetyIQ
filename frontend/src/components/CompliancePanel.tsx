import { ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react'
import { useSafetyStore } from '../store/safetyStore'
import clsx from 'clsx'

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-gray-400 text-xs">{label}</span>
        <span className="mono text-xs font-bold" style={{ color }}>{score}/100</span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

function scoreColor(score: number) {
  if (score >= 85) return '#22C55E'
  if (score >= 70) return '#EAB308'
  if (score >= 55) return '#F97316'
  return '#EF4444'
}

export function CompliancePanel() {
  const compliance = useSafetyStore(s => s.compliance)

  if (!compliance) {
    return (
      <div className="text-center py-8 text-gray-600 text-sm">
        Loading compliance data...
      </div>
    )
  }

  const overallColor = scoreColor(compliance.overall_score)

  return (
    <div className="space-y-4">
      {/* Overall score */}
      <div className="flex items-center gap-4">
        <div className="relative flex-shrink-0">
          <svg width="80" height="80" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="32" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="7" />
            <circle
              cx="40" cy="40" r="32"
              fill="none"
              stroke={overallColor}
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 32}`}
              strokeDashoffset={`${2 * Math.PI * 32 * (1 - compliance.overall_score / 100)}`}
              transform="rotate(-90 40 40)"
              style={{ transition: 'all 0.8s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="mono font-bold text-lg" style={{ color: overallColor }}>
              {compliance.overall_score}
            </span>
          </div>
        </div>
        <div className="flex-1">
          <div className="font-semibold text-white text-sm">Overall Compliance</div>
          <div className="text-gray-500 text-xs mt-0.5">
            {compliance.open_findings} open findings · Next audit: {compliance.next_audit}
          </div>
          <div className="flex items-center gap-1 mt-1">
            <ShieldCheck size={12} className="text-gray-500" />
            <span className="text-gray-500 text-xs">Last audit: {compliance.last_audit}</span>
          </div>
        </div>
      </div>

      {/* Framework scores */}
      <div className="space-y-2">
        <p className="text-gray-500 text-xs font-medium">FRAMEWORK SCORES</p>
        <ScoreBar label="OISD Standards"   score={compliance.oisd_score}         color={scoreColor(compliance.oisd_score)} />
        <ScoreBar label="Factory Act 1948" score={compliance.factory_act_score}   color={scoreColor(compliance.factory_act_score)} />
        <ScoreBar label="DGMS"             score={compliance.dgms_score}          color={scoreColor(compliance.dgms_score)} />
      </div>

      {/* Critical gaps */}
      {compliance.critical_gaps.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <ShieldAlert size={13} className="text-red-400" />
            <p className="text-red-400 text-xs font-bold">CRITICAL GAPS ({compliance.critical_gaps.length})</p>
          </div>
          <div className="space-y-1.5">
            {compliance.critical_gaps.map((gap, i) => (
              <div key={i} className="glass-card p-2 border border-red-900/40 bg-red-950/15">
                <div className="flex gap-2">
                  <AlertTriangle size={11} className="text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-red-300/90 text-xs leading-relaxed">{gap}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}