import { apiClient, UPLOAD_TIMEOUT_MS } from './client'

function encodeId(value, label) {
  if (value === undefined || value === null || String(value).trim() === '') {
    throw new Error(`${label} is required.`)
  }
  return encodeURIComponent(String(value).trim())
}

/**
 * GET /dashboard/overview
 */
export async function getDashboardOverview() {
  const { data } = await apiClient.get('/dashboard/overview')
  return data
}

/**
 * GET /patients
 */
export async function getPatients() {
  const { data } = await apiClient.get('/patients')
  return data
}

/**
 * GET /patients/{patient_id}
 */
export async function getPatient(patientId) {
  const encoded = encodeId(patientId, 'patientId')
  const { data } = await apiClient.get(`/patients/${encoded}`)
  return data
}

/**
 * GET /patients/{patient_id}/reports
 * @param {string} patientId
 * @param {{ order?: 'asc' | 'desc', include_pages?: boolean }} [options]
 */
export async function getPatientReports(patientId, options = {}) {
  const encoded = encodeId(patientId, 'patientId')
  const params = {}

  if (options.order === 'asc' || options.order === 'desc') {
    params.order = options.order
  }
  if (typeof options.include_pages === 'boolean') {
    params.include_pages = options.include_pages
  }

  const { data } = await apiClient.get(`/patients/${encoded}/reports`, { params })
  return data
}

/**
 * GET /patients/{patient_id}/timeline
 */
export async function getPatientTimeline(patientId) {
  const encoded = encodeId(patientId, 'patientId')
  const { data } = await apiClient.get(`/patients/${encoded}/timeline`)
  return data
}

/**
 * GET /patients/{patient_id}/analysis
 */
export async function getPatientAnalysis(patientId) {
  const encoded = encodeId(patientId, 'patientId')
  const { data } = await apiClient.get(`/patients/${encoded}/analysis`)
  return data
}

/**
 * GET /patients/{patient_id}/compare
 * @param {string} patientId
 * @param {{ previous_report_id?: number, latest_report_id?: number }} [options]
 */
export async function comparePatientReports(patientId, options = {}) {
  const encoded = encodeId(patientId, 'patientId')
  const hasPrev = options.previous_report_id !== undefined && options.previous_report_id !== null
  const hasLatest = options.latest_report_id !== undefined && options.latest_report_id !== null

  if (hasPrev !== hasLatest) {
    throw new Error('Provide both previous_report_id and latest_report_id, or omit both.')
  }

  const params = {}
  if (hasPrev && hasLatest) {
    params.previous_report_id = options.previous_report_id
    params.latest_report_id = options.latest_report_id
  }

  const { data } = await apiClient.get(`/patients/${encoded}/compare`, { params })
  return data
}

/**
 * GET /reports/{report_id}/analysis
 */
export async function getReportAnalysis(reportId) {
  const encoded = encodeId(reportId, 'reportId')
  const { data } = await apiClient.get(`/reports/${encoded}/analysis`)
  return data
}

/**
 * POST /upload-pdfs
 * Sends multipart FormData with longer timeout to allow PyMuPDF + Tesseract OCR processing.
 * @param {FileList | File[]} files
 * @param {string | null} [patientId]
 */
export async function uploadPdfs(files, patientId = null) {
  const fileList = Array.from(files || [])
  if (fileList.length === 0) {
    throw new Error('At least one PDF file is required.')
  }

  const formData = new FormData()
  for (const file of fileList) {
    formData.append('files', file)
  }

  if (typeof patientId === 'string' && patientId.trim()) {
    formData.append('patient_id', patientId.trim())
  }

  const { data } = await apiClient.post('/upload-pdfs', formData, {
    timeout: UPLOAD_TIMEOUT_MS,
  })
  return data
}
