import { useEffect, useState } from 'react'
import { getClaim, type Claim, type Decision } from '@/lib/api'

export function useClaim(claimId: string) {
  const [data, setData] = useState<(Claim & { decision?: Decision }) | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!claimId) return
    setLoading(true)
    getClaim(claimId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [claimId])

  return { data, loading, error }
}
