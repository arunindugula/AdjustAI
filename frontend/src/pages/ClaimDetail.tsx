import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useClaim } from '@/hooks/useClaim'
import { usePolicy } from '@/hooks/usePolicy'
import { useDocuments } from '@/hooks/useDocuments'
import { StatusPill } from '@/components/StatusPill'
import { VerdictCard } from '@/components/VerdictCard'
import { AgentPipelinePlaceholder } from '@/components/AgentPipelinePlaceholder'
import { ArrowLeft, FileText, Shield, FolderOpen } from 'lucide-react'

const TABS = ['Claim', 'Policy', 'Documents', 'Agent'] as const
type Tab = typeof TABS[number]

export default function ClaimDetail() {
  const { claimId } = useParams<{ claimId: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('Claim')

  const { data: claim, loading: claimLoading } = useClaim(claimId ?? '')
  const { data: policy, loading: policyLoading } = usePolicy(
    claim?.policy_id ?? '',
    claim?.incident_date ?? '',
  )
  const { data: docs, loading: docsLoading } = useDocuments(claimId ?? '')

  if (claimLoading) return <p className="text-sm text-gray-400">Loading…</p>
  if (!claim) return <p className="text-sm text-red-500">Claim not found.</p>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">{claim.claimant_name}</h1>
          <p className="text-xs font-mono text-gray-400">{claim.claim_id}</p>
        </div>
        <div className="ml-auto">
          <StatusPill status={claim.claim_status} />
        </div>
      </div>

      {/* Existing verdict */}
      {claim.decision && (
        <VerdictCard decision={claim.decision} />
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'Claim' && <FileText className="h-4 w-4" />}
            {t === 'Policy' && <Shield className="h-4 w-4" />}
            {t === 'Documents' && <FolderOpen className="h-4 w-4" />}
            {t}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {tab === 'Claim' && (
        <div className="grid grid-cols-2 gap-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm sm:grid-cols-3">
          {[
            ['Policy ID', claim.policy_id],
            ['Incident Type', claim.incident_type],
            ['Incident Date', claim.incident_date],
            ['Repair Estimate', `$${Number(claim.repair_estimate_usd).toLocaleString()}`],
            ['Vehicle ACV', `$${Number(claim.vehicle_acv_usd).toLocaleString()}`],
            ['Assigned Adjuster', claim.assigned_adjuster],
            ['Police Report', claim.police_report_filed ? 'Yes' : 'No'],
            ['Injuries Reported', claim.injuries_reported ? 'Yes' : 'No'],
            ['Prior Claims (12mo)', String(claim.prior_claims_12mo)],
            ['Fraud Risk Score', String(claim.fraud_risk_score)],
            ['Status', claim.claim_status],
            ['Created', new Date(claim.created_at).toLocaleDateString()],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-gray-400">{label}</p>
              <p className="mt-0.5 font-medium text-gray-900">{value}</p>
            </div>
          ))}
        </div>
      )}

      {tab === 'Policy' && (
        <div>
          {policyLoading && <p className="text-sm text-gray-400">Loading policy…</p>}
          {!policyLoading && !policy && <p className="text-sm text-red-500">Policy not found.</p>}
          {policy && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                {[
                  ['Policyholder', `${policy.holder_first} ${policy.holder_last}`],
                  ['Coverage Type', policy.coverage_type],
                  ['Status', policy.policy_status],
                  ['Policy Start', policy.policy_start],
                  ['Policy End', policy.policy_end],
                  ['Vehicle', `${policy.vehicle_year} ${policy.vehicle_make} ${policy.vehicle_model}`],
                  ['Vehicle ACV', `$${Number(policy.vehicle_acv_usd).toLocaleString()}`],
                  ['Collision Deductible', `$${Number(policy.collision_deductible_usd).toLocaleString()}`],
                  ['Comp. Deductible', `$${Number(policy.comprehensive_deductible_usd).toLocaleString()}`],
                  ['Liability Limit', policy.liability_limit],
                  ['MedPay Limit', `$${Number(policy.medpay_limit_usd).toLocaleString()}`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-xs text-gray-400">{label}</p>
                    <p className="mt-0.5 font-medium text-gray-900">{value}</p>
                  </div>
                ))}
              </div>
              <div className="flex gap-3 pt-2">
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${policy.in_force ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {policy.in_force ? 'In Force' : 'Lapsed'}
                </span>
                {policy.liability_only && (
                  <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-medium text-orange-700">
                    Liability Only
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'Documents' && (
        <div>
          {docsLoading && <p className="text-sm text-gray-400">Loading documents…</p>}
          {!docsLoading && docs && docs.documents.length === 0 && (
            <p className="text-sm text-gray-400">No documents attached to this claim.</p>
          )}
          {docs && docs.documents.length > 0 && (
            <div className="space-y-3">
              {docs.documents.map((d) => (
                <div key={d.document_id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-gray-900">{d.document_type.replace(/_/g, ' ')}</p>
                      <p className="text-sm text-gray-500 mt-0.5">{d.description}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {d.upload_date} · {d.page_count}p · by {d.uploaded_by}
                      </p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                      d.ocr_status === 'Completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>{d.ocr_status}</span>
                  </div>
                  {d.content_text && (
                    <p className="mt-2 text-sm text-gray-600 line-clamp-3">{d.content_text}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'Agent' && <AgentPipelinePlaceholder />}
    </div>
  )
}
