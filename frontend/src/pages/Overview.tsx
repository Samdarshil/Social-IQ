import { motion } from 'motion/react'
import { ArrowRight, Eye, HeartHandshake, TrendingUp, Users } from 'lucide-react'
import { Link, useOutletContext } from 'react-router-dom'
import { FilterBar } from '../components/FilterBar'
import { PlatformComparisonBlock, InsightView, TopContentList, ProfileBlock } from '../components/cards/blocks'
import { FollowersChart, TrendChart } from '../components/charts/charts'
import { Card, CountUp, Delta, EmptyState, ErrorState, SectionTitle, Skeleton, Button } from '../components/ui/primitives'
import { useApi } from '../hooks/useApi'
import { useFilters } from '../hooks/useFilters'
import { stagger } from '../animations/variants'
import { fmtCompact, fmtRate } from '../data/format'
import type { LayoutCtx } from '../layouts/AppLayout'
import type { Insights, PlatformComparison, Profile, Summary, Timeseries, TopContent } from '../types/api'

export default function Overview() {
  const { params } = useFilters()
  const ctx = useOutletContext<LayoutCtx>()
  const s = useApi<Summary>('/summary', params)
  const ts = useApi<Timeseries>('/timeseries', { ...params, freq: params.days <= 30 ? 'D' : 'W' })
  const pc = useApi<PlatformComparison>('/platforms/compare', params)
  const top = useApi<TopContent>('/content/top', { ...params, n: 5 })
  const ins = useApi<Insights>('/insights')
  const prof = useApi<Profile>('/profile')

  if (ctx.source?.source.mode === 'empty') return (
    <EmptyState title="No data yet" body="Connect a platform to see your analytics, or explore the full product with clearly labelled demo data." action={<Link to="/app/privacy"><Button>Connect a platform</Button></Link>} />
  )
  if (s.error) return <ErrorState message={s.error} onRetry={s.reload} />
  const d = s.data
  const hero = ins.data?.cards.find((c) => c.kind === 'growth') ?? ins.data?.cards[0]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm text-muted">Overview</p>
          {hero ? <h1 className="mt-1 max-w-2xl text-balance text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">{hero.headline}</h1> : <Skeleton className="mt-2 h-9 w-96 max-w-full" />}
          {hero?.why && <p className="mt-2 max-w-2xl text-sm text-muted">{hero.why}</p>}
        </div>
        <FilterBar />
      </div>

      <motion.div variants={stagger} initial="initial" animate="animate" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { l: 'Total reach', i: Eye, v: d?.current.views, f: fmtCompact, dl: d?.deltas.views_pct },
          { l: 'Engagement rate', i: HeartHandshake, v: d?.current.engagement_rate, f: (n: number) => fmtRate(n), dl: d?.deltas.engagement_rate_pct, raw: true },
          { l: 'Followers', i: Users, v: d?.followers.total, f: fmtCompact, dl: d?.followers.pct, note: d && !d.followers.available ? 'History unavailable' : undefined },
          { l: 'Posts published', i: TrendingUp, v: d?.current.posts, f: (n: number) => String(Math.round(n)), dl: d?.deltas.posts_pct },
        ].map((k) => (
          <Card key={k.l} className="p-5" hover>
            <div className="flex items-center justify-between text-muted"><span className="text-xs font-medium uppercase tracking-wider">{k.l}</span><k.i className="h-4 w-4" /></div>
            <div className="mt-3 text-3xl font-semibold tracking-tight">{d && k.v != null ? <CountUp key={`${k.l}${k.v}`} value={k.raw ? (k.v as number) * 100 : (k.v as number)} format={k.raw ? (n) => n.toFixed(2) + '%' : k.f} /> : d ? 'n/a' : <Skeleton className="h-9 w-28" />}</div>
            <div className="mt-2 flex items-center gap-2">{d ? (k.note ? <span className="text-xs text-muted">{k.note}</span> : <><Delta value={k.dl} /><span className="text-xs text-muted">vs previous {d.window_days}d</span></>) : <Skeleton className="h-4 w-24" />}</div>
          </Card>
        ))}
      </motion.div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="p-5 xl:col-span-2">
          <SectionTitle title="Performance trend" sub={`Reach over the last ${params.days} days${params.platforms ? ' (filtered)' : ''}`} />
          {ts.loading && !ts.data ? <Skeleton className="h-[260px]" /> : ts.error ? <ErrorState message={ts.error} onRetry={ts.reload} /> : <TrendChart points={ts.data?.points ?? []} metric="views" />}
        </Card>
        <Card className="p-5">
          <SectionTitle title="Follower growth" />
          {ts.data?.followers.length ? <FollowersChart data={ts.data.followers} /> : ts.loading ? <Skeleton className="h-[200px]" /> : <p className="text-sm text-muted">Follower history is not available for the connected platforms yet.</p>}
        </Card>
      </div>

      <Card className="p-5">
        <SectionTitle title="Platform comparison" sub="Compare rates and per-follower reach, not raw views" right={<Link to="/app/analytics" className="inline-flex items-center gap-1 text-sm text-cyan hover:underline">Details <ArrowRight className="h-3.5 w-3.5" /></Link>} />
        {pc.loading && !pc.data ? <Skeleton className="h-40" /> : pc.error ? <ErrorState message={pc.error} onRetry={pc.reload} /> : pc.data && <PlatformComparisonBlock data={pc.data} />}
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="p-5 xl:col-span-2">
          <SectionTitle title="Top content" sub="Ranked by performance index within each platform" right={<Link to="/app/content" className="inline-flex items-center gap-1 text-sm text-cyan hover:underline">All content <ArrowRight className="h-3.5 w-3.5" /></Link>} />
          {top.loading && !top.data ? <Skeleton className="h-64" /> : top.data && <TopContentList items={top.data.items} />}
        </Card>
        <Card className="p-5">
          <SectionTitle title="Social DNA" sub="Last 90 days" />
          {prof.data ? <ProfileBlock p={prof.data} /> : <Skeleton className="h-72" />}
        </Card>
      </div>

      {ins.data && ins.data.cards.length > 1 && (
        <div>
          <SectionTitle title="AI insights" sub="Every insight is computed from your data. Open the Assistant to dig deeper." right={<Link to="/app/insights" className="inline-flex items-center gap-1 text-sm text-cyan hover:underline">All insights <ArrowRight className="h-3.5 w-3.5" /></Link>} />
          <motion.div variants={stagger} initial="initial" animate="animate" className="grid gap-4 md:grid-cols-2">{ins.data.cards.slice(0, 4).map((c, i) => <InsightView key={i} c={c} />)}</motion.div>
        </div>
      )}
    </div>
  )
}
