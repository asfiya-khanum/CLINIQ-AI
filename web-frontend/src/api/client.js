import axios from 'axios'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const DEFAULT_TIMEOUT_MS = 15000
export const UPLOAD_TIMEOUT_MS = 120000

/**
 * Shared Axios instance configured from VITE_API_BASE_URL.
 * Keeps withCredentials=false to align with FastAPI CORS configuration.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT_MS,
  withCredentials: false,
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  if (config.data instanceof FormData && config.headers) {
    // Allow the browser to generate the multipart/form-data boundary automatically.
    if (typeof config.headers.delete === 'function') {
      config.headers.delete('Content-Type')
    } else {
      delete config.headers['Content-Type']
    }
  }
  return config
})

/**
 * Normalize Axios and FastAPI HTTP errors into a user-safe message string.
 */
export function extractApiError(error, fallbackMessage = 'Unable to reach CLINIQ AI backend.') {
  if (!error) return fallbackMessage

  const detail = error.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const firstMsg = detail[0]?.msg
    if (typeof firstMsg === 'string' && firstMsg.trim()) {
      return firstMsg.trim()
    }
  }

  if (error.code === 'ECONNABORTED') {
    return 'Request timed out while waiting for the backend.'
  }

  if (!error.response && error.message) {
    return `${fallbackMessage} (${error.message})`
  }

  if (error.response?.status) {
    return `Backend returned HTTP ${error.response.status}.`
  }

  return fallbackMessage
}
