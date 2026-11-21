import { useState } from 'react'
import { FilterBar } from '../components/FilterBar'
import { AnomalyList, BestTimesBlock, CategoriesBlock, EngagementChangeBlock, PlatformComparisonBlock } from '../components/cards/blocks'
import { StackedShare, TrendChart } from '../components/charts/charts'
import { Card, ErrorState, SectionTitle, Segmented, Skeleton } from '../components/ui/primitives'
import { useApi } from '../hooks/useApi'
import { useFilters } from '../hooks/useFilters'
import { PLATFORM_LABEL } from '../types/api'
import type { Anomalies, BestTimes, Breakdown, Categories, CrossPlatform, EngagementChange, PlatformComparison, Timeseries } from '../types/api'
import { PlatformTag } from '../components/cards/blocks'
import { fmtRate } from '../data/format'

const Load = ({ r, h = 'h-48', children }: { r: { data: unknown; error: string | null; loading: boolean; reload: () => void }; h?: string; children: React.ReactNode }) =>
  r.error ? <ErrorState message={r.error} onRetry={r.reload} /> : r.data ? <>{children}</> : <Skeleton className={h} />

export default function Analytics() {
  const { params } = useFilters()
  const [metric, setMetric] = useState<'views' | 'engagement_rate' | 'interactions'>('views')
  const ts = useApi<Timeseries>('/timeseries', { ...params, freq: params.days <= 30 ? 'D' : 'W' })
  const pc = useApi<PlatformComparison>('/platforms/compare', params)
  const ec = useApi<EngagementChange>('/engagement-change', { platforms: params.platforms })
  const bt = useApi<BestTimes>('/best-times', params)
  const cat = useApi<Categories>('/categories', params)
  const br = useApi<Breakdown>('/engagement-breakdown', params)
  const an = useApi<Anomalies>('/anomalies', { platforms: params.platforms })
  const cp = useApi<CrossPlatform>('/cross-platform', params)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h1 className="text-2xl font-semibold tracking-tight">Analytics</h1><p className="mt-1 text-sm text-muted">What happened, and why.</p></div>
        <FilterBar />
      </div>

      <Card className="p-5">
        <SectionTitle title="Historical trend" right={<Segmented value={metric} onChange={setMetric} options={[{ value: 'views', label: 'Reach' }, { value: 'interactions', label: 'Interactions' }, { value: 'engagement_rate', label: 'Engagement rate' }]} />} />
        <Load r={ts} h="h-[260px]">{ts.data && <TrendChart points={ts.data.points} metric={metric} />}</Load>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-5"><SectionTitle title="Why engagement changed" sub="Last 28 days vs the 28 before" /><Load r={ec}>{ec.data && <EngagementChangeBlock d={ec.data} />}</Load></Card>
        <Card className="p-5"><SectionTitle title="Engagement breakdown" sub="Share of likes, comments and shares" /><Load r={br}>{br.data && <StackedShare rows={br.data.platforms.map((p) => ({ label: p.label, likes: p.likes_pct, comments: p.comments_pct, shares: p.shares_pct }))} />}</Load></Card>
      </div>

      <Card className="p-5"><SectionTitle title="Platform comparison" /><Load r={pc}>{pc.data && <PlatformComparisonBlock data={pc.data} />}</Load></Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-5"><SectionTitle title="Best publishing times" sub="Per platform, shrunk toward your average to avoid small-sample noise" /><Load r={bt} h="h-64">{bt.data && (Object.keys(bt.data.by_platform).length ? <BestTimesBlock platforms={bt.data.by_platform} /> : <p className="text-sm text-muted">Not enough posts yet.</p>)}</Load></Card>
        <Card className="p-5"><SectionTitle title="Best topics" sub="Performance index by category" /><Load r={cat} h="h-64">{cat.data && <CategoriesBlock rows={cat.data.categories} />}</Load></Card>
      </div>

      <Card className="p-5">
        <SectionTitle title="Cross-platform intelligence" sub="Which topic works best where, relative to each platform's own average" />
        <Load r={cp} h="h-48">{cp.data && (
          <div className="grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
            <div>
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Best platform per topic</h4>
              <ul className="space-y-2.5">{Object.entries(cp.data.best_platform_by_category).map(([c, p]) => (<li key={c} className="flex items-center justify-between text-sm"><span>{c}</span><PlatformTag p={p} /></li>))}</ul>
              {cp.data.focus && <p className="mt-4 rounded-lg border border-cyan/30 bg-cyan/5 p-3 text-sm">Focus: <b>{PLATFORM_LABEL[cp.data.focus]}</b> returns the most interactions per follower.</p>}
            </div>
            <div>
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Likely same-idea posts</h4>
              {cp.data.same_idea.length ? <ul className="space-y-4">{cp.data.same_idea.slice(0, 3).map((g, i) => (
                <li key={i} className="rounded-xl border border-line p-3"><div className="space-y-1.5">{g.posts.map((p) => <div key={p.platform} className="flex min-w-0 items-center gap-2 text-[13px]"><PlatformTag p={p.platform} className="w-24 shrink-0" /><span className="truncate text-muted">{p.title}</span><span className="num ml-auto shrink-0">{fmtRate(p.engagement_rate, 1)}</span></div>)}</div>
                  <p className="mt-2 text-xs text-muted">Best engagement: {PLATFORM_LABEL[g.best_platform]}</p></li>))}</ul> : <p className="text-sm text-muted">No similar posts found across platforms.</p>}
              <p className="mt-3 text-xs text-muted">{cp.data.method_note}</p>
            </div>
          </div>)}</Load>
      </Card>

      <Card className="p-5"><SectionTitle title="Anomaly detection" sub="Unusual views, engagement, comments and follower growth" /><Load r={an}>{an.data && <AnomalyList data={an.data} />}</Load></Card>
    </div>
  )
}
