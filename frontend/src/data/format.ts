export const fmtInt = (n: number | null | undefined) => (n == null ? 'n/a' : Math.round(n).toLocaleString('en-US'))
export function fmtCompact(n: number | null | undefined): string {
  if (n == null) return 'n/a'
  const a = Math.abs(n)
  if (a >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (a >= 1e4) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString('en-US')
}
export const fmtRate = (r: number | null | undefined, d = 2) => (r == null ? 'n/a' : (r * 100).toFixed(d) + '%')
export const fmtPct = (p: number | null | undefined, d = 1) => (p == null ? 'n/a' : `${p > 0 ? '+' : ''}${p.toFixed(d)}%`)
export const fmtDate = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
export const fmtDateLong = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
export function localInputValue(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}
