import { BookOpen } from 'lucide-react'
import { IncidentTimeline } from '../components/IncidentTimeline'

const RECENT_INCIDENTS = [
  { id: 'NM-2025-003', date: '2025-01-10', type: 'NEAR_MISS', zone: 'Blast Furnace',    color: 'text-yellow-400', desc: 'Gas sensor alarm ignored for 8 minutes due to alert fatigue. No injury.' },
  { id: 'NM-2025-002', date: '2025-01-07', type: 'NEAR_MISS', zone: 'Chemical Storage', color: 'text-yellow-400', desc: 'Pressure anomaly undetected for 3 hours — SCADA operator on break.' },
  { id: 'INC-2024-047', date: '2024-08-22', type: 'NEAR_MISS', zone: 'Blast Furnace Zone', color: 'text-yellow-400', desc: 'Hot work commenced 8m from elevated CO area. Isolation not confirmed in PTW.' },
  { id: 'INC-2024-018', date: '2024-03-11', type: 'INJURY',    zone: 'Chemical Storage',   color: 'text-orange-400', desc: 'PRV failed — tank pressure trending up for 6 hours. 3 workers with chemical burns.' },
  { id: 'INC-2023-092', date: '2023-11-05', type: 'FATALITY',  zone: 'Confined Space',     color: 'text-red-400',    desc: 'Worker asphyxiated. O₂ at 17.8%. Entry without SCBA despite reading.' },
  { id: 'INC-2023-031', date: '2023-04-18', type: 'DANGEROUS', zone: 'Hot Strip Mill',     color: 'text-orange-400', desc: 'Flash fire from concurrent hot work + confined space entry in adjacent zones.' },
]

const TYPE_BADGES: Record<string, string> = {
  NEAR_MISS:  'text-yellow-400 bg-yellow-950/20 border-yellow-800',
  INJURY:     'text-orange-400 bg-orange-950/20 border-orange-800',
  FATALITY:   'text-red-400 bg-red-950/20 border-red-800',
  DANGEROUS:  'text-orange-500 bg-orange-950/25 border-orange-700',
}

export function IncidentHub() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Incident Pattern Intelligence</h1>
          <p className="text-gray-500 text-xs">RAG-powered analysis over historical incidents, near-misses & OISD/Factory Act corpus</p>
        </div>
        <BookOpen size={20} className="text-blue-400" />
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Pattern analysis */}
        <div className="col-span-7">
          <div className="glass-card p-4">
            <IncidentTimeline />
          </div>
        </div>

        {/* Incident log */}
        <div className="col-span-5">
          <div className="glass-card p-4">
            <h2 className="text-sm font-semibold text-white mb-3">Incident Log</h2>
            <div className="space-y-2">
              {RECENT_INCIDENTS.map(inc => (
                <div key={inc.id} className="border-b border-white/5 pb-2 last:border-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`mono text-xs px-1.5 py-0.5 rounded border ${TYPE_BADGES[inc.type] ?? TYPE_BADGES.DANGEROUS}`}>
                      {inc.type}
                    </span>
                    <span className="text-gray-600 text-xs mono">{inc.date}</span>
                    <span className="text-gray-500 text-xs ml-auto">{inc.zone}</span>
                  </div>
                  <p className="text-gray-400 text-xs leading-relaxed">{inc.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Regulatory corpus */}
          <div className="glass-card p-4 mt-4">
            <h2 className="text-sm font-semibold text-white mb-3">RAG Corpus Coverage</h2>
            <div className="space-y-2">
              {[
                { source: 'OISD 105', desc: 'Permit-to-Work system', clauses: 12 },
                { source: 'OISD 116', desc: 'Gas/atmospheric hazards', clauses: 8 },
                { source: 'OISD 118', desc: 'Pressure vessels', clauses: 6 },
                { source: 'Factory Act 1948', desc: 'Sections 7A, 36, 36A, 38, 40', clauses: 15 },
                { source: 'DGMS Circulars', desc: '2019-03, 2021-07', clauses: 4 },
                { source: 'DGFASLI Form 18', desc: 'Incident notification', clauses: 1 },
              ].map(item => (
                <div key={item.source} className="flex items-center justify-between text-xs">
                  <div>
                    <span className="mono text-blue-400 font-medium">{item.source}</span>
                    <span className="text-gray-500 ml-2">{item.desc}</span>
                  </div>
                  <span className="mono text-gray-600">{item.clauses} clauses</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}