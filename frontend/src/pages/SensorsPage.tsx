import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Activity } from 'lucide-react'
import { SensorDashboard } from '../components/SensorDashboard'
import { api } from '../services/api'
import type { SensorHistory } from '../types'

function SensorChart({ sensorId }: { sensorId: string }) {
  const [history, setHistory] = useState<SensorHistory | null>(null)

  useEffect(() => {
    api.sensors.getById(sensorId).then(setHistory).catch(() => {})
  }, [sensorId])

  if (!history) return (
    <div className="h-48 flex items-center justify-center text-gray-600 text-sm">
      Loading chart...
    </div>
  )

  const data = history.readings.map(r => ({
    time: new Date(r.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
    value: r.value,
  }))

  const latestVal = data[data.length - 1]?.value ?? 0
  const lineColor = latestVal >= history.threshold_critical ? '#EF4444'
    : latestVal >= history.threshold_warning ? '#EAB308'
    : '#22C55E'

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="mono font-medium text-white">{history.sensor_type} · {history.zone}</span>
        <div className="flex gap-3 mono">
          <span>Min: {history.statistics.min}</span>
          <span>Max: {history.statistics.max}</span>
          <span>Mean: {history.statistics.mean}</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="time" tick={{ fill: '#556677', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#556677', fontSize: 10 }} tickLine={false} axisLine={false} width={35} />
          <Tooltip
            contentStyle={{ background: '#131920', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6 }}
            labelStyle={{ color: '#8899AA', fontSize: 11 }}
            itemStyle={{ color: lineColor, fontSize: 11 }}
          />
          <ReferenceLine y={history.threshold_warning}  stroke="#EAB308" strokeDasharray="4 2" strokeWidth={1} />
          <ReferenceLine y={history.threshold_critical} stroke="#EF4444" strokeDasharray="4 2" strokeWidth={1} />
          <Line
            type="monotone" dataKey="value" stroke={lineColor}
            strokeWidth={2} dot={false} activeDot={{ r: 4, fill: lineColor }}
          />
        </LineChart>
      </ResponsiveContainer>
      {history.statistics.time_to_critical_minutes !== null && (
        <div className="mono text-xs text-orange-400 bg-orange-950/20 border border-orange-800/40 px-2 py-1 rounded">
          ⚠ Time to critical threshold: ~{history.statistics.time_to_critical_minutes} minutes at current rate
        </div>
      )}
    </div>
  )
}

export function SensorsPage() {
  const [selectedSensor, setSelectedSensor] = useState<string | null>('S001')

  const SENSOR_IDS = ['S001', 'S002', 'S003', 'S004', 'S005', 'S006', 'S007', 'S008']

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Live Sensor Telemetry</h1>
          <p className="text-gray-500 text-xs">Real-time IoT/SCADA sensor readings across all plant zones</p>
        </div>
        <Activity size={20} className="text-blue-400" />
      </div>

      {/* Sensor chart */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm font-semibold text-white">Sensor History</span>
          <div className="flex gap-1 ml-auto flex-wrap">
            {SENSOR_IDS.map(id => (
              <button
                key={id}
                onClick={() => setSelectedSensor(id)}
                className={`mono text-xs px-2 py-0.5 rounded border transition-colors ${
                  selectedSensor === id
                    ? 'bg-blue-600/20 border-blue-600 text-blue-400'
                    : 'border-white/10 text-gray-500 hover:text-gray-300'
                }`}
              >
                {id}
              </button>
            ))}
          </div>
        </div>
        {selectedSensor && <SensorChart sensorId={selectedSensor} />}
      </div>

      {/* Live sensor grid */}
      <div className="glass-card p-4">
        <h2 className="text-sm font-semibold text-white mb-3">All Sensors — Live</h2>
        <SensorDashboard />
      </div>
    </div>
  )
}