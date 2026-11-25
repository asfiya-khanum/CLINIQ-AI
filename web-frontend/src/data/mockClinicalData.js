// Clearly labeled FICTIONAL DEMO DATA for UI shell preview only.
// No real patient data or backend responses are represented here.

export const FICTIONAL_PATIENT = {
  patient_id: 'FICT-DEMO-001',
  name: 'Alex Morgan (Fictional Demo)',
  age: '46 Years',
  sex: 'M',
  department: 'Internal Medicine (Demo)',
  report_count: 4,
  overall_severity: 'review_recommended',
}

export const FICTIONAL_PATIENTS_LIST = [
  {
    patient_id: 'FICT-DEMO-001',
    name: 'Alex Morgan (Fictional)',
    age: '46 Years',
    sex: 'M',
    report_count: 4,
    latest_study: 'X-RAY CHEST FOLLOW-UP',
    latest_date: '2026-11-24',
    severity: 'review_recommended',
  },
  {
    patient_id: 'FICT-DEMO-002',
    name: 'Clara Lin (Fictional)',
    age: '32 Years',
    sex: 'F',
    report_count: 2,
    latest_study: 'MRI LEFT FOOT PLAIN',
    latest_date: '2026-11-22',
    severity: 'attention_needed',
  },
  {
    patient_id: 'FICT-DEMO-003',
    name: 'Samuel Reid (Fictional)',
    age: '58 Years',
    sex: 'M',
    report_count: 3,
    latest_study: 'X-RAY CHEST',
    latest_date: '2026-11-15',
    severity: 'normal',
  },
]

export const FICTIONAL_TREND_SERIES = [
  { month: 'Jul', reports: 4, flagged: 1, normal: 3 },
  { month: 'Aug', reports: 7, flagged: 2, normal: 5 },
  { month: 'Sep', reports: 6, flagged: 2, normal: 4 },
  { month: 'Oct', reports: 10, flagged: 4, normal: 6 },
  { month: 'Nov', reports: 14, flagged: 5, normal: 9 },
]

export const FICTIONAL_CATEGORY_SERIES = [
  { category: 'Cardiopulmonary', count: 5 },
  { category: 'Musculoskeletal', count: 7 },
  { category: 'Fluid / Swelling', count: 4 },
  { category: 'Critical / Acute', count: 2 },
]

export const FICTIONAL_RECENT_ACTIVITY = [
  {
    id: 'ACT-1',
    patient_id: 'FICT-DEMO-001',
    title: 'Chest X-Ray Follow-up (Fictional)',
    date: '2026-11-24',
    status: 'review_recommended',
    summary: 'Improving lower lobe opacity; no pleural effusion noted.',
  },
  {
    id: 'ACT-2',
    patient_id: 'FICT-DEMO-002',
    title: 'MRI Left Foot Plain (Fictional)',
    date: '2026-11-22',
    status: 'attention_needed',
    summary: 'Patchy marrow edema and mild periarticular fluid requiring review.',
  },
  {
    id: 'ACT-3',
    patient_id: 'FICT-DEMO-003',
    title: 'Chest Radiograph Screening (Fictional)',
    date: '2026-11-15',
    status: 'normal',
    summary: 'Clear lung fields and normal cardiac silhouette.',
  },
]

export const FICTIONAL_DOCUMENTS = [
  {
    id: 101,
    filename: 'demo_chest_followup.pdf',
    patient_id: 'FICT-DEMO-001',
    study_name: 'X-RAY CHEST FOLLOW-UP',
    study_date: '2026-11-24',
    pages: 2,
    extraction_mode: 'PyMuPDF Text',
    severity: 'review_recommended',
  },
  {
    id: 102,
    filename: 'demo_foot_mri_scan.pdf',
    patient_id: 'FICT-DEMO-002',
    study_name: 'MRI LEFT FOOT PLAIN',
    study_date: '2026-11-22',
    pages: 3,
    extraction_mode: 'Tesseract OCR',
    severity: 'attention_needed',
  },
  {
    id: 103,
    filename: 'demo_chest_baseline.pdf',
    patient_id: 'FICT-DEMO-001',
    study_name: 'X-RAY CHEST',
    study_date: '2026-11-02',
    pages: 1,
    extraction_mode: 'PyMuPDF Text',
    severity: 'normal',
  },
]

export const FICTIONAL_TERMINOLOGY = [
  {
    term: 'Bone Marrow Edema',
    category: 'Musculoskeletal / Soft Tissue',
    status: 'Noted in report',
    plainMeaning:
      'Increased fluid signal inside the spongy inner bone tissue, often seen with stress, bruising, or nearby joint irritation.',
    context: 'Patchy marrow edema seen in talus bone (fictional sample).',
  },
  {
    term: 'Pleural Effusion',
    category: 'Cardiopulmonary',
    status: 'Absent / normal in report',
    plainMeaning:
      'Extra fluid in the thin space between the lungs and the chest wall.',
    context: 'No pleural effusion is seen (fictional sample).',
  },
]

export const FICTIONAL_TIMELINE = [
  {
    sequence: 1,
    date: '2026-10-12',
    study: 'Initial Chest X-Ray (Fictional)',
    filename: 'demo_chest_initial.pdf',
    severity: 'review_recommended',
    summary: 'Mild right lower zone opacity identified for follow-up.',
  },
  {
    sequence: 2,
    date: '2026-11-02',
    study: 'Follow-up Chest X-Ray (Fictional)',
    filename: 'demo_chest_baseline.pdf',
    severity: 'normal',
    summary: 'Interval clearing of lower zone opacity; cardiac silhouette normal.',
  },
  {
    sequence: 3,
    date: '2026-11-24',
    study: 'Annual Chest Screening (Fictional)',
    filename: 'demo_chest_followup.pdf',
    severity: 'review_recommended',
    summary: 'Stable cardiac silhouette; minor residual pleural thickening noted.',
  },
]

export const FICTIONAL_MEDICATIONS = [
  {
    medication: 'Metformin (Fictional)',
    dose: '500 mg',
    frequency: 'Twice daily',
    source: 'demo_clinic_note.pdf',
    status: 'Review Required',
  },
  {
    medication: 'Amlodipine (Fictional)',
    dose: '5 mg',
    frequency: 'Once daily',
    source: 'demo_admission.pdf',
    status: 'Consistent',
  },
  {
    medication: 'Atorvastatin (Fictional)',
    dose: '10 mg',
    frequency: 'Once daily',
    source: 'demo_prior_summary.pdf',
    status: 'Discontinued in latest',
  },
]

export const FICTIONAL_CONFLICTS = {
  missingInformation: [
    {
      reportId: 104,
      filename: 'demo_unlabeled_scan.pdf',
      missingFields: ['date'],
      note: 'Fictional example: study date missing from scanned header.',
    },
  ],
  potentialContradictions: [
    {
      finding: 'Pleural Effusion (Fictional Same-Date Conflict)',
      prevSource: 'Report #101 (2026-11-24)',
      latestSource: 'Report #105 (2026-11-24)',
      message: 'Same-date fictional reports contain opposing presence/absence statements requiring clinician verification.',
    },
  ],
  clinicalChanges: {
    newlyAppearing: ['Mild basilar atelectasis (fictional)'],
    improving: ['Right lower zone opacity (fictional)'],
    worsening: [],
    unchanged: ['Normal cardiac silhouette (fictional)'],
  },
}
