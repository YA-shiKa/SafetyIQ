import { useState } from 'react'
import { RefreshCw, Cpu } from 'lucide-react'
import { RiskScoreGauge } from '../components/RiskScoreGauge'
import { AlertPanel } from '../components/AlertPanel'
import { RiskHeatmap } from '../components/RiskHeatmap'
import { EmergencyPanel } from '../components/EmergencyPanel'
import { CompliancePanel } from '../components/CompliancePanel'
import { api } from '../services/api'
import { useSafetyStore } from '../store/safetyStore'
import type { AnalysisResult } from '../types'
import clsx from 'clsx'

export function Dashboard() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const { setLastAnalysisAt, wsConnected } = useSafetyStore()

  const runAnalysis = async () => {
    setAnalyzing(true)
    try {
      const result = await api.analysis.run()
      setAnalysisResult(result)
      setLastAnalysisAt(result.timestamp)
    } catch (e) {
      console.error('Analysis failed', e)
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Top bar */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold text-white">Operations Dashboard</h1>
          <p className="text-gray-500 text-xs">Real-time compound risk monitoring · Visakhapatnam Steel Complex</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={clsx(
            'flex items-center gap-1.5 mono text-xs px-2 py-1 rounded-full border',
            wsConnected
              ? 'text-green-400 border-green-800 bg-green-950/20'
              : 'text-gray-600 border-gray-800 bg-gray-950/20'
          )}>
            <div className={clsx('w-1.5 h-1.5 rounded-full', wsConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-600')} />
            {wsConnected ? 'LIVE' : 'CONNECTING'}
          </div>
          <button
            onClick={runAnalysis}
            disabled={analyzing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 text-white text-xs font-semibold rounded transition-colors mono"
          >
            <RefreshCw size={12} className={analyzing ? 'animate-spin' : ''} />
            {analyzing ? 'Analyzing...' : 'Run AI Analysis'}
          </button>
        </div>
      </div>

      {/* Main grid */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0 overflow-auto">

        {/* Col 1: Risk gauge + emergency */}
        <div className="col-span-3 flex flex-col gap-4">
          <div className="glass-card p-4 flex flex-col items-center gap-2">
            <p className="text-gray-500 text-xs font-medium tracking-wider">PLANT RISK SCORE</p>
            <RiskScoreGauge />
            <p className="text-gray-600 text-xs text-center">
              Compound signals fused across {8} sensors
            </p>
          </div>

          <div className="glass-card p-4 flex-1">
            <CompliancePanel />
          </div>
        </div>

        {/* Col 2: Zone heatmap */}
        <div className="col-span-5 flex flex-col gap-4">
          <div className="glass-card p-4 flex-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              <span className="font-semibold text-sm text-white">Zone Risk Heatmap</span>
              <span className="mono text-xs text-gray-600 ml-auto">
                {new Date().toLocaleTimeString()}
              </span>
            </div>
            <RiskHeatmap />
          </div>

          {/* AI Analysis result */}
          {analysisResult && (
            <div className="glass-card p-4 border border-blue-900/40">
              <div className="flex items-center gap-2 mb-3">
                <Cpu size={14} className="text-blue-400" />
                <span className="font-semibold text-sm text-white">AI Analysis Results</span>
                <span className="mono text-xs text-gray-600 ml-auto">
                  Score: {analysisResult.plant_risk_score}/100
                </span>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {analysisResult.compound_risks.map(risk => (
                  <div
                    key={risk.event_id}
                    className={clsx(
                      'p-2 rounded border text-xs',
                      risk.risk_level === 'CRITICAL' ? 'border-red-800/50 bg-red-950/20' :
                      risk.risk_level === 'HIGH'     ? 'border-orange-800/40 bg-orange-950/15' :
                      'border-yellow-800/30 bg-yellow-950/10'
                    )}
                  >
                    <div className="font-semibold text-white mb-0.5">{risk.title}</div>
                    <div className="text-gray-400">{risk.description}</div>
                    {risk.recommended_actions[0] && (
                      <div className="text-green-400/80 mt-1">→ {risk.recommended_actions[0]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Col 3: Alerts + emergency */}
        <div className="col-span-4 flex flex-col gap-4">
          <div className="glass-card p-4 flex-1 min-h-0 flex flex-col" style={{ maxHeight: 480 }}>
            <AlertPanel />
          </div>
          <EmergencyPanel />
        </div>
      </div>
    </div>
  )
}