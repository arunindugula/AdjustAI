import { useEffect, useState } from 'react'
import { getPolicy, type Policy } from '@/lib/api'

export function usePolicy(policyId: string, incidentDate: string) {
  const [data, setData] = useState<Policy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!policyId || !incidentDate) return
    setLoading(true)
    getPolicy(policyId, incidentDate)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [policyId, incidentDate])

  return { data, loading, error }
}
