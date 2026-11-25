import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  Clock3,
  FileText,
  Info,
  Loader2,
  RefreshCw,
  Sparkles,
  UploadCloud,
  Users,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { extractApiError } from '../api/client'
import { getDashboardOverview } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

const SEVERITY_META = [
  { key: 'attention_needed', label: 'Attention Needed', color: '#F43F5E' },
  { key: 'review_recommended', label: 'Review Recommended', color: '#F59E0B' },
  { key: 'normal', label: 'Normal', color: '#10B981' },
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-cyan-500/30 bg-[#0A1223]/95 px-3.5 py-2.5 text-xs shadow-xl backdrop-blur-md">
      <p className="mb-1 font-semibold text-white">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="flex items-center justify-between gap-4 text-slate-300">
          <span>{entry.name}:</span>
          <span className="font-bold text-cyan-300">{entry.value}</span>
        </p>
      ))}
    </div>
  )
}

function formatDateLabel(report) {
  return report?.study_date_iso || report?.study_date || (report?.created_at ? report.created_at.slice(0, 10) : 'Undated')
}

export default function OverviewDashboard() {
  const { selectedPatient, loading: patientLoading, error: patientError } = usePatient()

  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const requestSeqRef = useRef(0)

  const handleRetry = useCallback(async () => {
    const reqId = ++requestSeqRef.current
    setLoading(true)
    setError(null)
    try {
      const data = await getDashboardOverview()
      if (reqId === requestSeqRef.current) {
        setOverview(data)
      }
    } catch (err) {
      if (reqId === requestSeqRef.current) {
        setError(extractApiError(err, 'Failed to load dashboard overview from FastAPI backend.'))
      }
    } finally {
      if (reqId === requestSeqRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    const reqId = ++requestSeqRef.current
    getDashboardOverview()
      .then((data) => {
        if (reqId === requestSeqRef.current) {
          setOverview(data)
        }
      })
      .catch((err) => {
        if (reqId === requestSeqRef.current) {
          setError(extractApiError(err, 'Failed to load dashboard overview from FastAPI backend.'))
        }
      })
      .finally(() => {
        if (reqId === requestSeqRef.current) {
          setLoading(false)
        }
      })

    return () => {
      requestSeqRef.current += 1
    }
  }, [])

  const cards = overview?.cards || {}

  const severityChartData = useMemo(() => {
    const dist = overview?.severity_distribution || {}
    return SEVERITY_META.map((item) => ({
      name: item.label,
      count: Number(dist[item.key] ?? 0),
      color: item.color,
    }))
  }, [overview])

  const categoryChartData = useMemo(() => {
    const breakdown = overview?.category_breakdown || {}
    return Object.entries(breakdown).map(([category, count]) => ({
      category,
      count: Number(count ?? 0),
    }))
  }, [overview])

  const recentReports = Array.isArray(overview?.recent_reports) ? overview.recent_reports : []
  const hasAnySeverityData = severityChartData.some((d) => d.count > 0)

  return (
    <div className="space-y-6">
      {/* Welcome Hero */}
      <GlassCard hover={false} className="relative overflow-hidden p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-12 -top-12 h-56 w-56 rounded-full bg-cyan-500/10 blur-2xl" />
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <StatusBadge label="CLINIQ AI" tone="info" />
              <StatusBadge
                label={error ? 'Backend Unavailable' : 'Live Backend • GET /dashboard/overview'}
                tone={error ? 'attention_needed' : 'normal'}
              />
            </div>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              CLINIQ <span className="text-cyan-400">AI</span> — Clinical Intelligence Command
            </h1>
            <p className="mt-2.5 text-sm leading-relaxed text-slate-300">
              Clinical intelligence dashboard for unifying medical PDFs, reviewing deterministic
              abnormal flags, inspecting chronological timelines, and supporting clinician verification.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleRetry}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:text-white disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <Link
              to="/documents"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_0_24px_rgba(6,182,212,0.3)] transition hover:brightness-110"
            >
              <UploadCloud className="h-4 w-4" />
              Upload Reports
            </Link>
            <Link
              to="/intelligence"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:text-white"
            >
              <BrainCircuit className="h-4 w-4 text-cyan-400" />
              Patient Intelligence
            </Link>
          </div>
        </div>

        {/* Active Session Patient Strip */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-[#081021]/80 px-4 py-3 text-xs">
          <div className="flex flex-wrap items-center gap-3 text-slate-300">
            <span className="font-semibold text-cyan-300">Selected Session Patient:</span>
            {patientLoading ? (
              <span className="text-slate-400">Loading patient directory...</span>
            ) : patientError ? (
              <span className="text-rose-300">{patientError}</span>
            ) : selectedPatient ? (
              <>
                <span className="font-bold text-white">{selectedPatient.name || 'Unnamed Patient'}</span>
                <span className="text-slate-500">|</span>
                <span>
                  ID: <code className="text-cyan-300">{selectedPatient.patient_id}</code>
                </span>
                <span className="text-slate-500">|</span>
                <span>
                  {selectedPatient.age || 'Age N/A'}, {selectedPatient.sex || 'Sex N/A'}
                </span>
                <span className="text-slate-500">|</span>
                <span>{selectedPatient.report_count ?? 0} report(s)</span>
              </>
            ) : (
              <span className="text-slate-400">No patients found in database yet.</span>
            )}
          </div>
          <Link to="/patients" className="font-semibold text-cyan-400 hover:text-cyan-300">
            Switch Patient →
          </Link>
        </div>
      </GlassCard>

      {/* Error State Banner */}
      {error && (
        <GlassCard hover={false} className="border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Could not load dashboard overview</h2>
                <p className="mt-1 text-xs text-rose-200/90">{error}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleRetry}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 px-4 py-2 text-xs font-semibold text-rose-200 transition hover:bg-rose-500/25"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        </GlassCard>
      )}

      {/* Loading State */}
      {loading && !overview ? (
        <GlassCard hover={false} className="flex items-center justify-center gap-3 p-12 text-sm text-slate-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
          <span>Fetching clinical metrics from CLINIQ AI backend...</span>
        </GlassCard>
      ) : (
        <>
          {/* Live Patient & Report Statistics Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Total Patients"
              value={cards.total_patients ?? 0}
              subtitle="Registered SQLite patient records"
              icon={Users}
              accent="cyan"
            />
            <StatCard
              label="Total Reports"
              value={cards.total_reports ?? 0}
              subtitle="Processed clinical PDF documents"
              icon={FileText}
              accent="blue"
            />
            <StatCard
              label="Attention Needed"
              value={cards.attention_needed_reports ?? 0}
              subtitle="Reports with high-priority rule flags"
              icon={AlertTriangle}
              accent="rose"
            />
            <StatCard
              label="Review Recommended"
              value={cards.review_recommended_reports ?? 0}
              subtitle="Reports with moderate rule flags"
              icon={Activity}
              accent="amber"
            />
          </div>

          {/* Recharts Severity & Category Breakdown */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <GlassCard className="p-5 lg:col-span-6">
              <div className="mb-4 flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-white">Severity Distribution</h2>
                  <p className="text-xs text-slate-400">
                    Live report breakdown by rule-based severity level
                  </p>
                </div>
                <StatusBadge label="Live API Data" tone="info" />
              </div>
              {hasAnySeverityData ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={severityChartData} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="name" stroke="#64748B" fontSize={12} tickLine={false} />
                      <YAxis allowDecimals={false} stroke="#64748B" fontSize={12} tickLine={false} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Reports" radius={[8, 8, 0, 0]}>
                        {severityChartData.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-slate-800 text-xs text-slate-400">
                  No processed reports available to chart severity distribution.
                </div>
              )}
            </GlassCard>

            <GlassCard className="p-5 lg:col-span-6">
              <div className="mb-4 flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-white">Findings by Category</h2>
                  <p className="text-xs text-slate-400">
                    Rule-based abnormal finding category counts across reports
                  </p>
                </div>
                <StatusBadge label="Live API Data" tone="info" />
              </div>
              {categoryChartData.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={categoryChartData} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="category" stroke="#64748B" fontSize={11} tickLine={false} />
                      <YAxis allowDecimals={false} stroke="#64748B" fontSize={12} tickLine={false} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Flagged Findings" fill="#22D3EE" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-slate-800 text-xs text-slate-400">
                  No abnormal finding categories recorded yet.
                </div>
              )}
            </GlassCard>
          </div>

          {/* Recent Reports + Quick Actions */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <GlassCard className="p-5 lg:col-span-7">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white">Recent Reports</h2>
                  <p className="text-xs text-slate-400">Latest reports returned by GET /dashboard/overview</p>
                </div>
                <Link to="/timeline" className="inline-flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300">
                  Clinical timeline <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>

              {recentReports.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs text-slate-400">
                  No reports have been uploaded yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {recentReports.map((report) => {
                    const studyTitle = report.medical_info?.study_name || report.filename || `Report #${report.report_id}`
                    const severity = report.severity || 'normal'
                    return (
                      <div
                        key={report.report_id}
                        className="flex flex-col justify-between gap-2 rounded-xl border border-slate-800/80 bg-[#091022]/80 p-3.5 sm:flex-row sm:items-center"
                      >
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-semibold text-white">{studyTitle}</span>
                            <span className="font-mono text-xs text-cyan-300">{report.patient_id}</span>
                            <span className="text-[11px] text-slate-500">#{report.report_id}</span>
                          </div>
                          <p className="mt-1 truncate text-xs text-slate-400">
                            {report.clinical_summary || report.filename || 'No clinical summary generated.'}
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <span className="text-xs text-slate-500">{formatDateLabel(report)}</span>
                          <StatusBadge label={severity.replace(/_/g, ' ')} tone={severity} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </GlassCard>

            <GlassCard className="p-5 lg:col-span-5">
              <h2 className="text-base font-bold text-white">Quick Actions</h2>
              <p className="mt-1 text-xs text-slate-400">Navigate directly to core CLINIQ AI modules</p>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1">
                {[
                  { to: '/patients', label: 'Manage Patients', desc: 'Select active patient from SQLite roster', icon: Users },
                  { to: '/timeline', label: 'Inspect Clinical Timeline', desc: 'Chronological study progression', icon: Clock3 },
                  { to: '/conflicts', label: 'Review Conflict Intelligence', desc: 'Missing fields & contradictions', icon: AlertTriangle },
                  { to: '/reconstruction', label: 'Patient Reconstruction', desc: 'Rule-based vs AI pipeline view', icon: Sparkles },
                ].map(({ to, label, desc, icon: Icon }) => (
                  <Link
                    key={to}
                    to={to}
                    className="group flex items-center justify-between rounded-xl border border-slate-800 bg-[#091022]/90 p-3.5 transition hover:border-cyan-500/40 hover:bg-slate-900"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{label}</div>
                        <div className="text-xs text-slate-400">{desc}</div>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-1 group-hover:text-cyan-400" />
                  </Link>
                ))}
              </div>
            </GlassCard>
          </div>

          {/* Clinical Disclaimer Footer */}
          {overview?.clinical_disclaimer && (
            <div className="flex items-start gap-2.5 rounded-xl border border-slate-800/80 bg-[#091022]/70 px-4 py-3 text-xs text-slate-400">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
              <span>{overview.clinical_disclaimer}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
