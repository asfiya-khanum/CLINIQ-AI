import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Info,
  Loader2,
  Pill,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react'
import { extractApiError } from '../api/client'
import { getPatientAnalysis } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import PatientSelectorBar from '../components/PatientSelectorBar'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

export default function MedicationReconciliation() {
  const { selectedPatientId, loading: patientsLoading } = usePatient()

  const [state, setState] = useState({ data: null, error: null, resolvedPatientId: null })
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const requestSeqRef = useRef(0)

  // Session-only clinician notes (explicitly not persisted to SQLite)
  const [notesState, setNotesState] = useState({ forPatientId: null, draft: '', saved: '' })

  const handleRetry = useCallback(async () => {
    if (!selectedPatientId) return
    const reqId = ++requestSeqRef.current
    setManualRefreshing(true)
    try {
      const data = await getPatientAnalysis(selectedPatientId)
      if (reqId === requestSeqRef.current) {
        setState({ data, error: null, resolvedPatientId: selectedPatientId })
      }
    } catch (err) {
      if (reqId === requestSeqRef.current) {
        setState({
          data: null,
          error: extractApiError(err, 'Failed to load medication status comparison data.'),
          resolvedPatientId: selectedPatientId,
        })
      }
    } finally {
      if (reqId === requestSeqRef.current) {
        setManualRefreshing(false)
      }
    }
  }, [selectedPatientId])

  useEffect(() => {
    if (!selectedPatientId) return undefined
    let cancelled = false
    const reqId = ++requestSeqRef.current

    getPatientAnalysis(selectedPatientId)
      .then((data) => {
        if (!cancelled && reqId === requestSeqRef.current) {
          setState({ data, error: null, resolvedPatientId: selectedPatientId })
        }
      })
      .catch((err) => {
        if (!cancelled && reqId === requestSeqRef.current) {
          setState({
            data: null,
            error: extractApiError(err, 'Failed to load medication status comparison data.'),
            resolvedPatientId: selectedPatientId,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedPatientId])

  const isCurrent = selectedPatientId && state.resolvedPatientId === selectedPatientId
  const analysis = isCurrent ? state.data : null
  const error = isCurrent ? state.error : null
  const loading = Boolean(selectedPatientId) && (manualRefreshing || !isCurrent)

  const conflictData = analysis?.conflict_detection || {}
  const comparability = conflictData?.comparability || {}
  const medChanges = Array.isArray(conflictData?.clinical_changes?.medication_changes)
    ? conflictData.clinical_changes.medication_changes
    : []

  const activeDraft = notesState.forPatientId === selectedPatientId ? notesState.draft : ''
  const activeSaved = notesState.forPatientId === selectedPatientId ? notesState.saved : ''

  return (
    <div className="space-y-6">
      <PageHeader
        title="Medication Reconciliation"
        subtitle="Displays explicit cross-report medication status changes returned by the backend conflict analyzer alongside documented extraction limits."
        badge={error ? 'Backend Unavailable' : 'Partial Backend Support • Explicit Status Changes Only'}
        badgeTone={error ? 'attention_needed' : 'review'}
      />

      <PatientSelectorBar onRefresh={handleRetry} refreshing={loading} />

      {/* Explicit Backend Scope & Safety Disclosure */}
      <GlassCard hover={false} className="border-cyan-500/30 bg-cyan-950/15 p-5">
        <div className="flex items-start gap-3 text-xs leading-relaxed text-cyan-100">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
          <div className="space-y-1.5">
            <p className="font-bold text-white">
              Backend Capability Scope & Clinical Disclaimer
            </p>
            <p className="text-slate-300">
              <strong>What the backend checks:</strong> When two comparable reports for a patient
              contain explicit medication status phrasing (e.g., <code>Medication: active</code> vs.{' '}
              <code>Medication: discontinued</code>),{' '}
              <code>GET /patients/{'{id}'}/analysis</code> reports status changes in{' '}
              <code>conflict_detection.clinical_changes.medication_changes</code> for clinician review.
            </p>
            <p className="text-amber-200/90">
              <strong>Current backend limitations:</strong> Structured full medication lists,
              extracted dosages, dosing frequencies, drug-drug interaction alerts, and database-saved
              reconciliation notes are <strong>not implemented</strong> in the FastAPI extractor.
              This view is not a clinically validated medication reconciliation system.
            </p>
          </div>
        </div>
      </GlassCard>

      {!selectedPatientId && !patientsLoading ? (
        <GlassCard hover={false} className="p-8 text-center">
          <p className="text-sm font-semibold text-white">No patient selected</p>
          <p className="mt-1 text-xs text-slate-400">
            Select a patient above to inspect backend-detected medication status changes.
          </p>
        </GlassCard>
      ) : error ? (
        <GlassCard hover={false} className="border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Could not load medication comparison</h2>
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
      ) : loading || !analysis ? (
        <GlassCard hover={false} className="flex items-center justify-center gap-3 p-12 text-sm text-slate-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
          <span>Checking patient reports for explicit medication status changes...</span>
        </GlassCard>
      ) : (
        <>
          {/* Live Medication Status Changes Section */}
          <GlassCard hover={false} className="p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Pill className="h-5 w-5 text-cyan-400" />
                <div>
                  <h2 className="text-base font-bold text-white">
                    Explicit Medication Status Changes (Unverified • Needs Clinician Review)
                  </h2>
                  <p className="text-xs text-slate-400">
                    Comparability status:{' '}
                    {comparability.reason ||
                      (comparability.comparable === false
                        ? 'Cross-report comparison not applicable.'
                        : 'Checked across latest comparable reports.')}
                  </p>
                </div>
              </div>
              <StatusBadge
                label={`${medChanges.length} Status Change(s)`}
                tone={medChanges.length > 0 ? 'review_recommended' : 'info'}
              />
            </div>

            {medChanges.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 p-6 text-xs leading-relaxed text-slate-400">
                <p className="font-semibold text-white">
                  No explicit cross-report medication status changes detected in backend response.
                </p>
                <p className="mt-1">
                  Either the selected patient&apos;s comparable reports do not contain matched{' '}
                  <code>medication: status</code> phrasing, fewer than two comparable reports exist,
                  or structured prescription tables were not present in the source PDFs. Structured
                  dosage/frequency lists are not fabricated.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                      <th className="pb-3 pr-4">Medication</th>
                      <th className="pb-3 pr-4">Previous Status</th>
                      <th className="pb-3 pr-4">Latest Status</th>
                      <th className="pb-3 pr-4">Dosage / Frequency</th>
                      <th className="pb-3 pr-4">Source Reports & Evidence</th>
                      <th className="pb-3">Verification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70">
                    {medChanges.map((item, idx) => (
                      <tr key={`${item.medication}-${idx}`}>
                        <td className="py-3.5 pr-4 font-semibold capitalize text-white">
                          {item.medication}
                        </td>
                        <td className="py-3.5 pr-4 text-slate-300">
                          {item.old_status || 'Unspecified'}
                        </td>
                        <td className="py-3.5 pr-4 text-slate-300">
                          {item.new_status || 'Unspecified'}
                        </td>
                        <td className="py-3.5 pr-4 text-xs text-slate-500">
                          Not structured by backend
                        </td>
                        <td className="py-3.5 pr-4 text-xs text-slate-300">
                          {item.previous_report && (
                            <div>
                              <strong>Prev #{item.previous_report.report_id}</strong> (
                              {item.previous_report.study_date}): &ldquo;
                              {item.previous_report.context}&rdquo;
                            </div>
                          )}
                          {item.latest_report && (
                            <div className="mt-1">
                              <strong>Latest #{item.latest_report.report_id}</strong> (
                              {item.latest_report.study_date}): &ldquo;
                              {item.latest_report.context}&rdquo;
                            </div>
                          )}
                        </td>
                        <td className="py-3.5">
                          <StatusBadge
                            label={item.status || 'REVIEW_REQUIRED'}
                            tone="review_recommended"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>

          {/* Session-Only Clinician Verification Notes */}
          <GlassCard hover={false} className="p-6">
            <div className="mb-3 flex items-center gap-2 text-xs text-amber-300">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              <span>
                CLINIQ AI does not prescribe, verify, or modify medications. Notes below stay in
                temporary React session state only and are not saved to SQLite.
              </span>
            </div>
            <textarea
              rows={3}
              value={activeDraft}
              onChange={(e) =>
                setNotesState((prev) => ({
                  forPatientId: selectedPatientId,
                  draft: e.target.value,
                  saved: prev.forPatientId === selectedPatientId ? prev.saved : '',
                }))
              }
              placeholder={`Enter session-only clinician review notes for ${selectedPatientId}...`}
              className="w-full rounded-xl border border-slate-700 bg-[#080F20] p-3 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() =>
                  setNotesState((prev) => ({
                    forPatientId: selectedPatientId,
                    draft: prev.forPatientId === selectedPatientId ? prev.draft : '',
                    saved: (prev.forPatientId === selectedPatientId ? prev.draft : '').trim(),
                  }))
                }
                className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
              >
                Save Session Note
              </button>
              {activeSaved && (
                <span className="text-xs text-emerald-300">
                  Saved in local session state (not persisted): &ldquo;{activeSaved}&rdquo;
                </span>
              )}
            </div>
          </GlassCard>

          {(conflictData.disclaimer || analysis?.clinical_disclaimer) && (
            <div className="flex items-start gap-2.5 rounded-xl border border-slate-800/80 bg-[#091022]/70 px-4 py-3 text-xs text-slate-400">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
              <span>{conflictData.disclaimer || analysis.clinical_disclaimer}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
