import { motion } from 'motion/react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import clsx from 'clsx'
import { fmtCompact, fmtDate, fmtRate, cap } from '../../data/format'
import type { HeatCell, PlatformId, SeriesPoint } from '../../types/api'
import { PLATFORM_LABEL } from '../../types/api'

export const SERIES_COLORS: Record<PlatformId, string> = { youtube: '#22D3EE', instagram: '#34D399', x: '#A78BFA', linkedin: '#FBBF24' }
const AXIS = { stroke: '#94A3B8', fontSize: 11, tickLine: false, axisLine: false } as const

function TipBox({ active, payload, label, fmt }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string | number; fmt: (n: number, name: string) => string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card-elev px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-medium text-ink">{typeof label === 'string' && label.includes('T') ? fmtDate(label) : label}</div>
      {payload.map((p) => (<div key={p.name} className="flex items-center gap-2 text-muted"><span className="h-2 w-2 rounded-full" style={{ background: p.color }} />{p.name}<span className="num ml-auto pl-3 font-medium text-ink">{fmt(p.value, p.name)}</span></div>))}
    </div>
  )
}

export function TrendChart({ points, metric }: { points: SeriesPoint[]; metric: 'views' | 'engagement_rate' | 'interactions' }) {
  const isRate = metric === 'engagement_rate'
  const data = points.map((p) => ({ date: p.date, value: isRate ? p.engagement_rate : p[metric] }))
  return (
    <ResponsiveContainer width="100%" height={260}>
      {isRate ? (
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#24303D" strokeDasharray="3 6" vertical={false} />
          <XAxis dataKey="date" tickFormatter={fmtDate} {...AXIS} minTickGap={28} />
          <YAxis tickFormatter={(v) => fmtRate(v, 1)} {...AXIS} width={58} />
          <Tooltip content={<TipBox fmt={(n) => fmtRate(n)} />} cursor={{ stroke: '#33465a' }} />
          <Line name="Engagement rate" dataKey="value" stroke="#34D399" strokeWidth={2.2} dot={false} isAnimationActive animationDuration={700} />
        </LineChart>
      ) : (
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#22D3EE" stopOpacity={0.35} /><stop offset="1" stopColor="#22D3EE" stopOpacity={0} /></linearGradient></defs>
          <CartesianGrid stroke="#24303D" strokeDasharray="3 6" vertical={false} />
          <XAxis dataKey="date" tickFormatter={fmtDate} {...AXIS} minTickGap={28} />
          <YAxis tickFormatter={fmtCompact} {...AXIS} width={58} />
          <Tooltip content={<TipBox fmt={(n) => fmtCompact(n)} />} cursor={{ stroke: '#33465a' }} />
          <Area name={cap(metric)} dataKey="value" stroke="#22D3EE" strokeWidth={2.2} fill="url(#g1)" isAnimationActive animationDuration={700} />
        </AreaChart>
      )}
    </ResponsiveContainer>
  )
}

