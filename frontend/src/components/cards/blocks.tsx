import { motion } from 'motion/react'
import clsx from 'clsx'
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Lightbulb, Sparkles, Target } from 'lucide-react'
import { PlatformMark } from '../ui/PlatformMark'
import { Card, Delta } from '../ui/primitives'
import { Heatmap, HBar, ProfileRadar, ScoreGauge, FactorBars } from '../charts/charts'
import { cap, fmtCompact, fmtDate, fmtInt, fmtPct, fmtRate } from '../../data/format'
import type { Anomalies, AnomalyItem, ContentItem, EngagementChange, InsightCard, PlatformComparison, PlatformId, PlatformRow, Prediction, Profile } from '../../types/api'
import { PLATFORM_LABEL } from '../../types/api'
import { rise, stagger } from '../../animations/variants'

export function PlatformTag({ p, className }: { p: PlatformId; className?: string }) {
  return <span className={clsx('inline-flex items-center gap-1.5', className)}><PlatformMark platform={p} size={16} /><span className="text-[13px]">{PLATFORM_LABEL[p]}</span></span>
}

export function PlatformComparisonBlock({ data, compact }: { data: Pick<PlatformComparison, 'platforms' | 'best' | 'note'> & { focus?: PlatformId | null }; compact?: boolean }) {
  const rows = data.platforms
  if (!rows.length) return <p className="p-6 text-sm text-muted">No platform data in this range.</p>
  const col = (r: PlatformRow) => [
    { k: 'Engagement', v: fmtRate(r.engagement_rate), best: data.best.engagement_rate === r.platform },
    { k: 'Views / follower', v: r.views_per_follower == null ? 'n/a' : r.views_per_follower.toFixed(2), best: data.best.views_per_follower === r.platform },
    { k: 'Follower growth', v: fmtPct(r.follower_growth_pct), best: data.best.follower_growth_pct === r.platform },
  ]
  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2">
        {rows.map((r, i) => (
          <motion.div key={r.platform} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05, duration: 0.3 }} className="rounded-xl border border-line bg-elevated/50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <PlatformTag p={r.platform} />
              {data.focus === r.platform && <span className="inline-flex items-center gap-1 rounded-full bg-cyan/10 px-2 py-0.5 text-[11px] font-medium text-cyan"><Target className="h-3 w-3" />Focus</span>}
            </div>
            <div className="num text-2xl font-semibold">{fmtCompact(r.views)} <span className="text-xs font-normal text-muted">views · {r.posts} posts</span></div>
            <dl className="mt-3 grid grid-cols-3 gap-2">
              {col(r).map((c) => (<div key={c.k}><dt className="text-[10px] uppercase tracking-wider text-muted">{c.k}</dt><dd className={clsx('num mt-0.5 text-[13px] font-medium', c.best && 'text-mint')}>{c.v}{c.best && ' ★'}</dd></div>))}
            </dl>
          </motion.div>
        ))}
      </div>
      {!compact && <p className="mt-3 text-xs leading-relaxed text-muted">★ best across platforms. {data.note}</p>}
    </div>
  )
}

export function TopContentList({ items, limit, onSelect }: { items: ContentItem[]; limit?: number; onSelect?: (c: ContentItem) => void }) {
  return (
    <ul className="divide-y divide-line">
      {items.slice(0, limit).map((c) => (
        <li key={c.content_id}>
          <button onClick={() => onSelect?.(c)} className={clsx('flex w-full items-center gap-3 px-1 py-3 text-left', onSelect && 'rounded-lg transition-colors hover:bg-elevated/60')}>
            <PlatformMark platform={c.platform} size={22} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{c.title || '(untitled)'}</div>
              <div className="mt-0.5 text-xs text-muted">{cap(c.content_type)} · {c.category} · {fmtDate(c.published_at)}</div>
            </div>
            <div className="shrink-0 text-right"><div className="num text-sm font-semibold">{c.perf_index.toFixed(0)}</div><div className="num text-[11px] text-muted">{fmtCompact(c.views)} · {fmtRate(c.engagement_rate, 1)}</div></div>
          </button>
        </li>
      ))}
    </ul>
  )
}

export function InsightView({ c }: { c: InsightCard }) {
  const tone = { positive: 'text-mint', negative: 'text-rose', attention: 'text-amber', neutral: 'text-cyan' }[c.tone]
  const Icon = c.tone === 'negative' ? ArrowDownRight : c.tone === 'positive' ? ArrowUpRight : c.tone === 'attention' ? AlertTriangle : Lightbulb
  return (
    <Card className="p-5" hover>
      <div className="flex gap-3">
        <div className={clsx('mt-0.5 rounded-lg bg-elevated p-2', tone)}><Icon className="h-4 w-4" /></div>
        <div className="min-w-0"><h3 className="text-[15px] font-semibold leading-snug">{c.headline}</h3>{c.why && <p className="mt-1.5 text-sm leading-relaxed text-muted">{c.why}</p>}</div>
      </div>
    </Card>
  )
}

