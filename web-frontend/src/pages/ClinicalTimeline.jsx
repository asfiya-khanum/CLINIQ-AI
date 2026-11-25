import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Calendar,
  Clock3,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { extractApiError } from '../api/client'
import { getPatientTimeline } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import PatientSelectorBar from '../components/PatientSelectorBar'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

export default function ClinicalTimeline() {
  const { selectedPatientId, loading: patientsLoading } = usePatient()
  const [state, setState] = useState({ data: null, error: null, resolvedPatientId: null })
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const requestSeqRef = useRef(0)

  const handleRetry = useCallback(async () => {
    if (!selectedPatientId) return
    const reqId = ++requestSeqRef.current
    setManualRefreshing(true)
    try {
      const data = await getPatientTimeline(selectedPatientId)
      if (reqId === requestSeqRef.current) {
        setState({ data, error: null, resolvedPatientId: selectedPatientId })
      }
    } catch (err) {
      if (reqId === requestSeqRef.current) {
        setState({
          data: null,
          error: extractApiError(err, 'Failed to load clinical timeline.'),
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

    getPatientTimeline(selectedPatientId)
      .then((data) => {
        if (!cancelled && reqId === requestSeqRef.current) {
          setState({ data, error: null, resolvedPatientId: selectedPatientId })
        }
      })
      .catch((err) => {
        if (!cancelled && reqId === requestSeqRef.current) {
          setState({
            data: null,
            error: extractApiError(err, 'Failed to load clinical timeline.'),
            resolvedPatientId: selectedPatientId,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedPatientId])

  const isCurrent = selectedPatientId && state.resolvedPatientId === selectedPatientId
  const timelineResp = isCurrent ? state.data : null
  const error = isCurrent ? state.error : null
  const loading = Boolean(selectedPatientId) && (manualRefreshing || !isCurrent)

  const events = Array.isArray(timelineResp?.timeline) ? timelineResp.timeline : []
  const dateRange = timelineResp?.date_range

  return (
    <div className="space-y-6">
      <PageHeader
        title="Clinical Timeline"
        subtitle="Chronological study progression sorted by parsed study date (undated reports placed after dated records)."
        badge={error ? 'Backend Unavailable' : 'Live Backend • GET /patients/{id}/timeline'}
        badgeTone={error ? 'attention_needed' : 'normal'}
      />

      <PatientSelectorBar onRefresh={handleRetry} refreshing={loading} />

      {!selectedPatientId && !patientsLoading ? (
        <GlassCard hover={false} className="p-8 text-center">
          <p className="text-sm font-semibold text-white">No patient selected</p>
          <p className="mt-1 text-xs text-slate-400">
            Select a patient above or register a patient by uploading a medical PDF.
          </p>
        </GlassCard>
      ) : error ? (
        <GlassCard hover={false} className="border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Could not load patient timeline</h2>
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
      ) : loading || !timelineResp ? (
        <GlassCard hover={false} className="flex items-center justify-center gap-3 p-12 text-sm text-slate-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
          <span>Assembling chronological timeline...</span>
        </GlassCard>
      ) : (
        <>
          {/* Timeline Summary Strip */}
          <GlassCard hover={false} className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">
                  {timelineResp.overview_summary || 'Timeline summary unavailable.'}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Total reports: {timelineResp.total_reports ?? events.length} • Dated reports:{' '}
                  {timelineResp.dated_reports ?? 0}
                  {dateRange?.earliest && dateRange?.latest
                    ? ` • Span: ${dateRange.earliest} → ${dateRange.latest}`
                    : ' • Date span unavailable'}
                </p>
              </div>
              <StatusBadge
                label={(timelineResp.overall_severity || 'normal').replace(/_/g, ' ')}
                tone={timelineResp.overall_severity || 'normal'}
              />
            </div>
          </GlassCard>

          {events.length === 0 ? (
            <GlassCard hover={false} className="p-8 text-center text-xs text-slate-400">
              No clinical events recorded on this patient&apos;s timeline yet.
            </GlassCard>
          ) : (
            <GlassCard hover={false} className="p-6">
              <div className="relative space-y-6 before:absolute before:bottom-2 before:left-4 before:top-2 before:w-0.5 before:bg-gradient-to-b before:from-cyan-400 before:to-blue-600/30">
                {events.map((event) => {
                  const dateLabel = event.study_date_iso || event.study_date || 'Undated'
                  const severity = event.severity || 'normal'
                  const flags = Array.isArray(event.abnormal_flags) ? event.abnormal_flags : []

                  return (
                    <div key={`${event.report_id}-${event.sequence}`} className="relative pl-12">
                      <div className="absolute left-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full border border-cyan-400 bg-[#080D1B]">
                        <Clock3 className="h-3 w-3 text-cyan-300" />
                      </div>

                      <div className="rounded-xl border border-slate-800/80 bg-[#091124] p-4 transition hover:border-cyan-500/40">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-cyan-300">
                            <Calendar className="h-3.5 w-3.5" />
                            <span>
                              Step #{event.sequence} • {dateLabel}
                            </span>
                            {!event.study_date_iso && !event.study_date && (
                              <StatusBadge label="Date Missing" tone="review" />
                            )}
                          </div>
                          <StatusBadge label={severity.replace(/_/g, ' ')} tone={severity} />
                        </div>

                        <h3 className="mt-2 text-base font-bold text-white">
                          {event.study_name || event.filename || `Report #${event.report_id}`}
                        </h3>

                        {event.clinical_summary && (
                          <p className="mt-1.5 text-sm text-slate-300">{event.clinical_summary}</p>
                        )}

                        {event.findings && (
                          <p className="mt-2 text-xs leading-relaxed text-slate-400">
                            <strong className="text-slate-300">Findings:</strong> {event.findings}
                          </p>
                        )}

                        {event.impression && (
                          <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
                            <strong className="text-slate-300">Impression:</strong>{' '}
                            {event.impression}
                          </p>
                        )}

                        {flags.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {flags.map((flag, idx) => (
                              <StatusBadge
                                key={`${event.report_id}-${flag.term}-${idx}`}
                                label={flag.term}
                                tone={flag.severity === 'high' ? 'attention_needed' : 'info'}
                              />
                            ))}
                          </div>
                        )}

                        <p className="mt-2.5 font-mono text-xs text-slate-500">
                          Report #{event.report_id} • File: {event.filename || 'unknown.pdf'}
                          {event.uploaded_at ? ` • Uploaded: ${event.uploaded_at.slice(0, 10)}` : ''}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </GlassCard>
          )}
        </>
      )}
    </div>
  )
}
