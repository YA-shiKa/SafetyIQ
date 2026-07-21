import { useSafetyStore } from '../store/safetyStore'

function getRiskColor(score: number) {
  if (score >= 91) return '#DC2626'
  if (score >= 76) return '#EF4444'
  if (score >= 56) return '#F97316'
  if (score >= 31) return '#EAB308'
  return '#22C55E'
}

function getRiskLabel(score: number) {
  if (score >= 91) return 'CRITICAL'
  if (score >= 76) return 'DANGER'
  if (score >= 56) return 'ELEVATED'
  if (score >= 31) return 'CAUTION'
  return 'SAFE'
}

export function RiskScoreGauge() {
  const score = useSafetyStore(s => s.plantRiskScore)
  const color = getRiskColor(score)
  const label = getRiskLabel(score)
  const isCritical = score >= 76

  const circumference = 2 * Math.PI * 54
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`relative ${isCritical ? 'critical-pulse' : ''}`}>
        <svg width="140" height="140" viewBox="0 0 140 140">
          {/* Track */}
          <circle
            cx="70" cy="70" r="54"
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="10"
          />
          {/* Progress */}
          <circle
            cx="70" cy="70" r="54"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform="rotate(-90 70 70)"
            style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.5s ease' }}
          />
          {/* Glow */}
          <circle
            cx="70" cy="70" r="54"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeOpacity="0.15"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform="rotate(-90 70 70)"
            style={{ filter: `blur(6px)`, transition: 'stroke-dashoffset 0.8s ease' }}
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="mono font-bold text-3xl"
            style={{ color, transition: 'color 0.5s ease' }}
          >
            {score}
          </span>
          <span className="text-xs text-gray-500 mono">/100</span>
        </div>
      </div>
      <div
        className="mono text-xs font-bold tracking-widest px-3 py-1 rounded-full"
        style={{
          color,
          background: `${color}18`,
          border: `1px solid ${color}40`,
        }}
      >
        {label}
      </div>
    </div>
  )
}