export function EngagementChangeBlock({ d }: { d: EngagementChange }) {
  if (!d.available) return <p className="text-sm text-muted">{d.reason}</p>
  const down = (d.change_pct ?? 0) < 0
  const rows = [...d.by_platform.map((x) => ({ ...x, label: PLATFORM_LABEL[x.key as PlatformId] ?? x.key, kind: 'Platform' })), ...d.by_category.map((x) => ({ ...x, label: x.key, kind: 'Category' }))]
    .sort((a, b) => a.effect - b.effect)
  const picked = [...rows.slice(0, 4), ...rows.slice(-2)].filter((r, i, a) => a.findIndex((x) => x.label === r.label && x.kind === r.kind) === i)
  const max = Math.max(...picked.map((r) => Math.abs(r.effect * 100)), 0.01)
  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <div className="num text-3xl font-semibold">{fmtRate(d.rate_now)}</div>
        <div className={clsx('num text-sm font-medium', down ? 'text-rose' : 'text-mint')}>{fmtPct(d.change_pct)} vs {fmtRate(d.rate_before)} in the {d.days} days before</div>
      </div>
      <p className="mt-1 text-xs text-muted">{d.significant ? 'Statistically significant' : 'Not statistically significant: could be normal variation'}{d.p_value != null && ` (p = ${d.p_value < 0.001 ? '<0.001' : d.p_value.toFixed(3)})`} · {d.posts_now} vs {d.posts_before} posts</p>
      <ul className="mt-4 space-y-2.5">
        {picked.map((r) => {
          const v = r.effect * 100
          return (
            <li key={r.kind + r.label} className="grid grid-cols-[110px_1fr_64px] items-center gap-3 text-[13px]">
              <span className="truncate" title={`${r.kind}: ${r.label}`}><span className="text-muted">{r.kind === 'Platform' ? '' : '# '}</span>{r.label}</span>
              <div className="relative h-2 rounded-full bg-elevated"><div className="absolute left-1/2 top-0 h-full w-px bg-line" />
                <motion.div initial={{ width: 0 }} animate={{ width: `${(Math.abs(v) / max) * 50}%` }} transition={{ duration: 0.5 }} className={clsx('absolute top-0 h-full rounded-full', v < 0 ? 'right-1/2 bg-rose' : 'left-1/2 bg-mint')} /></div>
              <span className={clsx('num text-right font-medium', v < 0 ? 'text-rose' : 'text-mint')}>{v > 0 ? '+' : ''}{v.toFixed(2)} pt</span>
            </li>
          )
        })}
      </ul>
      <p className="mt-4 text-xs leading-relaxed text-muted">Comments are {(d.comment_share_now * 100).toFixed(1)}% of interactions now vs {(d.comment_share_before * 100).toFixed(1)}% before. {d.method}</p>
    </div>
  )
}

