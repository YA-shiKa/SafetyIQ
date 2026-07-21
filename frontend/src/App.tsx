import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { SensorsPage } from './pages/SensorsPage'
import { PermitCenter } from './pages/PermitCenter'
import { IncidentHub } from './pages/IncidentHub'
import { Compliance } from './pages/Compliance'
import { useSensorStream } from './hooks/useSensorStream'
import { useRiskScore } from './hooks/useRiskScore'
import { useSafetyStore } from './store/safetyStore'

function AppLayout() {
  useSensorStream()
  useRiskScore(15000)

  const emergencyActive = useSafetyStore(s => s.emergencyActive)
  const emergencyZone   = useSafetyStore(s => s.emergencyZone)
  const clearEmergency  = useSafetyStore(s => s.clearEmergency)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <main className="flex-1 overflow-auto p-5 min-w-0">
        {/* Emergency banner */}
        {emergencyActive && (
          <div className="mb-4 p-3 bg-red-600 text-white rounded-lg flex items-center justify-between critical-pulse">
            <div className="flex items-center gap-3">
              <span className="text-lg">🚨</span>
              <div>
                <div className="font-bold">EMERGENCY RESPONSE ACTIVE</div>
                <div className="text-red-100 text-sm">
                  Zone: {emergencyZone} · Evacuation in progress · All permits suspended
                </div>
              </div>
            </div>
            <button
              onClick={clearEmergency}
              className="px-3 py-1 bg-red-800 hover:bg-red-900 rounded text-sm font-semibold transition-colors"
            >
              Clear
            </button>
          </div>
        )}

        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/sensors"    element={<SensorsPage />} />
          <Route path="/permits"    element={<PermitCenter />} />
          <Route path="/incidents"  element={<IncidentHub />} />
          <Route path="/compliance" element={<Compliance />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}