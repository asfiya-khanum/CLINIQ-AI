import { Link } from 'react-router-dom'
import { RefreshCw, Users } from 'lucide-react'
import { usePatient } from '../context/patientContextStore'
import GlassCard from './GlassCard'

export default function PatientSelectorBar({ onRefresh = null, refreshing = false }) {
  const {
    patients,
    selectedPatientId,
    selectedPatient,
    selectPatient,
    loading: patientsLoading,
    error: patientsError,
    refreshPatients,
  } = usePatient()

  const handleRefreshAll = () => {
    refreshPatients()
    if (onRefresh) {
      onRefresh()
    }
  }

  return (
    <GlassCard hover={false} className="p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-cyan-500/25 bg-cyan-500/10 text-cyan-300">
            <Users className="h-4 w-4" />
          </div>
          <div>
            <label
              htmlFor="active-patient-select"
              className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400"
            >
              Active Patient
            </label>
            {patientsLoading && patients.length === 0 ? (
              <span className="text-xs text-slate-300">Loading patient directory...</span>
            ) : patients.length === 0 ? (
              <span className="text-xs text-slate-400">
                {patientsError || 'No patients found in database.'}
              </span>
            ) : (
              <select
                id="active-patient-select"
                value={selectedPatientId || ''}
                onChange={(e) => selectPatient(e.target.value)}
                className="mt-0.5 rounded-lg border border-slate-700 bg-[#080F20] px-3 py-1.5 text-sm font-semibold text-white focus:border-cyan-400 focus:outline-none"
              >
                {patients.map((patient) => (
                  <option key={patient.patient_id} value={patient.patient_id}>
                    {patient.name || 'Unnamed Patient'} ({patient.patient_id}) •{' '}
                    {patient.report_count ?? 0} report(s)
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
          {selectedPatient && (
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-800 bg-[#081021]/90 px-3 py-1.5">
              <span>
                ID: <code className="text-cyan-300">{selectedPatient.patient_id}</code>
              </span>
              <span className="text-slate-600">•</span>
              <span>Age: {selectedPatient.age || 'N/A'}</span>
              <span className="text-slate-600">•</span>
              <span>Sex: {selectedPatient.sex || 'N/A'}</span>
            </div>
          )}

          <button
            type="button"
            onClick={handleRefreshAll}
            disabled={refreshing || patientsLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/90 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:text-white disabled:opacity-60"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 text-cyan-400 ${refreshing || patientsLoading ? 'animate-spin' : ''}`}
            />
            Refresh
          </button>

          <Link
            to="/patients"
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300"
          >
            All Patients →
          </Link>
        </div>
      </div>
    </GlassCard>
  )
}
