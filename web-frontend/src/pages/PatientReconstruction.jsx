import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Calendar,
  Cpu,
  FileText,
  Info,
  Layers,
  Loader2,
  RefreshCw,
  Search,
  UserCheck,
} from 'lucide-react'
import { extractApiError } from '../api/client'
import { getPatientAnalysis, getPatientReports } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import PatientSelectorBar from '../components/PatientSelectorBar'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

const PIPELINE_STAGES = [
  { step: '01', title: 'Document Ingestion', desc: 'Multi-PDF upload via PyMuPDF & Tesseract OCR' },
  { step: '02', title: 'Metadata Extraction', desc: 'Patient ID, study, findings & impression' },
  { step: '03', title: 'Timeline Assembly', desc: 'Chronological sorting by study date' },
  { step: '04', title: 'Rule & Conflict Check', desc: 'Missing fields & opposing assertions' },
  { step: '05', title: 'Clinician Review', desc: 'Human verification required' },
]

export default function PatientReconstruction() {
  const { selectedPatientId, loading: patientsLoading } = usePatient()

  const [state, setState] = useState({ data: null, error: null, resolvedPatientId: null })
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const requestSeqRef = useRef(0)

  // On-demand client-side keyword search over fetched patient reports (with pages/raw_text)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchState, setSearchState] = useState({
    forPatientId: null,
    query: '',
    loading: false,
    error: null,
    matches: [],
    searchedCount: 0,
  })
  const searchSeqRef = useRef(0)

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
          error: extractApiError(err, 'Failed to load patient reconstruction data.'),
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
            error: extractApiError(err, 'Failed to load patient reconstruction data.'),
            resolvedPatientId: selectedPatientId,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedPatientId])

  const handleSearch = async (event) => {
    event.preventDefault()
    const trimmed = searchTerm.trim()
    if (!selectedPatientId || !trimmed) return

    const reqId = ++searchSeqRef.current
    setSearchState({
      forPatientId: selectedPatientId,
      query: trimmed,
      loading: true,
      error: null,
      matches: [],
      searchedCount: 0,
    })

    try {
      const resp = await getPatientReports(selectedPatientId, {
        order: 'desc',
        include_pages: true,
      })
      if (reqId !== searchSeqRef.current) return

      const reports = Array.isArray(resp?.reports) ? resp.reports : []
      const needle = trimmed.toLowerCase()
      const matched = []

      for (const report of reports) {
        const fieldsToCheck = [
          ['Study Name', report.medical_info?.study_name],
          ['Findings', report.medical_info?.findings],
          ['Impression', report.medical_info?.impression],
          ['Clinical Summary', report.clinical_summary],
          ['Raw Text', report.raw_text],
        ]

        let hitSection = null
        let snippet = null

        for (const [label, text] of fieldsToCheck) {
          if (!text) continue
          const idx = text.toLowerCase().indexOf(needle)
          if (idx !== -1) {
            hitSection = label
            const start = Math.max(0, idx - 60)
            const end = Math.min(text.length, idx + needle.length + 120)
            snippet = `${start > 0 ? '...' : ''}${text.slice(start, end).trim()}${end < text.length ? '...' : ''}`
            break
          }
        }

        if (hitSection) {
          matched.push({
            report_id: report.report_id,
            filename: report.filename,
            study_name: report.medical_info?.study_name || 'Unspecified Study',
            study_date: report.study_date_iso || report.medical_info?.study_date || 'Undated',
            severity: report.severity || 'normal',
            hitSection,
            snippet,
          })
        }
      }

      setSearchState({
        forPatientId: selectedPatientId,
        query: trimmed,
        loading: false,
        error: null,
        matches: matched,
        searchedCount: reports.length,
      })
    } catch (err) {
      if (reqId !== searchSeqRef.current) return
      setSearchState({
        forPatientId: selectedPatientId,
        query: trimmed,
        loading: false,
        error: extractApiError(err, 'Failed to search stored reports.'),
        matches: [],
        searchedCount: 0,
      })
    }
  }

  const isCurrent = selectedPatientId && state.resolvedPatientId === selectedPatientId
  const analysis = isCurrent ? state.data : null
  const error = isCurrent ? state.error : null
  const loading = Boolean(selectedPatientId) && (manualRefreshing || !isCurrent)

  const patient = analysis?.patient
  const latest = analysis?.latest_report
  const timeline = analysis?.timeline || {}
  const timelineEvents = Array.isArray(timeline?.timeline) ? timeline.timeline : []
  const comparison = analysis?.comparison || {}
  const conflictData = analysis?.conflict_detection || {}
  const incompleteReports = Array.isArray(conflictData?.missing_information?.incomplete_reports)
    ? conflictData.missing_information.incomplete_reports
    : []
  const ruleObs = analysis?.rule_based_observations
  const aiLayer = analysis?.ai_generated_explanations
  const cards = analysis?.dashboard?.cards || {}
  const activeSearch = searchState.forPatientId === selectedPatientId ? searchState : null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patient Reconstruction"
        subtitle="Reconstructed clinical profile, deterministic pipeline outputs, missing-data disclosures, and external AI status from backend records."
        badge={error ? 'Backend Unavailable' : 'Live Backend • GET /patients/{id}/analysis'}
        badgeTone={error ? 'attention_needed' : 'normal'}
      />

      {/* Pipeline Architecture Strip */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {PIPELINE_STAGES.map((stage) => (
          <GlassCard key={stage.step} className="p-4">
            <div className="text-xs font-extrabold tracking-widest text-cyan-400">STEP {stage.step}</div>
            <div className="mt-2 text-sm font-bold text-white">{stage.title}</div>
            <p className="mt-1 text-xs text-slate-400">{stage.desc}</p>
          </GlassCard>
        ))}
      </div>

      <PatientSelectorBar onRefresh={handleRetry} refreshing={loading} />

      {!selectedPatientId && !patientsLoading ? (
        <GlassCard hover={false} className="p-8 text-center">
          <p className="text-sm font-semibold text-white">No patient selected</p>
          <p className="mt-1 text-xs text-slate-400">
            Select a patient above or upload a clinical PDF to view patient reconstruction.
          </p>
        </GlassCard>
      ) : error ? (
        <GlassCard hover={false} className="border-rose-500/40 bg-rose-950/20 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <h2 className="text-sm font-bold text-white">Could not load patient reconstruction</h2>
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
          <span>Reconstructing longitudinal patient view...</span>
        </GlassCard>
      ) : (
        <>
          {/* Section 1: Confirmed Extracted Patient & Latest Report */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <GlassCard hover={false} className="p-6 lg:col-span-5">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <UserCheck className="h-5 w-5 text-cyan-400" />
                  <h2 className="text-base font-bold text-white">Extracted Patient Record</h2>
                </div>
                <StatusBadge label="Extracted / Stored" tone="info" />
              </div>
              <dl className="space-y-2.5 text-xs">
                <div className="flex justify-between gap-3 border-b border-slate-800/70 pb-2">
                  <dt className="text-slate-400">Patient ID</dt>
                  <dd className="font-mono font-semibold text-cyan-300">{patient?.patient_id}</dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-800/70 pb-2">
                  <dt className="text-slate-400">Name</dt>
                  <dd className="font-semibold text-white">{patient?.name || 'Not extracted'}</dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-800/70 pb-2">
                  <dt className="text-slate-400">Age / Sex</dt>
                  <dd className="text-slate-200">
                    {patient?.age || 'Age unavailable'} • {patient?.sex || 'Sex unavailable'}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-800/70 pb-2">
                  <dt className="text-slate-400">Reports on File</dt>
                  <dd className="font-semibold text-white">
                    {cards.total_reports ?? patient?.report_count ?? 0} ({cards.dated_reports ?? 0} dated)
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-400">Date Span</dt>
                  <dd className="text-slate-200">
                    {timeline?.date_range?.earliest && timeline?.date_range?.latest
                      ? `${timeline.date_range.earliest} → ${timeline.date_range.latest}`
                      : 'Unavailable (missing/unparsed study dates)'}
                  </dd>
                </div>
              </dl>
            </GlassCard>

            <GlassCard hover={false} className="p-6 lg:col-span-7">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-cyan-400" />
                  <h2 className="text-base font-bold text-white">Latest Extracted Report Content</h2>
                </div>
                {latest ? (
                  <StatusBadge
                    label={`Report #${latest.report_id} • ${(latest.severity || 'normal').replace(/_/g, ' ')}`}
                    tone={latest.severity || 'normal'}
                  />
                ) : (
                  <StatusBadge label="No Reports" tone="review" />
                )}
              </div>

              {latest ? (
                <div className="space-y-3 text-xs">
                  <div className="text-slate-400">
                    Study: <strong className="text-white">{latest.study_name || 'Unspecified'}</strong> •
                    Date: {latest.study_date_iso || latest.study_date || 'Undated'} • File:{' '}
                    <span className="font-mono text-slate-300">{latest.filename}</span>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-[#091124] p-3">
                    <div className="mb-1 font-semibold text-cyan-300">Extracted Findings</div>
                    <p className="whitespace-pre-line leading-relaxed text-slate-300">
                      {latest.findings || 'No structured findings section was extracted.'}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-[#091124] p-3">
                    <div className="mb-1 font-semibold text-blue-300">Extracted Impression</div>
                    <p className="whitespace-pre-line leading-relaxed text-slate-300">
                      {latest.impression || 'No structured impression section was extracted.'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs text-slate-400">
                  No reports have been stored for this patient yet.
                </div>
              )}
            </GlassCard>
          </div>

          {/* Section 2: Rule-Based Engine vs External AI Layer */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <GlassCard hover={false} className="p-6">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Layers className="h-5 w-5 text-cyan-400" />
                  <h2 className="text-base font-bold text-white">Rule-Based Clinical Engine</h2>
                </div>
                <StatusBadge
                  label={`Deterministic • ai_generated: ${ruleObs?.ai_generated ? 'true' : 'false'}`}
                  tone="normal"
                />
              </div>

              <div className="space-y-3 text-xs leading-relaxed text-slate-300">
                <p>
                  {ruleObs?.overview_summary || 'No rule-based summary available.'}
                </p>
                <div className="rounded-xl border border-slate-800 bg-[#091124] p-3">
                  <div className="font-semibold text-white">Cross-Report Comparison Status</div>
                  <p className="mt-1 text-slate-300">
                    {comparison?.comparison_available
                      ? comparison.rule_based_observations?.summary
                      : comparison?.reason || 'Comparison unavailable (fewer than two reports).'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge
                    label={`Flags Across History: ${ruleObs?.total_abnormal_flags ?? 0}`}
                    tone="info"
                  />
                  <StatusBadge
                    label={`Incomplete Reports: ${incompleteReports.length}`}
                    tone={incompleteReports.length > 0 ? 'review' : 'normal'}
                  />
                  <StatusBadge
                    label={`Contradictions: ${conflictData?.counts?.potential_contradictions ?? 0}`}
                    tone={(conflictData?.counts?.potential_contradictions ?? 0) > 0 ? 'attention_needed' : 'normal'}
                  />
                </div>
              </div>
            </GlassCard>

            <GlassCard hover={false} className="p-6">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Cpu className="h-5 w-5 text-blue-400" />
                  <h2 className="text-base font-bold text-white">External AI / Agentic Layer</h2>
                </div>
                <StatusBadge
                  label={aiLayer?.enabled ? 'Configured' : 'Not Configured (enabled: false)'}
                  tone={aiLayer?.enabled ? 'normal' : 'review'}
                />
              </div>
              <p className="text-xs leading-relaxed text-slate-300">
                {aiLayer?.summary ||
                  aiLayer?.note ||
                  'No external AI model is configured on the backend. Reconstructed views above reflect strictly extracted PDF fields and deterministic Python rules.'}
              </p>

              {incompleteReports.length > 0 && (
                <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                  <div className="font-semibold text-white">Missing Information Disclosure</div>
                  <ul className="mt-1.5 space-y-1">
                    {incompleteReports.map((item) => (
                      <li key={item.report_id}>
                        Report #{item.report_id} ({item.filename}): missing{' '}
                        {(item.missing_fields || []).join(', ')}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </GlassCard>
          </div>

          {/* Section 3: Compact Reconstructed Timeline Sequence */}
          <GlassCard hover={false} className="p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-cyan-400" />
                <h2 className="text-base font-bold text-white">Reconstructed Chronological Sequence</h2>
              </div>
              <StatusBadge label={`${timelineEvents.length} Event(s)`} tone="info" />
            </div>

            {timelineEvents.length === 0 ? (
              <p className="text-xs text-slate-400">No chronological events stored yet.</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {timelineEvents.map((ev) => (
                  <div
                    key={`${ev.report_id}-${ev.sequence}`}
                    className="rounded-xl border border-slate-800 bg-[#091124] p-3.5 text-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-cyan-300">
                        #{ev.sequence} • {ev.study_date_iso || ev.study_date || 'Undated'}
                      </span>
                      <StatusBadge
                        label={(ev.severity || 'normal').replace(/_/g, ' ')}
                        tone={ev.severity || 'normal'}
                      />
                    </div>
                    <div className="mt-1 font-bold text-white">
                      {ev.study_name || ev.filename}
                    </div>
                    <p className="mt-1 text-slate-400">
                      {ev.clinical_summary || 'No clinical summary recorded.'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>

          {/* Section 4: Client-Side Keyword Search Over Stored Reports */}
          <GlassCard hover={false} className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-bold text-white">Patient History Keyword Search</h2>
                <p className="mt-1 text-xs text-slate-400">
                  Searches stored study names, findings, impressions, summaries, and OCR/PDF raw text via{' '}
                  <code>GET /patients/{'{id}'}/reports?include_pages=true</code>.
                </p>
              </div>
              <StatusBadge label="Live Client Filter" tone="info" />
            </div>

            <form onSubmit={handleSearch} className="mt-4 flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Enter keyword present in stored reports (e.g., edema, effusion, chest)..."
                  className="w-full rounded-xl border border-slate-700 bg-[#080F20] py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={!searchTerm.trim() || activeSearch?.loading}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {activeSearch?.loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Search Reports
                  </>
                )}
              </button>
            </form>

            {activeSearch && !activeSearch.loading && (
              <div className="mt-4 space-y-2.5">
                {activeSearch.error ? (
                  <p className="text-xs text-rose-300">{activeSearch.error}</p>
                ) : activeSearch.matches.length === 0 ? (
                  <p className="text-xs text-slate-400">
                    No matches for &ldquo;{activeSearch.query}&rdquo; across{' '}
                    {activeSearch.searchedCount} report(s).
                  </p>
                ) : (
                  <>
                    <p className="text-xs text-slate-400">
                      Found {activeSearch.matches.length} matching report(s) for &ldquo;
                      {activeSearch.query}&rdquo; (searched {activeSearch.searchedCount} report(s)):
                    </p>
                    {activeSearch.matches.map((m) => (
                      <div
                        key={m.report_id}
                        className="rounded-xl border border-slate-800 bg-[#091124] p-3 text-xs"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-semibold text-white">
                            Report #{m.report_id} — {m.study_name} ({m.study_date})
                          </span>
                          <StatusBadge label={`Matched in ${m.hitSection}`} tone="info" />
                        </div>
                        <p className="mt-1.5 text-slate-300">{m.snippet}</p>
                        <p className="mt-1 font-mono text-[11px] text-slate-500">{m.filename}</p>
                      </div>
                    ))}
                  </>
                )}
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
