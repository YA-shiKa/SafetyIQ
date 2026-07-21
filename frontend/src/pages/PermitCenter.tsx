import { FileCheck } from 'lucide-react'
import { PermitIntelCard } from '../components/PermitIntelCard'

const ACTIVE_PERMITS = [
  { permit_id: 'PTW-2847', type: 'CONFINED_SPACE', zone: 'Confined Space B7', workers: 4, issued_by: 'SO-Sharma', status: 'ACTIVE', isolation_confirmed: true },
  { permit_id: 'PTW-2851', type: 'HOT_WORK',       zone: 'Coke Oven Battery A', workers: 2, issued_by: 'SO-Patel',  status: 'ACTIVE', isolation_confirmed: false },
  { permit_id: 'PTW-2849', type: 'ELECTRICAL_ISOLATION', zone: 'Hot Strip Mill', workers: 2, issued_by: 'SO-Kumar', status: 'ACTIVE', isolation_confirmed: true },
  { permit_id: 'PTW-2853', type: 'CONFINED_SPACE', zone: 'Raw Material Bay', workers: 3, issued_by: 'SO-Singh', status: 'SUSPENDED', isolation_confirmed: false },
]

const STATUS_STYLES = {
  ACTIVE:    'text-green-400 bg-green-950/20 border-green-800',
  SUSPENDED: 'text-red-400 bg-red-950/20 border-red-800',
  COMPLETED: 'text-gray-500 bg-gray-900/20 border-gray-800',
  DENIED:    'text-red-600 bg-red-950/20 border-red-900',
}

export function PermitCenter() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Permit Intelligence Center</h1>
          <p className="text-gray-500 text-xs">AI-powered PTW validation against live plant conditions (OISD 105)</p>
        </div>
        <FileCheck size={20} className="text-blue-400" />
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Active permits table */}
        <div className="col-span-7">
          <div className="glass-card p-4">
            <h2 className="text-sm font-semibold text-white mb-3">
              Active Permits
              <span className="mono text-xs text-gray-500 font-normal ml-2">
                {ACTIVE_PERMITS.filter(p => p.status === 'ACTIVE').length} active · {ACTIVE_PERMITS.filter(p => p.status === 'SUSPENDED').length} suspended
              </span>
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-600 border-b border-white/5">
                    <th className="text-left py-2 px-1 mono font-medium">PERMIT ID</th>
                    <th className="text-left py-2 px-1 font-medium">TYPE</th>
                    <th className="text-left py-2 px-1 font-medium">ZONE</th>
                    <th className="text-center py-2 px-1 font-medium">WORKERS</th>
                    <th className="text-center py-2 px-1 font-medium">ISOLATION</th>
                    <th className="text-left py-2 px-1 font-medium">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {ACTIVE_PERMITS.map(p => (
                    <tr key={p.permit_id} className="hover:bg-white/2 transition-colors">
                      <td className="py-2 px-1 mono text-blue-400">{p.permit_id}</td>
                      <td className="py-2 px-1 text-gray-300">{p.type.replace(/_/g, ' ')}</td>
                      <td className="py-2 px-1 text-gray-400">{p.zone}</td>
                      <td className="py-2 px-1 text-center mono text-gray-300">{p.workers}</td>
                      <td className="py-2 px-1 text-center">
                        {p.isolation_confirmed
                          ? <span className="text-green-400">✓</span>
                          : <span className="text-red-400 font-bold">✗</span>
                        }
                      </td>
                      <td className="py-2 px-1">
                        <span className={`mono text-xs px-1.5 py-0.5 rounded-full border ${STATUS_STYLES[p.status as keyof typeof STATUS_STYLES]}`}>
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* SIMOPS warning */}
            <div className="mt-3 p-2 border border-orange-800/40 bg-orange-950/15 rounded text-xs">
              <span className="text-orange-400 font-bold">⚠ SIMOPs Alert: </span>
              <span className="text-gray-300">
                PTW-2851 (HOT_WORK in Coke Oven A) and PTW-2847 (CONFINED_SPACE in B7) are operating concurrently.
                OISD 105 Section 7.2 SIMOPs assessment required.
              </span>
            </div>
          </div>

          {/* OISD 105 checklist reference */}
          <div className="glass-card p-4 mt-4">
            <h2 className="text-sm font-semibold text-white mb-3">OISD 105 Mandatory Checklist</h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                {
                  type: 'CONFINED SPACE',
                  items: [
                    { label: 'Pre-entry atmospheric test (O₂, H₂S, CO)', ok: true },
                    { label: '2-hour retest interval compliance', ok: false },
                    { label: 'Isolation certificate attached', ok: false },
                    { label: 'Rescue plan documented', ok: false },
                    { label: 'SCBA availability confirmed', ok: true },
                    { label: 'Standby personnel assigned', ok: true },
                  ],
                },
                {
                  type: 'HOT WORK',
                  items: [
                    { label: 'Combustibles cleared', ok: true },
                    { label: 'Fire extinguisher at site', ok: true },
                    { label: 'Firewatch assigned', ok: true },
                    { label: 'Isolation from flammable sources', ok: false },
                    { label: 'Gas testing completed', ok: true },
                    { label: 'Adjacent zone notified', ok: false },
                  ],
                },
              ].map(checklist => (
                <div key={checklist.type}>
                  <p className="mono text-xs font-bold text-gray-500 mb-2">{checklist.type}</p>
                  <ul className="space-y-1">
                    {checklist.items.map((item, i) => (
                      <li key={i} className="flex items-center gap-2 text-xs">
                        <span className={item.ok ? 'text-green-400' : 'text-red-400'}>{item.ok ? '✓' : '✗'}</span>
                        <span className={item.ok ? 'text-gray-400' : 'text-red-300/80'}>{item.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* AI Permit validation */}
        <div className="col-span-5">
          <div className="glass-card p-4">
            <PermitIntelCard />
          </div>
        </div>
      </div>
    </div>
  )
}