export function FollowersChart({ data }: { data: { date: string; followers: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs><linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#34D399" stopOpacity={0.3} /><stop offset="1" stopColor="#34D399" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid stroke="#24303D" strokeDasharray="3 6" vertical={false} />
        <XAxis dataKey="date" tickFormatter={fmtDate} {...AXIS} minTickGap={36} />
        <YAxis tickFormatter={fmtCompact} {...AXIS} width={58} domain={['dataMin', 'dataMax']} />
        <Tooltip content={<TipBox fmt={(n) => fmtCompact(n)} />} cursor={{ stroke: '#33465a' }} />
        <Area name="Followers" dataKey="followers" stroke="#34D399" strokeWidth={2.2} fill="url(#g2)" animationDuration={700} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function HBar({ rows, format, color = '#22D3EE', height }: { rows: { label: string; value: number; highlight?: boolean }[]; format: (n: number) => string; color?: string; height?: number }) {
  const h = height ?? Math.max(120, rows.length * 38)
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 56, bottom: 0, left: 0 }}>
        <XAxis type="number" hide domain={[0, 'dataMax']} />
        <YAxis type="category" dataKey="label" {...AXIS} width={118} tick={{ fill: '#F4F7FA', fontSize: 12 }} />
        <Tooltip content={<TipBox fmt={(n) => format(n)} />} cursor={{ fill: 'rgba(255,255,255,.03)' }} />
        <Bar dataKey="value" name="Value" radius={[0, 6, 6, 0]} barSize={16} animationDuration={700} label={{ position: 'right', fill: '#94A3B8', fontSize: 11, formatter: (v: unknown) => format(Number(v)) }}>
          {rows.map((r, i) => <Cell key={i} fill={r.highlight === false ? '#33465a' : color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

/** Day x time-block heatmap. Opacity = performance relative to the platform's own range. */
export function Heatmap({ cells, baseline }: { cells: HeatCell[]; baseline: number }) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const blocks = [0, 3, 6, 9, 12, 15, 18, 21]
  const get = (d: string, b: number) => cells.find((c) => c.day === d && c.block === b)
  const scores = cells.map((c) => c.score)
  const lo = Math.min(...scores, baseline), hi = Math.max(...scores, baseline + 1)
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[420px]">
        <div className="grid gap-1" style={{ gridTemplateColumns: '36px repeat(8, 1fr)' }}>
          <div />
          {blocks.map((b) => <div key={b} className="text-center text-[10px] text-muted">{String(b).padStart(2, '0')}h</div>)}
          {days.map((d, di) => (
            <div key={d} className="contents">
              <div className="flex items-center text-[11px] text-muted">{d}</div>
              {blocks.map((b, bi) => {
                const c = get(d, b)
                const t = c ? (c.score - lo) / (hi - lo) : 0
                return (
                  <motion.div key={b} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: (di + bi) * 0.012, duration: 0.2 }}
                    title={c ? `${d} ${String(b).padStart(2, '0')}:00-${String(b + 2).padStart(2, '0')}:59 UTC · score ${c.score.toFixed(0)} · ${c.n} posts` : 'No posts'}
                    className={clsx('h-7 rounded-md', !c && 'border border-dashed border-line')}
                    style={c ? { background: `rgba(34,211,238,${0.08 + t * 0.85})` } : undefined} />
                )
              })}
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-end gap-2 text-[10px] text-muted">lower<span className="h-2 w-24 rounded-full" style={{ background: 'linear-gradient(90deg, rgba(34,211,238,.08), rgba(34,211,238,.93))' }} />higher · UTC · empty = no posts</div>
      </div>
    </div>
  )
}

export function StackedShare({ rows }: { rows: { label: string; likes: number; comments: number; shares: number }[] }) {
  return (
    <div className="space-y-4">
      {rows.map((r) => (
        <div key={r.label}>
          <div className="mb-1.5 flex justify-between text-xs"><span className="font-medium">{r.label}</span><span className="num text-muted">{(r.likes * 100).toFixed(0)}% likes · {(r.comments * 100).toFixed(0)}% comments · {(r.shares * 100).toFixed(0)}% shares</span></div>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-elevated">
            <motion.div initial={{ width: 0 }} animate={{ width: `${r.likes * 100}%` }} transition={{ duration: 0.6 }} className="bg-cyan" />
            <motion.div initial={{ width: 0 }} animate={{ width: `${r.comments * 100}%` }} transition={{ duration: 0.6, delay: 0.05 }} className="bg-mint" />
            <motion.div initial={{ width: 0 }} animate={{ width: `${r.shares * 100}%` }} transition={{ duration: 0.6, delay: 0.1 }} className="bg-[#A78BFA]" />
          </div>
        </div>
      ))}
      <div className="flex gap-4 text-[11px] text-muted"><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-cyan" />Likes</span><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-mint" />Comments</span><span><i className="mr-1.5 inline-block h-2 w-2 rounded-full bg-[#A78BFA]" />Shares / reposts</span></div>
    </div>
  )
}

export function ProfileRadar({ dims }: { dims: Record<string, { score: number }> }) {
  const data = Object.entries(dims).map(([k, v]) => ({ k: cap(k), v: Math.round(v.score) }))
  return (
    <ResponsiveContainer width="100%" height={250}>
      <RadarChart data={data} outerRadius="58%" margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid stroke="#24303D" />
        <PolarAngleAxis dataKey="k" tick={{ fill: '#94A3B8', fontSize: 11 }} />
        <Radar dataKey="v" stroke="#22D3EE" strokeWidth={2} fill="#22D3EE" fillOpacity={0.22} animationDuration={800} />
      </RadarChart>
    </ResponsiveContainer>
  )
}

export function ScoreGauge({ score, label, low, high }: { score: number; label: 'LOW' | 'MEDIUM' | 'HIGH'; low: number; high: number }) {
  const R = 72, C = Math.PI * R
  const color = label === 'HIGH' ? '#34D399' : label === 'MEDIUM' ? '#22D3EE' : '#FB7185'
  return (
    <div className="relative mx-auto w-[200px]">
      <svg viewBox="0 0 180 110" className="w-full">
        <path d="M18 96 A72 72 0 0 1 162 96" fill="none" stroke="#24303D" strokeWidth="12" strokeLinecap="round" />
        <path d="M18 96 A72 72 0 0 1 162 96" fill="none" stroke={color} strokeOpacity=".25" strokeWidth="12" strokeLinecap="round" strokeDasharray={`${C}`} strokeDashoffset={C - (C * high) / 100} />
        <path d="M18 96 A72 72 0 0 1 162 96" fill="none" stroke="#161D26" strokeWidth="14" strokeLinecap="butt" strokeDasharray={`${C}`} strokeDashoffset={C - (C * low) / 100} style={{ display: 'none' }} />
        <motion.path d="M18 96 A72 72 0 0 1 162 96" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round" strokeDasharray={C} initial={{ strokeDashoffset: C }} animate={{ strokeDashoffset: C - (C * score) / 100 }} transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }} />
      </svg>
      <div className="absolute inset-x-0 bottom-0 text-center">
        <div className="num text-4xl font-semibold leading-none">{Math.round(score)}</div>
        <div className="mt-1 text-[11px] font-semibold tracking-widest" style={{ color }}>{label}</div>
      </div>
    </div>
  )
}

export function FactorBars({ items, tone }: { items: { text: string; impact: number }[]; tone: 'pos' | 'neg' }) {
  const max = Math.max(1, ...items.map((i) => Math.abs(i.impact)))
  return (
    <ul className="space-y-3">
      {items.map((f, i) => (
        <li key={f.text}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]"><span>{f.text}</span><span className={clsx('num shrink-0 font-semibold', tone === 'pos' ? 'text-mint' : 'text-rose')}>{f.impact > 0 ? '+' : ''}{f.impact.toFixed(1)}</span></div>
          <div className="h-1.5 rounded-full bg-elevated"><motion.div initial={{ width: 0 }} animate={{ width: `${(Math.abs(f.impact) / max) * 100}%` }} transition={{ duration: 0.5, delay: i * 0.06 }} className={clsx('h-full rounded-full', tone === 'pos' ? 'bg-mint' : 'bg-rose')} /></div>
        </li>
      ))}
    </ul>
  )
}

export function PlatformLegend() {
  return <div className="flex flex-wrap gap-3 text-[11px] text-muted">{(Object.keys(SERIES_COLORS) as PlatformId[]).map((p) => <span key={p}><i className="mr-1.5 inline-block h-2 w-2 rounded-full" style={{ background: SERIES_COLORS[p] }} />{PLATFORM_LABEL[p]}</span>)}</div>
}
