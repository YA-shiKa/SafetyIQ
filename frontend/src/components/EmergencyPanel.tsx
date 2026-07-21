import { useState } from 'react'
import { Siren, AlertTriangle, CheckCircle, Loader } from 'lucide-react'
import { api } from '../services/api'
import { useSafetyStore } from '../store/safetyStore'
import type { EmergencyResponse } from '../types'
import clsx from 'clsx'

const EMERGENCY_TYPES = [
  'GAS_LEAK', 'EXPLOSION', 'FIRE', 'CONFINED_SPACE_RESCUE',
  'STRUCTURAL_FAILURE', 'CHEMICAL_SPILL', 'WORKER_INJURY', 'EVACUATION',
]

const ZONES = [
  'Coke Oven Battery A', 'Coke Oven Battery B', 'Blast Furnace Zone',
  'Hot Strip Mill', 'Confined Space B7', 'Chemical Storage', 'Raw Material Bay',
]

export function EmergencyPanel() {
  const { triggerEmergency } = useSafetyStore()
  const [form, setForm] = useState({
    zone: 'Coke Oven Battery A',
    emergency_type: 'GAS_LEAK',
    description: '',
    workers_in_zone: 12,
  })
  const [step, setStep] = useState<'IDLE' | 'CONFIRM' | 'RUNNING' | 'DONE'>('IDLE')
  const [response, setResponse] = useState<EmergencyResponse | null>(null)

  const handleActivate = async () => {
    if (step === 'IDLE') { setStep('CONFIRM'); return }
    setStep('RUNNING')
    try {
      const res = await api.emergency.trigger({ ...form, triggered_by: 'SAFETY_OFFICER' })
      setResponse(res)
      triggerEmergency(form.zone)
      setStep('DONE')
    } catch (e) {
      setStep('IDLE')
    }
  }

  const reset = () => {
    setStep('IDLE')
    setResponse(null)
  }

  return (
    <div className="glass-card p-4 border border-red-900/40 space-y-3">
      <div className="flex items-center gap-2">
        <Siren size={16} className="text-red-400 animate-pulse" />
        <span className="font-bold text-red-400 text-sm">Emergency Response Orchestrator</span>
      </div>

      {step === 'DONE' && response ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle size={16} />
            <span className="font-semibold text-sm">Response Activated</span>
            <span className="mono text-xs text-gray-500 ml-auto">{response.response_id}</span>
          </div>

          <div>
            <p className="text-gray-400 text-xs font-medium mb-2">ACTIONS INITIATED</p>
            <ul className="space-y-1">
              {response.actions_initiated.map((action, i) => (
                <li key={i} className="flex items-center gap-2 text-xs text-green-300/80">
                  <CheckCircle size={10} className="text-green-600 flex-shrink-0" />
                  {action}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>Incident Report:</span>
            <span className="mono text-blue-400">{response.incident_report_id}</span>
          </div>

          <button
            onClick={reset}
            className="w-full py-1.5 text-xs text-gray-400 border border-white/10 rounded hover:bg-white/5 transition-colors"
          >
            Reset
          </button>
        </div>
      ) : (
        <>
          {step === 'IDLE' && (
            <div className="grid grid-cols-2 gap-2">
              <div className="col-span-2">
                <label className="text-gray-500 text-xs mb-1 block">Emergency Type</label>
                <select
                  value={form.emergency_type}
                  onChange={e => setForm(f => ({ ...f, emergency_type: e.target.value }))}
                  className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white mono"
                >
                  {EMERGENCY_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>

              <div className="col-span-2">
                <label className="text-gray-500 text-xs mb-1 block">Zone</label>
                <select
                  value={form.zone}
                  onChange={e => setForm(f => ({ ...f, zone: e.target.value }))}
                  className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
                >
                  {ZONES.map(z => <option key={z}>{z}</option>)}
                </select>
              </div>

              <div>
                <label className="text-gray-500 text-xs mb-1 block">Workers in Zone</label>
                <input
                  type="number"
                  min={0}
                  value={form.workers_in_zone}
                  onChange={e => setForm(f => ({ ...f, workers_in_zone: +e.target.value }))}
                  className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white mono"
                />
              </div>

              <div>
                <label className="text-gray-500 text-xs mb-1 block">&nbsp;</label>
                <div className="text-xs text-gray-500 py-1.5">Auto-detected from PTW</div>
              </div>

              <div className="col-span-2">
                <label className="text-gray-500 text-xs mb-1 block">Description</label>
                <textarea
                  rows={2}
                  placeholder="Describe the triggering event..."
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full bg-surface-800 border border-white/10 rounded px-2 py-1.5 text-sm text-white resize-none"
                />
              </div>
            </div>
          )}

          {step === 'CONFIRM' && (
            <div className="glass-card p-3 border border-red-700/50 bg-red-950/20 space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-red-400" />
                <span className="font-bold text-red-400 text-sm">Confirm Emergency Activation</span>
              </div>
              <p className="text-gray-300 text-xs">
                This will immediately trigger PA evacuation, SMS alerts to all emergency contacts,
                SCADA lockdown of all permits in <strong>{form.zone}</strong>, and generate a DGFASLI Form 18 report.
              </p>
              <p className="text-red-400 text-xs font-bold">This action cannot be undone.</p>
            </div>
          )}

          <button
            onClick={handleActivate}
            disabled={step === 'RUNNING'}
            className={clsx(
              'w-full py-2.5 font-bold text-sm rounded transition-all mono flex items-center justify-center gap-2',
              step === 'CONFIRM'
                ? 'bg-red-600 hover:bg-red-700 text-white border-2 border-red-400 critical-pulse'
                : 'bg-red-900/40 hover:bg-red-900/60 text-red-400 border border-red-800'
            )}
          >
            {step === 'RUNNING' && <Loader size={14} className="animate-spin" />}
            {step === 'IDLE'    && '🚨 ACTIVATE EMERGENCY RESPONSE'}
            {step === 'CONFIRM' && '⚠ CONFIRM — ACTIVATE NOW'}
            {step === 'RUNNING' && 'Orchestrating response...'}
          </button>

          {step === 'CONFIRM' && (
            <button
              onClick={() => setStep('IDLE')}
              className="w-full py-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
          )}
        </>
      )}
    </div>
  )
}