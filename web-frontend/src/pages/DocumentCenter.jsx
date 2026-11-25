import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Info,
  Loader2,
  RefreshCw,
  Trash2,
  UploadCloud,
  XCircle,
} from 'lucide-react'
import { extractApiError } from '../api/client'
import { getPatientReports, uploadPdfs } from '../api/cliniqApi'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'
import PatientSelectorBar from '../components/PatientSelectorBar'
import StatusBadge from '../components/StatusBadge'
import { usePatient } from '../context/patientContextStore'

function isPdfFile(file) {
  if (!file) return false
  const nameOk = file.name.toLowerCase().endsWith('.pdf')
  const typeOk = !file.type || file.type === 'application/pdf'
  return nameOk && typeOk
}

function formatUploadedDate(isoString) {
  if (!isoString) return null
  const parsed = new Date(isoString)
  if (Number.isNaN(parsed.getTime())) return isoString.slice(0, 10)
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  })
}

export default function DocumentCenter() {
  const {
    selectedPatientId,
    selectedPatient,
    selectPatient,
    loading: patientsLoading,
    refreshPatients,
  } = usePatient()

  const fileInputRef = useRef(null)
  const reportSeqRef = useRef(0)
  const isUploadingRef = useRef(false)

  // Upload state
  const [selectedFiles, setSelectedFiles] = useState([])
  const [fileValidationWarning, setFileValidationWarning] = useState(null)
  const [useSelectedAsFallback, setUseSelectedAsFallback] = useState(true)
  const [customFallbackPatientId, setCustomFallbackPatientId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)

  // Report listing state
  const [reportsState, setReportsState] = useState({
    data: null,
    error: null,
    resolvedPatientId: null,
  })
  const [manualRefreshing, setManualRefreshing] = useState(false)

  const fetchReportsForPatient = useCallback(async (patientId) => {
    if (!patientId) return
    const reqId = ++reportSeqRef.current
    setManualRefreshing(true)
    try {
      const data = await getPatientReports(patientId, { order: 'desc' })
      if (reqId === reportSeqRef.current) {
        setReportsState({ data, error: null, resolvedPatientId: patientId })
      }
    } catch (err) {
      if (reqId === reportSeqRef.current) {
        setReportsState({
          data: null,
          error: extractApiError(err, 'Failed to load patient reports from CLINIQ AI backend.'),
          resolvedPatientId: patientId,
        })
      }
    } finally {
      if (reqId === reportSeqRef.current) {
        setManualRefreshing(false)
      }
    }
  }, [])

  useEffect(() => {
    if (!selectedPatientId) return undefined
    let cancelled = false
    const reqId = ++reportSeqRef.current

    getPatientReports(selectedPatientId, { order: 'desc' })
      .then((data) => {
        if (!cancelled && reqId === reportSeqRef.current) {
          setReportsState({ data, error: null, resolvedPatientId: selectedPatientId })
        }
      })
      .catch((err) => {
        if (!cancelled && reqId === reportSeqRef.current) {
          setReportsState({
            data: null,
            error: extractApiError(err, 'Failed to load patient reports from CLINIQ AI backend.'),
            resolvedPatientId: selectedPatientId,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedPatientId])

  const handleFileSelect = (event) => {
    const incoming = Array.from(event.target.files || [])
    if (incoming.length === 0) return

    const validPdfs = []
    const rejectedNames = []

    for (const file of incoming) {
      if (isPdfFile(file)) {
        validPdfs.push(file)
      } else {
        rejectedNames.push(file.name)
      }
    }

    if (rejectedNames.length > 0) {
      setFileValidationWarning(
        `Ignored non-PDF file(s): ${rejectedNames.join(', ')}. Only .pdf files are accepted.`
      )
    } else {
      setFileValidationWarning(null)
    }

    setUploadError(null)
    setUploadResult(null)
    setSelectedFiles(validPdfs)
  }

  const handleRemoveQueuedFile = (indexToRemove) => {
    if (uploading) return
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove))
  }

  const handleClearQueue = () => {
    if (uploading) return
    setSelectedFiles([])
    setFileValidationWarning(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const effectiveFallbackId =
    useSelectedAsFallback && selectedPatientId
      ? selectedPatientId
      : customFallbackPatientId.trim() || null

  const handleUpload = async () => {
    if (isUploadingRef.current || uploading) return
    if (selectedFiles.length === 0) {
      setUploadError('Select at least one PDF file before clicking Upload.')
      return
    }

    const nonPdf = selectedFiles.find((f) => !isPdfFile(f))
    if (nonPdf) {
      setUploadError(`Invalid file "${nonPdf.name}". Only PDF files are allowed.`)
      return
    }

    isUploadingRef.current = true
    setUploading(true)
    setUploadError(null)
    setUploadResult(null)

    try {
      const result = await uploadPdfs(selectedFiles, effectiveFallbackId)
      setUploadResult(result)

      const fileOutcomes = Array.isArray(result?.files) ? result.files : []
      const anySuccess = fileOutcomes.some((item) => item.status === 'success')

      if (anySuccess) {
        setSelectedFiles([])
        setFileValidationWarning(null)
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }

        await refreshPatients()

        const patientIdToReload =
          selectedPatientId ||
          fileOutcomes.find((item) => item.status === 'success')?.patient_id ||
          null

        if (patientIdToReload) {
          if (!selectedPatientId) {
            selectPatient(patientIdToReload)
          }
          await fetchReportsForPatient(patientIdToReload)
        }
      }
    } catch (err) {
      setUploadError(extractApiError(err, 'PDF upload failed. Please verify the backend is running.'))
    } finally {
      isUploadingRef.current = false
      setUploading(false)
    }
  }

  const isCurrent = selectedPatientId && reportsState.resolvedPatientId === selectedPatientId
  const reportsResp = isCurrent ? reportsState.data : null
  const reportsError = isCurrent ? reportsState.error : null
  const reportsLoading = Boolean(selectedPatientId) && (manualRefreshing || !isCurrent)

  const reports = Array.isArray(reportsResp?.reports) ? reportsResp.reports : []
  const uploadOutcomes = Array.isArray(uploadResult?.files) ? uploadResult.files : []
  const successCount = uploadOutcomes.filter((f) => f.status === 'success').length
  const failedCount = uploadOutcomes.filter((f) => f.status !== 'success').length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Document Center"
        subtitle="Upload clinical PDFs for PyMuPDF + Tesseract OCR extraction and inspect stored reports per patient."
        badge={reportsError ? 'Backend Unavailable' : 'Live Backend • POST /upload-pdfs'}
        badgeTone={reportsError ? 'attention_needed' : 'normal'}
      />

      <PatientSelectorBar
        onRefresh={() => fetchReportsForPatient(selectedPatientId)}
        refreshing={reportsLoading}
      />

      {/* Upload Workspace */}
      <GlassCard hover={false} className="p-6">
        <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-cyan-500/25 bg-cyan-500/5 px-4 py-3 text-xs text-cyan-200">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
          <span>
            Each PDF&apos;s internal Patient ID is always preferred. A fallback Patient ID is used
            only when a PDF header contains no Patient ID (and the backend rejects cross-patient name conflicts).
          </span>
        </div>

        {/* Patient Assignment Controls */}
        <div className="mb-5 space-y-3 rounded-xl border border-slate-800 bg-[#080F20]/90 p-4">
          {selectedPatientId ? (
            <label className="flex cursor-pointer items-start gap-2.5 text-xs text-slate-200">
              <input
                type="checkbox"
                checked={useSelectedAsFallback}
                disabled={uploading}
                onChange={(e) => setUseSelectedAsFallback(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-900 accent-cyan-400"
              />
              <span>
                Use active selected patient{' '}
                <strong className="text-white">{selectedPatient?.name || 'Unnamed'}</strong> (
                <code className="text-cyan-300">{selectedPatientId}</code>) as fallback Patient ID
                if an uploaded PDF has no Patient ID.
              </span>
            </label>
          ) : (
            <div className="flex items-start gap-2 text-xs text-amber-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <span>
                No patient is currently selected. Select a patient above to attach undated/ID-less
                PDFs safely, or leave fallback blank to extract Patient IDs directly from each PDF.
              </span>
            </div>
          )}

          {(!selectedPatientId || !useSelectedAsFallback) && (
            <div className="max-w-md pt-1">
              <label
                htmlFor="fallback-patient-id"
                className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-400"
              >
                Optional Manual Fallback Patient ID
              </label>
              <input
                id="fallback-patient-id"
                type="text"
                disabled={uploading}
                value={customFallbackPatientId}
                onChange={(e) => setCustomFallbackPatientId(e.target.value)}
                placeholder="Leave blank to extract Patient ID from each PDF"
                className="w-full rounded-xl border border-slate-700 bg-[#060C1A] px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none disabled:opacity-60"
              />
            </div>
          )}
        </div>

        {/* File Picker */}
        <label
          className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-cyan-500/35 bg-[#081022]/80 px-6 py-9 text-center transition ${
            uploading
              ? 'cursor-not-allowed opacity-60'
              : 'cursor-pointer hover:border-cyan-400/60 hover:bg-[#0B162D]'
          }`}
        >
          <UploadCloud className="mb-3 h-10 w-10 text-cyan-400" />
          <p className="text-sm font-semibold text-white">
            Click to select clinical PDF report(s)
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Accepts `.pdf` files only • Supports multi-file queue • Upload starts only when you click Upload
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            multiple
            disabled={uploading}
            onChange={handleFileSelect}
            className="hidden"
          />
        </label>

        {fileValidationWarning && (
          <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-amber-500/40 bg-amber-950/25 px-4 py-3 text-xs text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
            <span>{fileValidationWarning}</span>
          </div>
        )}

        {/* Selected Queue + Explicit Upload Button */}
        {selectedFiles.length > 0 && (
          <div className="mt-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Queued for Upload ({selectedFiles.length})
              </p>
              <button
                type="button"
                onClick={handleClearQueue}
                disabled={uploading}
                className="text-xs font-semibold text-slate-400 hover:text-rose-300 disabled:opacity-50"
              >
                Clear Queue
              </button>
            </div>

            <div className="space-y-2">
              {selectedFiles.map((file, idx) => (
                <div
                  key={`${file.name}-${file.size}-${idx}`}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-[#091124] px-4 py-2.5 text-sm"
                >
                  <div className="min-w-0 truncate font-medium text-white">{file.name}</div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className="text-xs text-slate-400">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRemoveQueuedFile(idx)}
                      disabled={uploading}
                      aria-label={`Remove ${file.name}`}
                      className="text-slate-500 transition hover:text-rose-400 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <div className="text-xs text-slate-400">
                Fallback Patient ID:{' '}
                <code className="text-cyan-300">
                  {effectiveFallbackId || 'None (extract from PDF only)'}
                </code>
              </div>

              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading || selectedFiles.length === 0}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_0_24px_rgba(6,182,212,0.3)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {uploading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing PDF(s) & OCR...
                  </>
                ) : (
                  <>
                    <UploadCloud className="h-4 w-4" />
                    Upload {selectedFiles.length} PDF{selectedFiles.length > 1 ? 's' : ''}
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Upload Error */}
        {uploadError && (
          <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-rose-500/40 bg-rose-950/25 px-4 py-3 text-xs text-rose-200">
            <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
            <div>
              <p className="font-semibold text-white">Upload request failed</p>
              <p className="mt-0.5">{uploadError}</p>
            </div>
          </div>
        )}

        {/* Upload Per-File Outcomes */}
        {uploadOutcomes.length > 0 && (
          <div className="mt-5 space-y-3 rounded-xl border border-slate-800 bg-[#081021]/90 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                {failedCount === 0 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                )}
                <span>
                  Upload Summary: {successCount} succeeded, {failedCount} failed
                </span>
              </div>
            </div>

            <div className="space-y-2">
              {uploadOutcomes.map((item, idx) => {
                const ok = item.status === 'success'
                const assignedElsewhere =
                  ok && selectedPatientId && item.patient_id !== selectedPatientId

                return (
                  <div
                    key={`${item.filename}-${idx}`}
                    className={`rounded-xl border p-3 text-xs ${
                      ok
                        ? 'border-emerald-500/30 bg-emerald-950/15 text-emerald-100'
                        : 'border-rose-500/30 bg-rose-950/20 text-rose-100'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-white">{item.filename}</span>
                      <StatusBadge
                        label={ok ? `Saved • Report #${item.report_id}` : 'Error'}
                        tone={ok ? 'normal' : 'attention_needed'}
                      />
                    </div>
                    {ok ? (
                      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-slate-300">
                        <span>
                          Patient: <code className="text-cyan-300">{item.patient_id}</code> (
                          {item.patient_id_source}) • Study:{' '}
                          {item.medical_info?.study_name || 'Unspecified'} •{' '}
                          {item.page_count ?? 0} page(s)
                        </span>
                        {assignedElsewhere && (
                          <button
                            type="button"
                            onClick={() => selectPatient(item.patient_id)}
                            className="rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-300 hover:bg-cyan-500/20"
                          >
                            Switch to {item.patient_id}
                          </button>
                        )}
                      </div>
                    ) : (
                      <p className="mt-1 text-rose-200">{item.message || 'File processing failed.'}</p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </GlassCard>

      {/* Stored Reports for Selected Patient */}
      <GlassCard hover={false} className="p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white">Patient Document Repository</h2>
            <p className="text-xs text-slate-400">
              {selectedPatientId
                ? `Reports stored for ${selectedPatient?.name || selectedPatientId} (${selectedPatientId})`
                : 'Select a patient above to inspect stored clinical reports.'}
            </p>
          </div>
          {selectedPatientId && (
            <div className="flex items-center gap-2">
              <StatusBadge label={`${reports.length} Report(s)`} tone="info" />
              <button
                type="button"
                onClick={() => fetchReportsForPatient(selectedPatientId)}
                disabled={reportsLoading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/90 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:text-white disabled:opacity-60"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 text-cyan-400 ${reportsLoading ? 'animate-spin' : ''}`}
                />
                Refresh
              </button>
            </div>
          )}
        </div>

        {!selectedPatientId && !patientsLoading ? (
          <div className="rounded-xl border border-dashed border-amber-500/35 bg-amber-950/15 p-8 text-center">
            <p className="text-sm font-semibold text-white">No patient selected</p>
            <p className="mt-1 text-xs text-amber-200/90">
              Select a patient from the selector above or from Patient Management to view their stored PDFs.
            </p>
          </div>
        ) : reportsError ? (
          <div className="flex flex-col justify-between gap-4 rounded-xl border border-rose-500/40 bg-rose-950/20 p-5 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div>
                <p className="text-sm font-bold text-white">Could not load patient reports</p>
                <p className="mt-1 text-xs text-rose-200/90">{reportsError}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => fetchReportsForPatient(selectedPatientId)}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 px-4 py-2 text-xs font-semibold text-rose-200 transition hover:bg-rose-500/25"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        ) : reportsLoading || !reportsResp ? (
          <div className="flex items-center justify-center gap-3 py-10 text-sm text-slate-300">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
            <span>Loading patient reports...</span>
          </div>
        ) : reports.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400">
            No reports stored for patient <code className="text-cyan-300">{selectedPatientId}</code> yet.
          </div>
        ) : (
          <div className="space-y-3">
            {reports.map((report) => {
              const severity = report.severity || 'normal'
              const studyName = report.medical_info?.study_name || 'Unspecified Study'
              const studyDate =
                report.study_date_iso || report.medical_info?.study_date || 'Undated'
              const flagCount = Array.isArray(report.abnormal_flags)
                ? report.abnormal_flags.length
                : 0
              const uploadedLabel = formatUploadedDate(report.created_at)

              return (
                <div
                  key={report.report_id}
                  className="flex flex-col justify-between gap-3 rounded-xl border border-slate-800/80 bg-[#091124] p-4 sm:flex-row sm:items-center"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <FileText className="mt-0.5 h-5 w-5 shrink-0 text-cyan-400" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-white">
                        <span>Report #{report.report_id}</span>
                        <span className="text-slate-500">—</span>
                        <span className="truncate">{report.filename}</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-400">
                        {studyName} • Study Date: {studyDate} • {report.page_count ?? 0} page(s)
                        {uploadedLabel ? ` • Uploaded: ${uploadedLabel}` : ''}
                      </div>
                      {report.clinical_summary && (
                        <p className="mt-1.5 text-xs text-slate-300">{report.clinical_summary}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <StatusBadge
                      label={`${flagCount} Flag${flagCount === 1 ? '' : 's'}`}
                      tone="info"
                    />
                    <StatusBadge label={severity.replace(/_/g, ' ')} tone={severity} />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
