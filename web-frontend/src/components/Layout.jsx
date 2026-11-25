import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Clock3,
  Cpu,
  FileText,
  LayoutDashboard,
  Menu,
  Pill,
  ShieldAlert,
  Users,
  X,
} from 'lucide-react'
import { API_BASE_URL } from '../api/client'
import StatusBadge from './StatusBadge'

export const NAV_ITEMS = [
  { label: 'Overview Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Patient Management', path: '/patients', icon: Users },
  { label: 'Document Center', path: '/documents', icon: FileText },
  { label: 'Patient Intelligence', path: '/intelligence', icon: BrainCircuit },
  { label: 'Clinical Timeline', path: '/timeline', icon: Clock3 },
  { label: 'Medication Reconciliation', path: '/medications', icon: Pill },
  { label: 'Conflict Intelligence', path: '/conflicts', icon: AlertTriangle },
  { label: 'Patient Reconstruction', path: '/reconstruction', icon: Cpu },
]

function SidebarContent({ onNavigate }) {
  return (
    <div className="flex h-full flex-col justify-between bg-[#060B17]/95 px-4 py-6">
      <div>
        <div className="mb-6 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-[0_0_24px_rgba(6,182,212,0.35)]">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-lg font-extrabold tracking-tight text-white">
              CLINIQ <span className="text-cyan-400">AI</span>
            </div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Clinical Intelligence
            </div>
          </div>
        </div>

        <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          Workspace
        </div>

        <nav className="space-y-1.5" aria-label="Primary Sidebar Navigation">
          {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              onClick={onNavigate}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'border border-cyan-500/40 bg-gradient-to-r from-cyan-500/15 to-blue-600/15 text-cyan-200 shadow-[0_0_20px_rgba(6,182,212,0.12)]'
                    : 'border border-transparent text-slate-400 hover:border-slate-800 hover:bg-slate-900/70 hover:text-slate-100'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0 transition-transform duration-200 group-hover:scale-110" />
              <span className="truncate">{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="mt-6 space-y-3">
        <div className="rounded-xl border border-slate-800/90 bg-[#0B1325] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              API Configuration
            </span>
            <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
          </div>
          <p className="mt-2 truncate font-mono text-xs text-cyan-300">
            {API_BASE_URL}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            UI shell mode • Backend integration pending Step 2
          </p>
        </div>
        <div className="px-2 text-[11px] text-slate-500">
          MEDUSA-X / CLINIQ AI • React + Vite
        </div>
      </div>
    </div>
  )
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const activeRoute = NAV_ITEMS.find((item) => item.path === location.pathname) || NAV_ITEMS[0]

  return (
    <div className="min-h-screen bg-[#080D1B] text-slate-100">
      {/* Ambient radial backdrop */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-blue-600/10 blur-3xl" />
        <div className="absolute right-0 top-1/4 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl" />
      </div>

      {/* Desktop Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-slate-800/80 lg:block">
        <SidebarContent onNavigate={() => {}} />
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-10 h-full w-72 border-r border-slate-800">
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
              className="absolute right-3 top-5 rounded-lg border border-slate-700 bg-slate-900 p-1.5 text-slate-300 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="relative z-10 flex min-h-screen flex-col lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-[#080D1B]/80 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation menu"
                className="rounded-lg border border-slate-800 bg-slate-900/90 p-2 text-slate-300 hover:border-cyan-500/40 hover:text-white lg:hidden"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <div className="text-xs font-medium text-slate-400">
                  CLINIQ AI Platform
                </div>
                <div className="text-sm font-semibold text-white">
                  {activeRoute.label}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <StatusBadge label="Fictional Demo Preview" tone="demo" />
              <span className="hidden items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1 text-xs text-slate-300 sm:inline-flex">
                <ShieldAlert className="h-3.5 w-3.5 text-cyan-400" />
                Clinician review required • Non-diagnostic
              </span>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div key={location.pathname} className="animate-fade-in">
            <Outlet />
          </div>
        </main>

        <footer className="border-t border-slate-800/70 px-4 py-4 text-center text-xs text-slate-500 sm:px-6 lg:px-8">
          MEDUSA-X / CLINIQ AI · Informational Clinical Intelligence Prototype ·
          All displayed records in this shell are fictional placeholders pending backend integration.
        </footer>
      </div>
    </div>
  )
}
