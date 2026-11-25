import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  Loader2,
  RefreshCw,
  Search,
  UserPlus,
  Users,
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

function formatUpdatedAt(isoString) {
  if (!isoString) return 'Not available'
  const parsed = new Date(isoString)
  if (Number.isNaN(parsed.getTime())) return isoString
  return parsed.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function PatientManagement() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const {
    patients,
    selectedPatientId,
    selectPatient,
    loading,
    error,
    refreshPatients,
  } = usePatient()

  const normalizedQuery = query.trim().toLowerCase()
  const filtered = patients.filter((p) => {
    if (!normalizedQuery) return true
    const nameMatch = (p.name || '').toLowerCase().includes(normalizedQuery)
    const idMatch = (p.patient_id || '').toLowerCase().includes(normalizedQuery)
    return nameMatch || idMatch
  })

  const handleInspect = (patientId) => {
    selectPatient(patientId)
    navigate('/intelligence')
  }

  return (
    <div>
      <PageHeader
        title="Patient Management"
        subtitle="Live patient records from the CLINIQ AI backend. Select a patient to inspect clinical intelligence."
        badge={error ? 'Backend Unavailable' : 'Live Backend • GET /patients'}
        badgeTone={error ? 'attention_needed' : 'normal'}
        actions={
          <>
            <button
              type="button"
              onClick={refreshPatients}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:text-white disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <Link
              to="/documents"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
            >
              <UserPlus className="h-4 w-4" />
              Upload Patient PDF
            </Link>
          </>
        }
      />

      {error && (
        <GlassCard hover={false} className="mb-6 border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Failed to fetch patient records</h2>
                <p className="mt-1 text-xs text-rose-200/90">{error}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={refreshPatients}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 px-4 py-2 text-xs font-semibold text-rose-200 transition hover:bg-rose-500/25"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        </GlassCard>
      )}

      <GlassCard hover={false} className="p-5">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search patients by name or patient ID..."
              className="w-full rounded-xl border border-slate-700/80 bg-[#080F20] py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Users className="h-4 w-4 text-cyan-400" />
            Showing {filtered.length} of {patients.length} patient(s)
          </div>
        </div>

        {loading && patients.length === 0 ? (
          <div className="flex items-center justify-center gap-3 py-12 text-sm text-slate-300">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
            <span>Loading patients from CLINIQ AI backend...</span>
          </div>
        ) : patients.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 py-12 text-center">
            <p className="text-sm font-semibold text-white">No patients found</p>
            <p className="mt-1 text-xs text-slate-400">
              {error ? 'Retry once the FastAPI backend is reachable.' : 'Upload a clinical PDF to register a patient record.'}
            </p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 py-10 text-center text-xs text-slate-400">
            No patients match &ldquo;{query}&rdquo;.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                  <th className="pb-3 pr-4">Patient ID</th>
                  <th className="pb-3 pr-4">Name</th>
                  <th className="pb-3 pr-4">Age</th>
                  <th className="pb-3 pr-4">Sex</th>
                  <th className="pb-3 pr-4">Reports</th>
                  <th className="pb-3 pr-4">Updated At</th>
                  <th className="pb-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {filtered.map((p) => {
                  const isActive = p.patient_id === selectedPatientId
                  return (
                    <tr
                      key={p.patient_id}
                      className={`transition hover:bg-slate-900/40 ${isActive ? 'bg-cyan-500/5' : ''}`}
                    >
                      <td className="py-3.5 pr-4 font-mono text-xs text-cyan-300">
                        <div className="flex flex-wrap items-center gap-2">
                          <span>{p.patient_id}</span>
                          {isActive && <StatusBadge label="Active" tone="info" />}
                        </div>
                      </td>
                      <td className="py-3.5 pr-4 font-semibold text-white">
                        {p.name || <span className="text-slate-500">Not recorded</span>}
                      </td>
                      <td className="py-3.5 pr-4 text-slate-300">{p.age || '—'}</td>
                      <td className="py-3.5 pr-4 text-slate-300">{p.sex || '—'}</td>
                      <td className="py-3.5 pr-4 font-semibold text-white">{p.report_count ?? 0}</td>
                      <td className="py-3.5 pr-4 text-xs text-slate-400">
                        {formatUpdatedAt(p.updated_at)}
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleInspect(p.patient_id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-cyan-300 transition hover:border-cyan-500/40 hover:bg-cyan-500/10"
                        >
                          Inspect <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
