import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT and adjuster identity on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('id_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  const adjusterId = localStorage.getItem('adjuster_id')
  if (adjusterId) config.headers['X-Adjuster-Id'] = adjusterId
  return config
})

export default api

// ── Types ──────────────────────────────────────────────────────────────────

export interface Claim {
  claim_id: string
  policy_id: string
  vehicle_vin: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_acv_usd: number
  incident_date: string
  incident_type: string
  incident_description: string
  damage_description: string
  repair_estimate_usd: number
  injuries_reported: boolean
  police_report_filed: boolean
  assigned_adjuster: string
  prior_claims_12mo: number
  fraud_risk_score: number
  claim_status: string
  created_at: string
}

export interface ClaimsResponse {
  total: number
  claims: Claim[]
}

export interface Policy {
  policy_id: string
  holder_first: string
  holder_last: string
  vehicle_vin: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_acv_usd: number
  coverage_type: string
  collision_coverage: boolean
  comprehensive_coverage: boolean
  collision_deductible_usd: number
  comprehensive_deductible_usd: number
  liability_limit: string
  medpay_limit_usd: number
  policy_status: string
  policy_start: string
  policy_end: string
  liability_only: boolean
  in_force: boolean
}

export interface Document {
  document_id: string
  claim_id: string
  document_type: string
  description: string
  upload_date: string
  page_count: number
  ocr_status: string
  uploaded_by: string
  content_text: string
}

export interface DocumentsResponse {
  claim_id: string
  total: number
  ocr_complete: number
  ocr_pending: number
  documents: Document[]
}

export interface PolicyChunk {
  clause_id: string
  clause_text: string
  source_uri: string
  score: number
}

export interface SearchResponse {
  query: string
  retrieval_method: string
  results: PolicyChunk[]
}

export interface Decision {
  decision_id: string
  claim_id: string
  adjuster_id: string
  verdict: 'Approve' | 'Deny' | 'Refer-Fraud' | 'Refer-Adjuster'
  reason: string
  model_generated: boolean
  confirmed_at: string
}

// ── API calls ──────────────────────────────────────────────────────────────

export const getClaims = () => api.get<ClaimsResponse>('/claims').then((r) => r.data)

export const getClaim = (claimId: string) =>
  api.get<Claim & { decision?: Decision }>(`/claims/${claimId}`).then((r) => r.data)

export const getPolicy = (policyId: string, incidentDate: string) =>
  api.get<Policy>(`/policies/${policyId}?incident_date=${incidentDate}`).then((r) => r.data)

export const getDocuments = (claimId: string) =>
  api.get<DocumentsResponse>(`/documents?claim_id=${claimId}`).then((r) => r.data)

export const searchPolicy = (query: string) =>
  api.get<SearchResponse>(`/documents/search?q=${encodeURIComponent(query)}`).then((r) => r.data)

export const postDecision = (claimId: string, payload: {
  adjuster_id: string
  verdict: string
  reason: string
}) => api.post<Decision>(`/claims/${claimId}/decision`, payload).then((r) => r.data)
