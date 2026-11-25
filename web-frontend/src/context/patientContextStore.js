import { createContext, useContext } from 'react'

export const PatientContext = createContext(null)

export function usePatient() {
  const ctx = useContext(PatientContext)
  if (!ctx) {
    throw new Error('usePatient must be used within a PatientProvider')
  }
  return ctx
}
