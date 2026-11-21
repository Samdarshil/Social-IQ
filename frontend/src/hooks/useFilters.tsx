import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { PlatformId } from '../types/api'

interface FilterState {
  days: number
  platforms: PlatformId[]
  setDays: (d: number) => void
  togglePlatform: (p: PlatformId) => void
  clearPlatforms: () => void
  params: { days: number; platforms?: string }
}
const Ctx = createContext<FilterState | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [days, setDays] = useState(30)
  const [platforms, setPlatforms] = useState<PlatformId[]>([])
  const value = useMemo<FilterState>(() => ({
    days, platforms, setDays,
    togglePlatform: (p) => setPlatforms((cur) => (cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p])),
    clearPlatforms: () => setPlatforms([]),
    params: { days, platforms: platforms.length ? platforms.join(',') : undefined },
  }), [days, platforms])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
export function useFilters(): FilterState {
  const c = useContext(Ctx)
  if (!c) throw new Error('useFilters must be used inside FilterProvider')
  return c
}
