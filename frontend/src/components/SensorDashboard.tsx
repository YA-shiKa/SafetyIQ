import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import { Activity, Thermometer, Wind, Droplets, Zap } from 'lucide-react'
import { useSafetyStore } from '../store/safetyStore'
import type { SensorReading } from '../types'
import clsx from 'clsx'

const SENSOR_ICONS: Record<string, React.ReactNode> = {
  H2S:      <Wind size={14} />,
  CO:       <Wind size={14} />,
  O2:       <Droplets size={14} />,
  TEMP:     <Thermometer size={14} />,
  PRESSURE: <Zap size={14} />,
}

const ALARM_STYLES = {
  NORMAL:   { badge: 'text-green-400 bg-green-950/30 border-green-800',  bar: '#22C55E' },
  WARNING:  { badge: 'text-yellow-400 bg-yellow-950/30 border-yellow-800', bar: '#EAB308' },
  CRITICAL: { badge: 'text-red-400 bg-red-950/30 border-red-800',         bar: '#EF4444' },
}

function SensorCard({ sensor }: { sensor: SensorReading }) {
  const styles = ALARM_STYLES[sensor.alarm_state]
  const pct = Math.min(100, (sensor.value / sensor.threshold_critical) * 100)

  const trendIcon = sensor.trend === 'rising' ? '↑' : sensor.trend === 'falling' ? '↓' : '→'
  const trendColor = sensor.trend === 'rising' && sensor.alarm_state !== 'NORMAL' ? 'text-red-400'
    : sensor.trend === 'falling' && sensor.sensor_type === 'O2' ? 'text-red-400'
    : 'text-gray-500'

  return (
    <div className={clsx(
      'glass-card p-3 space-y-2 border',
      sensor.alarm_state === 'CRITICAL' ? 'border-red-800/50 critical-pulse'
        : sensor.alarm_state === 'WARNING' ? 'border-yellow-800/40'
        : 'border-transparent'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-gray-400">
          {SENSOR_ICONS[sensor.sensor_type] ?? <Activity size={14} />}
          <span className="mono text-xs font-medium">{sensor.sensor_type}</span>
          <span className={clsx('mono text-xs', trendColor)}>{trendIcon}</span>
        </div>
        <span className={clsx('mono text-xs px-1.5 py-0.5 rounded-full border font-bold', styles.badge)}>
          {sensor.alarm_state}
        </span>
      </div>

      {/* Value */}
      <div>
        <span
          className="mono font-bold text-xl"
          style={{ color: styles.bar, transition: 'color 0.4s ease' }}
        >
          {sensor.value.toFixed(1)}
        </span>
        <span className="text-gray-500 text-xs ml-1">{sensor.unit}</span>
      </div>

      {/* Progress bar */}
      <div className="space-y-0.5">
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: styles.bar }}
          />
        </div>
        <div className="flex justify-between text-gray-600 text-xs mono">
          <span>0</span>
          <span className="text-gray-500">W:{sensor.threshold_warning}</span>
          <span className="text-gray-500">C:{sensor.threshold_critical}</span>
        </div>
      </div>

      {/* Zone */}
      <div className="text-gray-600 text-xs truncate">{sensor.zone}</div>
    </div>
  )
}

export function SensorDashboard() {
  const sensors = useSafetyStore(s => s.sensors)
  const [selectedZone, setSelectedZone] = useState<string>('ALL')

  const zones = ['ALL', ...Array.from(new Set(sensors.map(s => s.zone)))]

  const filtered = selectedZone === 'ALL'
    ? sensors
    : sensors.filter(s => s.zone === selectedZone)

  const critCount = sensors.filter(s => s.alarm_state === 'CRITICAL').length
  const warnCount = sensors.filter(s => s.alarm_state === 'WARNING').length

  return (
    <div className="space-y-3">
      {/* Stats strip */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Active Sensors', value: sensors.length, color: 'text-blue-400' },
          { label: 'In Warning',     value: warnCount,      color: 'text-yellow-400' },
          { label: 'Critical',       value: critCount,      color: 'text-red-400' },
        ].map(stat => (
          <div key={stat.label} className="glass-card p-2 text-center">
            <div className={clsx('mono font-bold text-lg', stat.color)}>{stat.value}</div>
            <div className="text-gray-500 text-xs">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Zone filter */}
      <div className="flex gap-1.5 flex-wrap">
        {zones.map(z => (
          <button
            key={z}
            onClick={() => setSelectedZone(z)}
            className={clsx(
              'mono text-xs px-2 py-0.5 rounded border transition-colors',
              selectedZone === z
                ? 'bg-blue-600/20 border-blue-600 text-blue-400'
                : 'border-white/10 text-gray-500 hover:text-gray-300 hover:border-white/20'
            )}
          >
            {z === 'ALL' ? 'All Zones' : z}
          </button>
        ))}
      </div>

      {/* Sensor grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {filtered.map(s => (
          <SensorCard key={s.sensor_id} sensor={s} />
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full text-center py-8 text-gray-600 text-sm">
            No sensors for selected zone
          </div>
        )}
      </div>
    </div>
  )
}