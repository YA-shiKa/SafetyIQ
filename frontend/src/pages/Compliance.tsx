import { ShieldCheck } from 'lucide-react'
import { CompliancePanel } from '../components/CompliancePanel'
import { useSafetyStore } from '../store/safetyStore'

const MOCK_FINDINGS = [
  { finding_id: 'FIND-001', standard_ref: 'OISD 105 Section 4.3', title: 'No Pre-Entry Atmospheric Test — PTW-2853', severity: 'CRITICAL', zone: 'Raw Material Bay',  days_overdue: 0 },
  { finding_id: 'FIND-002', standard_ref: 'OISD 105 Section 4.3', title: 'Atmospheric Re-test Interval Not Met — PTW-2847', severity: 'CRITICAL', zone: 'Confined Space B7', days_overdue: 0 },
  { finding_id: 'FIND-003', standard_ref: 'OISD 105 Section 6.1', title: 'Isolation Certificate Missing — PTW-2847', severity: 'CRITICAL', zone: 'Confined Space B7', days_overdue: 0 },
  { finding_id: 'FIND-004', standard_ref: 'OISD 105 Section 6.1', title: 'Isolation Certificate Missing — PTW-2851', severity: 'CRITICAL', zone: 'Coke Oven Battery A', days_overdue: 0 },
  { finding_id: 'FIND-005', standard_ref: 'OISD 105 Section 7.2', title: 'SIMOPs Assessment Missing — 3 Concurrent High-Risk Permits', severity: 'MAJOR', zone: 'Multiple Zones', days_overdue: 0 },
  { finding_id: 'FIND-006', standard_ref: 'OISD 116 Section 4.1', title: 'Insufficient SCBA Units — 2 available, 9 required', severity: 'CRITICAL', zone: 'Plant-Wide', days_overdue: 0 },
  { finding_id: 'FIND-007', standard_ref: 'OISD 116 Section 5.2', title: 'Gas Detector Calibration Overdue — H2S Detector Coke Oven A', severity: 'MAJOR', zone: 'Coke Oven Battery A', days_overdue: 93 },
  { finding_id: 'FIND-008', standard_ref: 'OISD 118 Section 8.4', title: 'PRV Inspection Overdue by 17 Days — PRV-004', severity: 'CRITICAL', zone: 'Chemical Storage', days_overdue: 17 },
  { finding_id: 'FIND-009', standard_ref: 'Factory Act 1948 Section 36A', title: 'No Rescue Plan Documented — PTW-2853', severity: 'CRITICAL', zone: 'Raw Material Bay', days_overdue: 0 },
  { finding_id: 'FIND-010', standard_ref: 'DGMS Circular 2019-03', title: 'Emergency Rescue Drill Overdue — Last Conducted 8 Months Ago', severity: 'MAJOR', zone: 'Plant-Wide', days_overdue: 60 },
]

const SEVERITY_STYLES = {
  CRITICAL: 'text-red-400 bg-red-950/20 border-red-800',
  MAJOR:    'text-orange-400 bg-orange-950/15 border-orange-800',
  MINOR:    'text-yellow-400 bg-yellow-950/15 border-yellow-800',
}

export function Compliance() {
  const compliance = useSafetyStore(s => s.compliance)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Quality & Compliance Monitor</h1>
          <p className="text-gray-500 text-xs">Continuous OISD · Factory Act 1948 · DGMS · DGFASLI compliance tracking</p>
        </div>
        <ShieldCheck size={20} className="text-blue-400" />
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Compliance scores */}
        <div className="col-span-4">
          <div className="glass-card p-4">
            <CompliancePanel />
          </div>
        </div>

        {/* Findings table */}
        <div className="col-span-8">
          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">
                Open Findings
                <span className="mono text-xs text-gray-500 font-normal ml-2">
                  {MOCK_FINDINGS.filter(f => f.severity === 'CRITICAL').length} critical ·{' '}
                  {MOCK_FINDINGS.filter(f => f.severity === 'MAJOR').length} major
                </span>
              </h2>
            </div>
            <div className="space-y-1.5 max-h-[520px] overflow-y-auto pr-1">
              {MOCK_FINDINGS.map(f => (
                <div
                  key={f.finding_id}
                  className={`p-2.5 rounded border text-xs ${
                    f.severity === 'CRITICAL' ? 'border-red-900/50 bg-red-950/15'
                    : f.severity === 'MAJOR'   ? 'border-orange-900/40 bg-orange-950/10'
                    : 'border-yellow-900/40 bg-yellow-950/10'
                  }`}
                >
                  <div className="flex items-start gap-2 justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <span className={`mono text-xs font-bold px-1 py-0.5 rounded border ${SEVERITY_STYLES[f.severity as keyof typeof SEVERITY_STYLES]}`}>
                          {f.severity}
                        </span>
                        <span className="mono text-blue-400/70">{f.standard_ref}</span>
                        {f.days_overdue > 0 && (
                          <span className="text-red-400">+{f.days_overdue}d overdue</span>
                        )}
                      </div>
                      <p className="text-white font-medium leading-snug">{f.title}</p>
                      <p className="text-gray-500 mt-0.5">{f.zone}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}