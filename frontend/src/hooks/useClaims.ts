import { useEffect, useState } from 'react'
import { getClaims, type ClaimsResponse } from '@/lib/api'

export function useClaims() {
  const [data, setData] = useState<ClaimsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getClaims()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading, error }
}
