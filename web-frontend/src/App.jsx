import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import PatientProvider from './context/PatientContext'
import ClinicalTimeline from './pages/ClinicalTimeline'
import ConflictIntelligence from './pages/ConflictIntelligence'
import DocumentCenter from './pages/DocumentCenter'
import MedicationReconciliation from './pages/MedicationReconciliation'
import OverviewDashboard from './pages/OverviewDashboard'
import PatientIntelligence from './pages/PatientIntelligence'
import PatientManagement from './pages/PatientManagement'
import PatientReconstruction from './pages/PatientReconstruction'

export default function App() {
  return (
    <BrowserRouter>
      <PatientProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<OverviewDashboard />} />
            <Route path="/patients" element={<PatientManagement />} />
            <Route path="/documents" element={<DocumentCenter />} />
            <Route path="/intelligence" element={<PatientIntelligence />} />
            <Route path="/timeline" element={<ClinicalTimeline />} />
            <Route path="/medications" element={<MedicationReconciliation />} />
            <Route path="/conflicts" element={<ConflictIntelligence />} />
            <Route path="/reconstruction" element={<PatientReconstruction />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </PatientProvider>
    </BrowserRouter>
  )
}
