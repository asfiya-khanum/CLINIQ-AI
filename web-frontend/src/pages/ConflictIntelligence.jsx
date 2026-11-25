import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  FileWarning,
  GitCompareArrows,
  Info,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { extractApiError } from '../api/client'
import { comparePatientReports } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import PatientSelectorBar from '../components/PatientSelectorBar'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

export default function ConflictIntelligence() {
  const { selectedPatientId, loading: patientsLoading } = usePatient()
  const [state, setState] = useState({ data: null, error: null, resolvedPatientId: null })
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const requestSeqRef = useRef(0)

  const handleRetry = useCallback(async () => {
    if (!selectedPatientId) return
    const reqId = ++requestSeqRef.current
    setManualRefreshing(true)
    try {
      const data = await comparePatientReports(selectedPatientId)
      if (reqId === requestSeqRef.current) {
        setState({ data, error: null, resolvedPatientId: selectedPatientId })
      }
    } catch (err) {
      if (reqId === requestSeqRef.current) {
        setState({
          data: null,
          error: extractApiError(err, 'Failed to load conflict and comparison intelligence.'),
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

    comparePatientReports(selectedPatientId)
      .then((data) => {
        if (!cancelled && reqId === requestSeqRef.current) {
          setState({ data, error: null, resolvedPatientId: selectedPatientId })
        }
      })
      .catch((err) => {
        if (!cancelled && reqId === requestSeqRef.current) {
          setState({
            data: null,
            error: extractApiError(err, 'Failed to load conflict and comparison intelligence.'),
            resolvedPatientId: selectedPatientId,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedPatientId])

  const isCurrent = selectedPatientId && state.resolvedPatientId === selectedPatientId
  const compareResp = isCurrent ? state.data : null
  const error = isCurrent ? state.error : null
  const loading = Boolean(selectedPatientId) && (manualRefreshing || !isCurrent)

  const conflictData = compareResp?.conflict_detection || {}
  const missingReports = Array.isArray(conflictData?.missing_information?.incomplete_reports)
    ? conflictData.missing_information.incomplete_reports
    : []
  const contradictions = Array.isArray(conflictData?.potential_contradictions)
    ? conflictData.potential_contradictions
    : []
  const medChanges = Array.isArray(conflictData?.clinical_changes?.medication_changes)
    ? conflictData.clinical_changes.medication_changes
    : []
  const labChanges = Array.isArray(conflictData?.clinical_changes?.lab_changes)
    ? conflictData.clinical_changes.lab_changes
    : []

  const changes = compareResp?.changes || {}
  const changeCounts = compareResp?.rule_based_observations?.counts || {}
  const totalFindingChanges =
    (changeCounts.newly_appearing ?? 0) +
    (changeCounts.improving ?? 0) +
    (changeCounts.worsening ?? 0) +
    (changeCounts.unchanged ?? 0)

  const changeBuckets = [
    { title: 'Newly Appearing', items: changes.newly_appearing || [], tone: 'review' },
    { title: 'Improving', items: changes.improving || [], tone: 'normal' },
    { title: 'Worsening', items: changes.worsening || [], tone: 'attention_needed' },
    { title: 'Unchanged', items: changes.unchanged || [], tone: 'info' },
    { title: 'Not Mentioned in Latest', items: changes.not_mentioned_in_latest || [], tone: 'demo' },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Conflict Intelligence"
        subtitle="Separates missing information, comparable same-date contradictions, and longitudinal clinical changes for clinician review."
        badge={error ? 'Backend Unavailable' : 'Live Backend • GET /patients/{id}/compare'}
        badgeTone={error ? 'attention_needed' : 'normal'}
      />

      <PatientSelectorBar onRefresh={handleRetry} refreshing={loading} />

      {!selectedPatientId && !patientsLoading ? (
        <GlassCard hover={false} className="p-8 text-center">
          <p className="text-sm font-semibold text-white">No patient selected</p>
          <p className="mt-1 text-xs text-slate-400">
            Select a patient above to run cross-report comparison and record completeness checks.
          </p>
        </GlassCard>
      ) : error ? (
        <GlassCard hover={false} className="border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Could not load comparison results</h2>
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
      ) : loading || !compareResp ? (
        <GlassCard hover={false} className="flex items-center justify-center gap-3 p-12 text-sm text-slate-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
          <span>Running rule-based comparison and conflict checks...</span>
        </GlassCard>
      ) : (
        <>
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              label="Missing Information"
              value={missingReports.length}
              subtitle="Incomplete report metadata checks"
              icon={FileWarning}
              accent="amber"
            />
            <StatCard
              label="Potential Contradictions"
              value={contradictions.length}
              subtitle="Comparable opposing assertions"
              icon={AlertTriangle}
              accent="rose"
            />
            <StatCard
              label="Clinical Changes"
              value={totalFindingChanges}
              subtitle="Longitudinal rule-based differences"
              icon={GitCompareArrows}
              accent="cyan"
            />
          </div>

          {/* Comparison Context & Study Compatibility Banner */}
          <GlassCard hover={false} className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-bold text-white">Comparison Pair</span>
                  <StatusBadge
                    label={compareResp.comparison_available ? 'Comparison Available' : 'Comparison Skipped'}
                    tone={compareResp.comparison_available ? 'normal' : 'review'}
                  />
                  {conflictData.status && (
                    <StatusBadge
                      label={conflictData.status.replace(/_/g, ' ')}
                      tone={conflictData.status === 'NO_CONTRADICTIONS_DETECTED' ? 'normal' : 'review_recommended'}
                    />
                  )}
                </div>
                <p className="text-xs text-slate-300">
                  {compareResp.comparison_available
                    ? compareResp.rule_based_observations?.summary
                    : compareResp.reason || 'At least two distinct reports are required for comparison.'}
                </p>
                {compareResp.study_compatibility?.note && (
                  <p className="text-xs text-cyan-300/90">
                    Study comparability: {compareResp.study_compatibility.note}
                  </p>
                )}
              </div>
            </div>

            {compareResp.previous_report && compareResp.latest_report && (
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-[#081021]/90 p-3 text-xs">
                  <div className="font-semibold text-slate-400">Previous Report</div>
                  <div className="mt-1 font-bold text-white">
                    #{compareResp.previous_report.report_id} —{' '}
                    {compareResp.previous_report.study_name || compareResp.previous_report.filename}
                  </div>
                  <div className="mt-0.5 text-slate-400">
                    Date:{' '}
                    {compareResp.previous_report.study_date_iso ||
                      compareResp.previous_report.study_date ||
                      'Undated'}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-[#081021]/90 p-3 text-xs">
                  <div className="font-semibold text-slate-400">Latest Report</div>
                  <div className="mt-1 font-bold text-white">
                    #{compareResp.latest_report.report_id} —{' '}
                    {compareResp.latest_report.study_name || compareResp.latest_report.filename}
                  </div>
                  <div className="mt-0.5 text-slate-400">
                    Date:{' '}
                    {compareResp.latest_report.study_date_iso ||
                      compareResp.latest_report.study_date ||
                      'Undated'}
                  </div>
                </div>
              </div>
            )}
          </GlassCard>

          {/* Missing Information & Potential Contradictions */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <GlassCard className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-bold text-white">Missing Information</h2>
                <StatusBadge
                  label={conflictData?.missing_information?.status || 'CHECKED'}
                  tone={missingReports.length > 0 ? 'review' : 'normal'}
                />
              </div>

              {missingReports.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 p-5 text-xs text-slate-400">
                  All checked reports include diagnosis/findings, date, and source metadata.
                </div>
              ) : (
                <div className="space-y-3">
                  {missingReports.map((item) => (
                    <div
                      key={item.report_id}
                      className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4"
                    >
                      <div className="text-sm font-semibold text-white">
                        Report #{item.report_id} — {item.study_name || item.filename}
                      </div>
                      <div className="mt-1 text-xs text-amber-200">
                        Missing fields: {(item.missing_fields || []).join(', ')}
                      </div>
                      <div className="mt-1 text-[11px] text-slate-400">
                        File: {item.filename} • Study date: {item.study_date || 'Undated'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>

            <GlassCard className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-bold text-white">Potential Contradictions</h2>
                <StatusBadge
                  label={contradictions.length > 0 ? 'Needs Human Review' : 'None Detected'}
                  tone={contradictions.length > 0 ? 'attention_needed' : 'normal'}
                />
              </div>

              {contradictions.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 p-5 text-xs text-slate-400">
                  {conflictData?.comparability?.comparable === false
                    ? conflictData.comparability.reason
                    : 'No mutually opposing same-date assertions detected between comparable reports.'}
                </div>
              ) : (
                <div className="space-y-3">
                  {contradictions.map((item, idx) => (
                    <div
                      key={`${item.finding}-${idx}`}
                      className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4"
                    >
                      <div className="text-sm font-semibold text-white">{item.finding}</div>
                      <p className="mt-1 text-xs text-slate-200">{item.message}</p>
                      <div className="mt-2 space-y-1 text-[11px] text-rose-200/90">
                        {item.previous_report && (
                          <div>
                            Report #{item.previous_report.report_id} ({item.previous_report.study_date || 'Undated'}): &ldquo;{item.previous_report.evidence}&rdquo;
                          </div>
                        )}
                        {item.latest_report && (
                          <div>
                            Report #{item.latest_report.report_id} ({item.latest_report.study_date || 'Undated'}): &ldquo;{item.latest_report.evidence}&rdquo;
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          </div>

          {/* Longitudinal Clinical Changes */}
          <GlassCard hover={false} className="p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-bold text-white">Longitudinal Clinical Changes</h2>
              <StatusBadge label="Non-Error Progression" tone="info" />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {changeBuckets.map((bucket) => (
                <div key={bucket.title} className="rounded-xl border border-slate-800 bg-[#091124] p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      {bucket.title}
                    </span>
                    <StatusBadge label={String(bucket.items.length)} tone={bucket.tone} />
                  </div>
                  {bucket.items.length > 0 ? (
                    <ul className="space-y-2.5 text-xs text-slate-300">
                      {bucket.items.map((item, idx) => (
                        <li key={`${item.finding}-${idx}`} className="space-y-1 border-b border-slate-800/70 pb-2 last:border-0 last:pb-0">
                          <div className="flex items-start gap-1.5 font-semibold text-white">
                            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-400" />
                            <span>{item.finding}</span>
                          </div>
                          {(item.evidence_latest || item.evidence_previous || item.note) && (
                            <p className="pl-5 text-[11px] text-slate-400">
                              {item.evidence_latest || item.note || item.evidence_previous}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500">None detected.</p>
                  )}
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Medication & Lab Status Changes (only rendered when returned) */}
          {(medChanges.length > 0 || labChanges.length > 0) && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {medChanges.length > 0 && (
                <GlassCard hover={false} className="p-6">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-base font-bold text-white">Medication Status Changes</h3>
                    <StatusBadge label="Review Required" tone="review_recommended" />
                  </div>
                  <div className="space-y-2.5 text-xs text-slate-300">
                    {medChanges.map((med, idx) => (
                      <div key={`${med.medication}-${idx}`} className="rounded-xl border border-slate-800 bg-[#091124] p-3">
                        <div className="font-semibold text-white">
                          {med.medication}: {med.old_status} → {med.new_status}
                        </div>
                        <p className="mt-1 text-slate-400">{med.message}</p>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}

              {labChanges.length > 0 && (
                <GlassCard hover={false} className="p-6">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-base font-bold text-white">Explicit Numeric Lab Changes</h3>
                    <StatusBadge label="Clinician Review" tone="info" />
                  </div>
                  <div className="space-y-2.5 text-xs text-slate-300">
                    {labChanges.map((lab, idx) => (
                      <div key={`${lab.test_name}-${idx}`} className="rounded-xl border border-slate-800 bg-[#091124] p-3">
                        <div className="font-semibold text-white">
                          {lab.test_name}: {lab.previous_value} {lab.unit} → {lab.latest_value} {lab.unit}
                        </div>
                        <p className="mt-1 text-slate-400">{lab.message}</p>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}
            </div>
          )}

          {/* Disclaimers */}
          {(conflictData.disclaimer || compareResp.clinical_disclaimer) && (
            <div className="flex items-start gap-2.5 rounded-xl border border-slate-800/80 bg-[#091022]/70 px-4 py-3 text-xs text-slate-400">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
              <span>{conflictData.disclaimer || compareResp.clinical_disclaimer}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
