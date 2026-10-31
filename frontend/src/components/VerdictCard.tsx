import { clsx } from 'clsx'
import { CheckCircle, XCircle, AlertTriangle, UserCheck } from 'lucide-react'
import type { Decision } from '@/lib/api'

const config = {
  Approve:         { icon: CheckCircle,  color: 'text-green-600',  bg: 'bg-green-50 border-green-200' },
  Deny:            { icon: XCircle,      color: 'text-red-600',    bg: 'bg-red-50 border-red-200' },
  'Refer-Fraud':   { icon: AlertTriangle,color: 'text-orange-600', bg: 'bg-orange-50 border-orange-200' },
  'Refer-Adjuster':{ icon: UserCheck,    color: 'text-blue-600',   bg: 'bg-blue-50 border-blue-200' },
} as const

export function VerdictCard({ decision }: { decision: Decision }) {
  const cfg = config[decision.verdict] ?? config['Refer-Adjuster']
  const Icon = cfg.icon

  return (
    <div className={clsx('rounded-lg border p-4', cfg.bg)}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={clsx('h-5 w-5', cfg.color)} />
        <span className={clsx('font-semibold', cfg.color)}>{decision.verdict}</span>
        {decision.model_generated && (
          <span className="ml-auto rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">AI</span>
        )}
      </div>
      <p className="text-sm text-gray-700">{decision.reason}</p>
      <p className="mt-2 text-xs text-gray-400">
        {new Date(decision.confirmed_at).toLocaleString()} · {decision.adjuster_id}
      </p>
    </div>
  )
}
