import { useSafetyStore } from '../store/safetyStore'
import type { Zone, RiskStatus } from '../types'
import clsx from 'clsx'

const STATUS_CONFIG: Record<RiskStatus, { color: string; bg: string; glow: string }> = {
  SAFE:     { color: '#22C55E', bg: 'rgba(34,197,94,0.10)',  glow: 'rgba(34,197,94,0.3)' },
  CAUTION:  { color: '#EAB308', bg: 'rgba(234,179,8,0.12)',  glow: 'rgba(234,179,8,0.3)' },
  ELEVATED: { color: '#F97316', bg: 'rgba(249,115,22,0.14)', glow: 'rgba(249,115,22,0.3)' },
  DANGER:   { color: '#EF4444', bg: 'rgba(239,68,68,0.16)',  glow: 'rgba(239,68,68,0.4)' },
  CRITICAL: { color: '#DC2626', bg: 'rgba(220,38,38,0.20)',  glow: 'rgba(220,38,38,0.5)' },
}

// Plant layout positions (approximate grid positions for Vizag Steel)
const ZONE_LAYOUT: Record<string, { x: number; y: number; w: number; h: number; label: string }> = {
  'Coke Oven Battery A': { x: 0,   y: 0,   w: 2, h: 1, label: 'Coke Oven A' },
  'Coke Oven Battery B': { x: 2,   y: 0,   w: 2, h: 1, label: 'Coke Oven B' },
  'Blast Furnace Zone':  { x: 0,   y: 1,   w: 2, h: 1, label: 'Blast Furnace' },
  'Hot Strip Mill':      { x: 2,   y: 1,   w: 2, h: 1, label: 'Hot Strip Mill' },
  'Confined Space B7':   { x: 0,   y: 2,   w: 1, h: 1, label: 'Confined Sp. B7' },
  'Chemical Storage':    { x: 1,   y: 2,   w: 1, h: 1, label: 'Chemical Store' },
  'Raw Material Bay':    { x: 2,   y: 2,   w: 2, h: 1, label: 'Raw Material Bay' },
}

function ZoneTile({ zone }: { zone: Zone }) {
  const layout = ZONE_LAYOUT[zone.zone_name]
  const cfg = STATUS_CONFIG[zone.status]
  const isCritical = zone.status === 'CRITICAL' || zone.status === 'DANGER'

  if (!layout) return null

  const style: React.CSSProperties = {
    gridColumn: `${layout.x + 1} / span ${layout.w}`,
    gridRow: `${layout.y + 1} / span ${layout.h}`,
    backgroundColor: cfg.bg,
    border: `1px solid ${cfg.color}40`,
    borderRadius: 8,
    padding: '10px 12px',
    cursor: 'default',
    position: 'relative',
    overflow: 'hidden',
    transition: 'all 0.4s ease',
    boxShadow: isCritical ? `0 0 18px ${cfg.glow}, inset 0 0 12px ${cfg.glow}` : 'none',
  }

  return (
    <div style={style} className={isCritical ? 'critical-pulse' : ''}>
      {/* Scan line for critical */}
      {isCritical && (
        <div
          className="absolute left-0 right-0 h-px opacity-30"
          style={{
            background: `linear-gradient(90deg, transparent, ${cfg.color}, transparent)`,
            animation: 'scan 3s linear infinite',
          }}
        />
      )}

      <div className="relative z-10">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-semibold text-white/80 leading-tight">{layout.label}</div>
            <div className="mono text-xs mt-0.5" style={{ color: cfg.color }}>
              {zone.status}
            </div>
          </div>
          <div className="mono font-bold text-base" style={{ color: cfg.color }}>
            {zone.risk_score}
          </div>
        </div>

        <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
          <span>👷 {zone.active_workers}</span>
          <span>📋 {zone.active_permits} PTW</span>
        </div>

        {/* Mini risk bar */}
        <div className="mt-2 h-0.5 bg-white/5 rounded overflow-hidden">
          <div
            className="h-full rounded transition-all duration-700"
            style={{ width: `${zone.risk_score}%`, backgroundColor: cfg.color }}
          />
        </div>
      </div>
    </div>
  )
}

export function RiskHeatmap() {
  const zones = useSafetyStore(s => s.zones)

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-gray-500 text-xs">Risk Level:</span>
        {(Object.keys(STATUS_CONFIG) as RiskStatus[]).map(status => (
          <div key={status} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STATUS_CONFIG[status].color }} />
            <span className="mono text-xs text-gray-400">{status}</span>
          </div>
        ))}
      </div>

      {/* Plant grid */}
      <div
        className="w-full"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gridTemplateRows: 'repeat(3, 100px)',
          gap: 8,
        }}
      >
        {zones.map(zone => (
          <ZoneTile key={zone.zone_id} zone={zone} />
        ))}

        {/* Placeholder tiles for zones not yet in data */}
        {zones.length === 0 && (
          <div
            className="col-span-4 row-span-3 flex items-center justify-center text-gray-700 text-sm"
          >
            Connecting to plant data...
          </div>
        )}
      </div>

      {/* Zone list fallback (always visible) */}
      {zones.length > 0 && (
        <div className="grid grid-cols-2 gap-2 mt-1">
          {zones
            .sort((a, b) => b.risk_score - a.risk_score)
            .map(zone => {
              const cfg = STATUS_CONFIG[zone.status]
              return (
                <div key={zone.zone_id} className="glass-card p-2 flex items-center gap-2">
                  <div className="w-1.5 h-8 rounded-full" style={{ backgroundColor: cfg.color }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-white text-xs font-medium truncate">{zone.zone_name}</div>
                    <div className="mono text-xs" style={{ color: cfg.color }}>
                      {zone.risk_score}/100 · {zone.status}
                    </div>
                  </div>
                  <div className="text-gray-500 text-xs text-right">
                    <div>{zone.active_workers} workers</div>
                    <div>{zone.active_permits} permits</div>
                  </div>
                </div>
              )
            })}
        </div>
      )}
    </div>
  )
}