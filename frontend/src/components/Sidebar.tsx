import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, FileCheck, BookOpen, ShieldCheck, Siren, Wifi, WifiOff } from 'lucide-react'
import { useSafetyStore } from '../store/safetyStore'
import clsx from 'clsx'

const NAV = [
  { to: '/',           icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/sensors',    icon: Activity,         label: 'Sensors' },
  { to: '/permits',    icon: FileCheck,        label: 'Permit Intel' },
  { to: '/incidents',  icon: BookOpen,         label: 'Incidents' },
  { to: '/compliance', icon: ShieldCheck,      label: 'Compliance' },
]

export function Sidebar() {
  const { wsConnected, plantRiskScore, alerts } = useSafetyStore()
  const unackAlerts = alerts.filter(a => !a.acknowledged).length

  const riskColor = plantRiskScore >= 91 ? '#DC2626'
    : plantRiskScore >= 76 ? '#EF4444'
    : plantRiskScore >= 56 ? '#F97316'
    : plantRiskScore >= 31 ? '#EAB308'
    : '#22C55E'

  return (
    <aside className="w-52 flex-shrink-0 flex flex-col h-screen bg-surface-900 border-r border-white/5">
      {/* Logo */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Siren size={14} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-white text-sm leading-tight">SafetyIQ</div>
            <div className="text-gray-600 text-xs">Vizag Steel Complex</div>
          </div>
        </div>
      </div>

      {/* Live status bar */}
      <div className="px-3 py-2 border-b border-white/5">
        <div className="glass-card p-2 flex items-center gap-2">
          <div className="flex-1">
            <div className="text-gray-500 text-xs mb-0.5">Plant Risk</div>
            <div className="mono font-bold text-base" style={{ color: riskColor }}>
              {plantRiskScore}/100
            </div>
          </div>
          <div className="text-right">
            {wsConnected
              ? <Wifi size={13} className="text-green-400" />
              : <WifiOff size={13} className="text-gray-600 animate-pulse" />
            }
            <div className="text-xs text-gray-600 mono">{wsConnected ? 'LIVE' : 'OFF'}</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 space-y-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => clsx(
              'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'bg-blue-600/20 text-blue-400 font-medium'
                : 'text-gray-500 hover:text-gray-200 hover:bg-white/5'
            )}
          >
            <Icon size={15} />
            {label}
            {label === 'Dashboard' && unackAlerts > 0 && (
              <span className="ml-auto mono text-xs bg-red-600 text-white px-1.5 py-0.5 rounded-full">
                {unackAlerts}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-white/5">
        <div className="text-gray-700 text-xs leading-relaxed">
          <div className="font-medium text-gray-500">DGFASLI Reg. AP/VSP/2024/001</div>
          <div>Factory Lic. APFACT/2024/VSP/0042</div>
        </div>
      </div>
    </aside>
  )
}