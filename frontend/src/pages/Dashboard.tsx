import { useClaims } from '@/hooks/useClaims'
import { ClaimsTable } from '@/components/ClaimsTable'
import { FileText, Clock, CheckCircle, AlertCircle } from 'lucide-react'

export default function Dashboard() {
  const { data, loading, error } = useClaims()

  const claims = data?.claims ?? []

  const kpis = [
    {
      label: 'Total Claims',
      value: data?.total ?? 0,
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Open',
      value: claims.filter((c) => c.claim_status === 'Open').length,
      icon: Clock,
      color: 'text-yellow-600',
      bg: 'bg-yellow-50',
    },
    {
      label: 'In Review',
      value: claims.filter((c) => c.claim_status === 'In Review').length,
      icon: AlertCircle,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
    },
    {
      label: 'Closed',
      value: claims.filter((c) => c.claim_status === 'Closed').length,
      icon: CheckCircle,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Claims Dashboard</h1>
        <p className="text-sm text-gray-500">All open and recent claims for adjudication</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {kpis.map((k) => {
          const Icon = k.icon
          return (
            <div key={k.label} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <div className={`mb-2 inline-flex rounded-md p-2 ${k.bg}`}>
                <Icon className={`h-5 w-5 ${k.color}`} />
              </div>
              <p className="text-2xl font-bold text-gray-900">{k.value}</p>
              <p className="text-xs text-gray-500">{k.label}</p>
            </div>
          )
        })}
      </div>

      {/* Claims table */}
      {loading && <p className="text-sm text-gray-400">Loading claims…</p>}
      {error && <p className="text-sm text-red-500">Error: {error}</p>}
      {!loading && !error && <ClaimsTable claims={claims} />}
    </div>
  )
}
