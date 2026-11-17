import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../services/api'

type Params = Record<string, string | number | undefined | null>

export function useApi<T>(path: string | null, params?: Params) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(path !== null)
  const [tick, setTick] = useState(0)
  const key = JSON.stringify(params ?? {})
  const seq = useRef(0)

  useEffect(() => {
    if (path === null) return
    const mine = ++seq.current
    const ctl = new AbortController()
    setLoading(true)
    api<T>(path, { params: params, signal: ctl.signal })
      .then((d) => { if (mine === seq.current) { setData(d); setError(null) } })
      .catch((e) => { if ((e as Error).name !== 'AbortError' && mine === seq.current) setError(e instanceof ApiError ? e.message : 'Something went wrong') })
      .finally(() => { if (mine === seq.current) setLoading(false) })
    return () => ctl.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}
