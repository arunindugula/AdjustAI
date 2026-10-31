import { AlertTriangle } from 'lucide-react'

export function FraudBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
      <AlertTriangle className="h-3 w-3" />
      Refer-Fraud
    </span>
  )
}
