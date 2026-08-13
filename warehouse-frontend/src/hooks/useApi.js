import { useCallback, useEffect, useState } from 'react'

export function useApi(loader, dependencies = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setData(await loader()) } catch (requestError) { setError(requestError.message) } finally { setLoading(false) }
  }, dependencies)

  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload, setData }
}
