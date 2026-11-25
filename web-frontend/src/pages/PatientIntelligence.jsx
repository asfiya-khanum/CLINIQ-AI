import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  FileSearch,
  Info,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { extractApiError } from '../api/client'
import { getPatientAnalysis } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import PatientSelectorBar from '../components/PatientSelectorBar'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

export default function PatientIntelligence() {
  const { selectedPatientId, loading: patientsLoading } = usePatient()
  const [state, setState] = useState({ data: null, error: null, resolvedPatientId: null })
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const requestSeqRef = useRef(0)

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
          error: extractApiError(err, 'Failed to load patient clinical analysis.'),
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
            error: extractApiError(err, 'Failed to load patient clinical analysis.'),
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

  const patient = analysis?.patient
  const latest = analysis?.latest_report
  const ruleObs = analysis?.rule_based_observations
  const glossary = analysis?.patient_friendly_explanations
  const aiLayer = analysis?.ai_generated_explanations
  const terminologyItems = Array.isArray(glossary?.terminology_explanations)
    ? glossary.terminology_explanations
    : []
  const flaggedItems = Array.isArray(ruleObs?.abnormal_flags) ? ruleObs.abnormal_flags : []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patient Intelligence"
        subtitle="Structured findings, clinical impression, rule-based observations, and plain-language glossary grounded in report context."
        badge={error ? 'Backend Unavailable' : 'Live Backend • GET /patients/{id}/analysis'}
        badgeTone={error ? 'attention_needed' : 'normal'}
      />

      <PatientSelectorBar onRefresh={handleRetry} refreshing={loading} />

      {!selectedPatientId && !patientsLoading ? (
        <GlassCard hover={false} className="p-8 text-center">
          <p className="text-sm font-semibold text-white">No patient selected</p>
          <p className="mt-1 text-xs text-slate-400">
            Select a patient above or upload a clinical PDF to view patient intelligence.
          </p>
        </GlassCard>
      ) : error ? (
        <GlassCard hover={false} className="border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Could not load patient analysis</h2>
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
          <span>Loading patient clinical intelligence...</span>
        </GlassCard>
      ) : (
        <>
          {/* Patient Overview Card */}
          <GlassCard hover={false} className="p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="flex flex-wrap items-center gap-2.5">
                  <h2 className="text-xl font-bold text-white">
                    {patient?.name || 'Unnamed Patient'}
                  </h2>
                  <StatusBadge label="Rule-Based Clinical Engine" tone="info" />
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  ID: <code className="text-cyan-300">{patient?.patient_id}</code> • Age:{' '}
                  {patient?.age || 'Not recorded'} • Sex: {patient?.sex || 'Not recorded'} •{' '}
                  {patient?.report_count ?? 0} report(s) on file
                </p>
              </div>
              <StatusBadge
                label={`Overall: ${(ruleObs?.overall_severity || 'normal').replace(/_/g, ' ')}`}
                tone={ruleObs?.overall_severity || 'normal'}
              />
            </div>

            {ruleObs?.overview_summary && (
              <p className="mt-4 rounded-xl border border-slate-800 bg-[#081021]/90 p-3.5 text-xs leading-relaxed text-slate-300">
                {ruleObs.overview_summary}
              </p>
            )}
          </GlassCard>

          {/* Latest Report Findings & Impression */}
          {latest ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                <span>
                  Latest Report: <strong className="text-white">#{latest.report_id}</strong> —{' '}
                  {latest.study_name || latest.filename} (
                  {latest.study_date_iso || latest.study_date || 'Undated'})
                </span>
                <StatusBadge
                  label={(latest.severity || 'normal').replace(/_/g, ' ')}
                  tone={latest.severity || 'normal'}
                />
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <GlassCard className="p-5">
                  <div className="mb-3 flex items-center gap-2 text-sm font-bold text-cyan-300">
                    <FileSearch className="h-4 w-4" />
                    Extracted Findings
                  </div>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">
                    {latest.findings || 'No structured findings section extracted for this report.'}
                  </p>
                </GlassCard>

                <GlassCard className="p-5">
                  <div className="mb-3 flex items-center gap-2 text-sm font-bold text-blue-300">
                    <CheckCircle2 className="h-4 w-4" />
                    Extracted Impression
                  </div>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">
                    {latest.impression || 'No structured impression section extracted for this report.'}
                  </p>
                </GlassCard>
              </div>
            </div>
          ) : (
            <GlassCard hover={false} className="p-6 text-center text-xs text-slate-400">
              No medical reports are uploaded for this patient yet.
            </GlassCard>
          )}

          {/* Rule-Based Observations vs External AI Separation */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <GlassCard hover={false} className="p-6">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <BrainCircuit className="h-5 w-5 text-cyan-400" />
                  <h3 className="text-base font-bold text-white">Rule-Based Observations</h3>
                </div>
                <StatusBadge
                  label={`AI Generated: ${ruleObs?.ai_generated ? 'Yes' : 'False (Deterministic)'}`}
                  tone="info"
                />
              </div>

              <p className="mb-4 text-xs text-slate-400">
                Total abnormal flags detected across history:{' '}
                <strong className="text-white">{ruleObs?.total_abnormal_flags ?? 0}</strong>
              </p>

              {flaggedItems.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 p-4 text-xs text-slate-400">
                  No abnormal clinical keywords were flagged by deterministic rules.
                </div>
              ) : (
                <div className="max-h-72 space-y-2.5 overflow-y-auto pr-1">
                  {flaggedItems.map((flag, idx) => (
                    <div
                      key={`${flag.report_id}-${flag.term}-${idx}`}
                      className="rounded-xl border border-slate-800 bg-[#091124] p-3.5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-white">{flag.term}</span>
                        <div className="flex items-center gap-2">
                          <StatusBadge label={flag.category || 'Clinical'} tone="info" />
                          <StatusBadge
                            label={flag.severity || 'moderate'}
                            tone={flag.severity === 'high' ? 'attention_needed' : 'review_recommended'}
                          />
                        </div>
                      </div>
                      <p className="mt-1 text-[11px] text-slate-500">
                        Report #{flag.report_id} ({flag.study_name || 'Study'} •{' '}
                        {flag.study_date || 'Undated'})
                      </p>
                      {flag.context && (
                        <p className="mt-1.5 text-xs text-slate-300">&ldquo;{flag.context}&rdquo;</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>

            <GlassCard hover={false} className="p-6">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Cpu className="h-5 w-5 text-blue-400" />
                  <h3 className="text-base font-bold text-white">AI-Generated Explanations Layer</h3>
                </div>
                <StatusBadge
                  label={aiLayer?.enabled ? 'External AI Enabled' : 'External AI: Not Configured'}
                  tone={aiLayer?.enabled ? 'normal' : 'review'}
                />
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#091124] p-4 text-xs leading-relaxed text-slate-300">
                <p>
                  <strong>Status:</strong>{' '}
                  {aiLayer?.enabled ? 'Enabled' : 'Disabled (`enabled: false`)'}
                </p>
                {aiLayer?.summary ? (
                  <p className="mt-2 text-slate-200">{aiLayer.summary}</p>
                ) : (
                  <p className="mt-2 text-slate-400">
                    {aiLayer?.note ||
                      'No external AI model is configured; all observations and terminology explanations are generated deterministically.'}
                  </p>
                )}
              </div>
            </GlassCard>
          </div>

          {/* Patient-Friendly Terminology Explanations */}
          <GlassCard hover={false} className="p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-cyan-400" />
                <div>
                  <h3 className="text-base font-bold text-white">
                    Patient-Friendly Terminology Explanations
                  </h3>
                  <p className="text-xs text-slate-400">
                    {glossary?.plain_language_summary ||
                      'Rule-based glossary definitions preserving original clinical meaning.'}
                  </p>
                </div>
              </div>
              <StatusBadge
                label={`Source: ${glossary?.source || 'rule_based_glossary'} (${glossary?.terminology_count ?? 0})`}
                tone="info"
              />
            </div>

            {terminologyItems.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 p-5 text-center text-xs text-slate-400">
                No glossary terms matched the latest report findings or impression.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {terminologyItems.map((item) => {
                  const isNegated = item.status_in_report === 'negated_or_normal'
                  return (
                    <div
                      key={`${item.term}-${item.matched_phrase}`}
                      className="rounded-xl border border-slate-800 bg-[#091124] p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-bold text-white">{item.term}</span>
                        <StatusBadge
                          label={isNegated ? 'Absent / Normal in report' : 'Noted in report'}
                          tone={isNegated ? 'normal' : 'info'}
                        />
                      </div>
                      <p className="mt-1 text-[11px] font-medium text-cyan-300/80">
                        {item.category}
                      </p>
                      <p className="mt-2 text-xs leading-relaxed text-slate-300">
                        {item.plain_meaning}
                      </p>
                      {item.context_note && (
                        <p className="mt-2 text-[11px] text-slate-400">{item.context_note}</p>
                      )}
                      {item.source_context && (
                        <p className="mt-1.5 text-[11px] text-slate-500">
                          Source ({item.source || 'report'}): &ldquo;{item.source_context}&rdquo;
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </GlassCard>

          {analysis?.clinical_disclaimer && (
            <div className="flex items-start gap-2.5 rounded-xl border border-slate-800/80 bg-[#091022]/70 px-4 py-3 text-xs text-slate-400">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
              <span>{analysis.clinical_disclaimer}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
