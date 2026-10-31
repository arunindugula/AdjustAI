import { useEffect, useState } from 'react'
import { getDocuments, type DocumentsResponse } from '@/lib/api'

export function useDocuments(claimId: string) {
  const [data, setData] = useState<DocumentsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!claimId) return
    setLoading(true)
    getDocuments(claimId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [claimId])

  return { data, loading, error }
}
