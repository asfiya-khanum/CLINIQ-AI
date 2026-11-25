import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { extractApiError } from '../api/client'
import { getPatients } from '../api/cliniqApi'
import { PatientContext } from './patientContextStore'

export default function PatientProvider({ children }) {
  const [patients, setPatients] = useState([])
  const [totalPatients, setTotalPatients] = useState(0)
  const [selectedPatientId, setSelectedPatientId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const requestSeqRef = useRef(0)

  const applyPatientsData = useCallback((data) => {
    const list = Array.isArray(data?.patients) ? data.patients : []
    setPatients(list)
    setTotalPatients(typeof data?.total_patients === 'number' ? data.total_patients : list.length)
    setSelectedPatientId((prev) => {
      if (prev && list.some((patient) => patient.patient_id === prev)) {
        return prev
      }
      return list[0]?.patient_id ?? null
    })
    return list
  }, [])

  const refreshPatients = useCallback(async () => {
    const reqId = ++requestSeqRef.current
    setLoading(true)
    setError(null)

    try {
      const data = await getPatients()
      if (reqId !== requestSeqRef.current) return null
      return applyPatientsData(data)
    } catch (err) {
      if (reqId !== requestSeqRef.current) return null
      setError(extractApiError(err, 'Unable to load patient list from CLINIQ AI backend.'))
      return null
    } finally {
      if (reqId === requestSeqRef.current) {
        setLoading(false)
      }
    }
  }, [applyPatientsData])

  useEffect(() => {
    const reqId = ++requestSeqRef.current
    getPatients()
      .then((data) => {
        if (reqId === requestSeqRef.current) {
          applyPatientsData(data)
        }
      })
      .catch((err) => {
        if (reqId === requestSeqRef.current) {
          setError(extractApiError(err, 'Unable to load patient list from CLINIQ AI backend.'))
        }
      })
      .finally(() => {
        if (reqId === requestSeqRef.current) {
          setLoading(false)
        }
      })

    return () => {
      requestSeqRef.current += 1
    }
  }, [applyPatientsData])

  const selectPatient = useCallback((patientId) => {
    setSelectedPatientId(patientId || null)
  }, [])

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.patient_id === selectedPatientId) ?? null,
    [patients, selectedPatientId]
  )

  const value = useMemo(
    () => ({
      patients,
      totalPatients,
      selectedPatientId,
      selectedPatient,
      selectPatient,
      loading,
      error,
      refreshPatients,
    }),
    [
      patients,
      totalPatients,
      selectedPatientId,
      selectedPatient,
      selectPatient,
      loading,
      error,
      refreshPatients,
    ]
  )

  return <PatientContext.Provider value={value}>{children}</PatientContext.Provider>
}