export function AnomalyList({ data }: { data: Pick<Anomalies, 'items' | 'method'> }) {
  if (!data.items.length) return <p className="text-sm text-muted">Nothing is outside your normal range.</p>
  const label = (a: AnomalyItem) => ({ views: 'Views', engagement_rate: 'Engagement', comment_rate: 'Comments', follower_growth: 'Follower growth' }[a.metric] ?? a.metric)
  return (
    <div>
      <ul className="divide-y divide-line">
        {data.items.slice(0, 6).map((a, i) => (
          <li key={i} className="flex items-start gap-3 py-3">
            <PlatformMark platform={a.platform} size={20} />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium">{a.message}</div>
              {a.title && <div className="mt-0.5 truncate text-xs text-muted">“{a.title}”</div>}
              <div className="num mt-0.5 text-[11px] text-muted">{label(a)} · {fmtDate(a.published_at)} · {Math.abs(a.z).toFixed(1)}σ {a.direction === 'high' ? 'above' : 'below'} typical</div>
            </div>
            <span className={clsx('rounded-full px-2 py-0.5 text-[11px] font-medium', a.direction === 'high' ? 'bg-mint/10 text-mint' : 'bg-rose/10 text-rose')}>{a.direction === 'high' ? 'High' : 'Low'}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted">{data.method}</p>
    </div>
  )
}

export function ProfileBlock({ p }: { p: Profile }) {
  if (!p.available) return <p className="text-sm text-muted">{p.reason}</p>
  return (
    <div>
      <ProfileRadar dims={p.dimensions} />
      <p className="text-sm text-muted">{p.summary}</p>
      <ul className="mt-4 space-y-2.5">
        {Object.entries(p.dimensions).map(([k, v]) => (
          <li key={k} title={v.formula}>
            <div className="mb-1 flex justify-between text-[13px]"><span className="font-medium">{cap(k)}</span><span className="num text-muted">{v.score.toFixed(0)}/100 · {v.unit}</span></div>
            <div className="h-1.5 rounded-full bg-elevated"><motion.div initial={{ width: 0 }} animate={{ width: `${v.score}%` }} transition={{ duration: 0.6 }} className="h-full rounded-full bg-gradient-to-r from-cyan to-mint" /></div>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted">{p.note}</p>
    </div>
  )
}

export function PredictionBlock({ pred }: { pred: Prediction }) {
  return (
    <div className="grid gap-6 sm:grid-cols-[210px_1fr]">
      <div>
        <ScoreGauge score={pred.score} label={pred.label} low={pred.interval.low} high={pred.interval.high} />
        <p className="num mt-3 text-center text-xs text-muted">{Math.round(pred.interval.level * 100)}% range: {pred.interval.low.toFixed(0)}–{pred.interval.high.toFixed(0)}</p>
        <p className="mt-1 text-center text-[11px] text-muted">Held-out coverage {(pred.interval.empirical_test_coverage * 100).toFixed(0)}%</p>
      </div>
      {pred.explanation && (
        <div className="grid gap-5 sm:grid-cols-2">
          <div><h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-mint">Pushing the score up</h4>{pred.explanation.positive.length ? <FactorBars tone="pos" items={pred.explanation.positive} /> : <p className="text-sm text-muted">No strong positive factors.</p>}</div>
          <div><h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-rose">Holding it back</h4>{pred.explanation.negative.length ? <FactorBars tone="neg" items={pred.explanation.negative} /> : <p className="text-sm text-muted">No strong negative factors.</p>}</div>
          <p className="text-xs text-muted sm:col-span-2">Average prediction is {pred.explanation.base_score.toFixed(0)}. Impacts are score points. {pred.explanation.method}</p>
        </div>
      )}
    </div>
  )
}

export function StrategyBlock({ d }: { d: { recommendations: { kind: string; text: string; platform?: PlatformId }[]; caution: string | null } }) {
  return (
    <div>
      <ul className="space-y-2.5">
        {d.recommendations.map((r, i) => (
          <motion.li key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="flex items-start gap-3 text-sm">
            {r.platform ? <PlatformMark platform={r.platform} size={18} /> : <Sparkles className="mt-0.5 h-[18px] w-[18px] text-cyan" />}<span>{r.text}</span>
          </motion.li>
        ))}
      </ul>
      {d.caution && <p className="mt-4 rounded-lg border border-amber/30 bg-amber/5 p-3 text-xs text-amber">{d.caution}</p>}
    </div>
  )
}

export function BestTimesBlock({ platforms }: { platforms: Record<string, { best_hours: { hour: number }[]; best_days: { day: string }[]; baseline: number; posts: number; heatmap: { day: string; dow: number; block: number; score: number; n: number }[] }> }) {
  const entries = Object.entries(platforms)
  return (
    <motion.div variants={stagger} initial="initial" animate="animate" className="space-y-5">
      {entries.slice(0, 2).map(([p, v]) => (
        <motion.div key={p} variants={rise}>
          <div className="mb-2 flex items-center justify-between"><PlatformTag p={p as PlatformId} /><span className="text-xs text-muted">Best: {v.best_days[0]?.day} ~{String(v.best_hours[0]?.hour ?? 0).padStart(2, '0')}:00 UTC</span></div>
          <Heatmap cells={v.heatmap} baseline={v.baseline} />
        </motion.div>
      ))}
    </motion.div>
  )
}

export function CategoriesBlock({ rows }: { rows: { category: string; perf_index: number }[] }) {
  return <HBar rows={rows.map((r, i) => ({ label: r.category, value: Math.round(r.perf_index), highlight: i < 2 }))} format={(n) => String(Math.round(n))} />
}

export function PeriodBlock({ d }: { d: { days: number; views_pct: number | null; engagement_rate_pct: number | null; current: { views: number; engagement_rate: number | null }; previous: { views: number; engagement_rate: number | null } } }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div><div className="text-xs uppercase tracking-wider text-muted">Views, last {d.days}d</div><div className="num mt-1 text-xl font-semibold">{fmtCompact(d.current.views)}</div><Delta value={d.views_pct} /> <span className="text-xs text-muted">vs {fmtCompact(d.previous.views)}</span></div>
      <div><div className="text-xs uppercase tracking-wider text-muted">Engagement rate</div><div className="num mt-1 text-xl font-semibold">{fmtRate(d.current.engagement_rate)}</div><Delta value={d.engagement_rate_pct} /> <span className="text-xs text-muted">vs {fmtRate(d.previous.engagement_rate)}</span></div>
    </div>
  )
}

export { fmtInt }
