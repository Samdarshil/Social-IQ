import { motion } from 'motion/react'
import clsx from 'clsx'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { Card, ErrorState, SectionTitle, Skeleton, Stat } from '../components/ui/primitives'
import { HBar } from '../components/charts/charts'
import { useApi } from '../hooks/useApi'
import { stagger, rise } from '../animations/variants'
import { fmtCompact, fmtInt, fmtRate } from '../data/format'
import type { TrendCluster, TrendCountry, TrendResult } from '../types/api'

const TONE = ['#94A3B8', '#22D3EE', '#34D399']
const toneOf = (i: number, k: number) => (k === 3 ? TONE[i] : TONE[Math.min(2, Math.round((i / (k - 1)) * 2))])

function CorrMatrix({ labels, m }: { labels: string[]; m: number[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[360px] border-separate border-spacing-1 text-center text-xs">
        <thead><tr><th />{labels.map((l) => <th key={l} className="px-1 pb-1 font-medium text-muted">{l}</th>)}</tr></thead>
        <tbody>{m.map((row, i) => (
          <tr key={i}><th className="pr-2 text-right font-medium text-muted">{labels[i]}</th>
            {row.map((v, j) => (
              <td key={j} className="num rounded-lg py-3 font-medium" style={{ background: i === j ? '#161D26' : `rgba(34,211,238,${Math.max(0.06, Math.abs(v) * 0.75)})`, color: Math.abs(v) > 0.55 && i !== j ? '#080B10' : '#F4F7FA' }}
                title={`Spearman ρ = ${v}`}>{i === j ? '1' : v.toFixed(2)}</td>))}
          </tr>))}</tbody>
      </table>
    </div>
  )
}

function ClusterCard({ c, k }: { c: TrendCluster; k: number }) {
  const m = c.medians
  return (
    <motion.div variants={rise} className="min-w-0"><Card className="h-full p-5" standalone>
      <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: toneOf(c.id, k) }} /><h3 className="text-base font-semibold">{c.label}</h3></div>
      <p className="mt-1 text-sm text-muted">{c.descriptor}</p>
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <Stat label="Videos">{fmtInt(c.size)}<span className="ml-1.5 text-sm font-normal text-muted">{(c.share * 100).toFixed(0)}%</span></Stat>
        <Stat label="Median views">{fmtCompact(m.views)}</Stat>
        <Stat label="Median likes">{fmtCompact(m.likes)}</Stat>
        <Stat label="Median comments">{fmtCompact(m.comments)}</Stat>
        <Stat label="Engagement rate">{fmtRate(m.engagement_rate, 2)}</Stat>
        <Stat label="Dislike share">{c.traits.dislike_share == null ? 'n/a' : fmtRate(c.traits.dislike_share, 1)}</Stat>
      </div>
      <div className="mt-4 border-t border-line pt-3 text-xs text-muted">
        <div className="mb-1.5 font-medium uppercase tracking-wider">Over-represented categories</div>
        <ul className="space-y-1">{c.top_categories.slice(0, 4).map((t) => (
          <li key={t.name} className="flex justify-between gap-2"><span className="text-ink">{t.name}</span><span className="num">{(t.share * 100).toFixed(0)}% of group · {t.lift}x</span></li>))}</ul>
        <div className="mt-3 grid grid-cols-3 gap-2 text-center">
          <div><div className="num text-sm font-medium text-ink">{c.traits.days_to_trend ?? 'n/a'}</div>days to trend</div>
          <div><div className="num text-sm font-medium text-ink">{c.traits.title_length ?? 'n/a'}</div>title chars</div>
          <div><div className="num text-sm font-medium text-ink">{c.traits.tag_count ?? 'n/a'}</div>tags</div>
        </div>
        {c.example[0] && <p className="mt-3 truncate" title={c.example[0].title}>Typical: “{c.example[0].title}” <span className="text-muted">({c.example[0].channel})</span></p>}
      </div>
    </Card></motion.div>
  )
}

export default function Clusters() {
  const [cc, setCc] = useState('US')
  const countries = useApi<{ items: TrendCountry[] }>('/research/trending/countries')
  const r = useApi<TrendResult>(`/research/trending/${cc}`)
  const d = r.data
  const k = d?.model.k ?? 3
  const cats = d ? d.category.rows.filter((x) => x.n >= d.category.min_n_for_test) : []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-3"><h1 className="text-2xl font-semibold tracking-tight">Engagement clusters</h1><span className="rounded-full border border-mint/40 bg-mint/10 px-2 py-0.5 text-[10px] font-semibold text-mint">REAL DATA · KAGGLE</span></div>
          <p className="mt-1 max-w-3xl text-sm text-muted">Machine-learning grouping of YouTube trending videos by views, likes, comments and engagement rate. Dataset: Kaggle “YouTube Trending Video Dataset” (historical, not live).</p>
        </div>
        <label className="text-sm text-muted">Country
          <select value={cc} onChange={(e) => setCc(e.target.value)} className="ml-2 rounded-lg border border-line bg-graphite px-3 py-1.5 text-ink" aria-label="Country">
            {(countries.data?.items ?? [{ country: 'US', name: 'United States' }]).map((c) => <option key={c.country} value={c.country}>{c.name}</option>)}
          </select>
        </label>
      </div>
      <div className="rounded-xl border border-amber/30 bg-amber/5 px-4 py-3 text-sm text-amber" role="note">
        Descriptive analysis of past data. Clusters describe patterns in this dataset; they are not predictions of future video popularity. Every video here already trended.
      </div>

      {r.error ? <ErrorState message={r.error} onRetry={r.reload} /> : !d ? <div className="space-y-4"><Skeleton className="h-28" /><Skeleton className="h-72" /></div> : (
        <>
          <Card className="p-5"><div className="grid grid-cols-2 gap-5 md:grid-cols-4">
            <Stat label="Videos analysed" sub={<span className="text-xs text-muted">{fmtInt(d.dataset.rows_raw)} rows, one per unique video</span>}>{fmtInt(d.dataset.videos_used)}</Stat>
            <Stat label="Silhouette (k=3)" sub={<span className="text-xs text-muted">{d.model.silhouette >= 0.5 ? 'clear' : d.model.silhouette >= 0.25 ? 'weak to moderate' : 'none'} separation</span>}>{d.model.silhouette.toFixed(2)}</Stat>
            <Stat label="Stability (ARI)" sub={<span className="text-xs text-muted">refit on 80% subsamples, min {d.model.stability_ari_min.toFixed(2)}</span>}>{d.model.stability_ari_mean.toFixed(2)}</Stat>
            <Stat label="Trending window" sub={<span className="text-xs text-muted">{d.source.kind === 'raw_csv' ? 'computed live from CSV' : 'pre-computed snapshot'}</span>}><span className="text-lg">{d.dataset.trending_window.first?.slice(0, 7)} to {d.dataset.trending_window.last?.slice(0, 7)}</span></Stat>
          </div></Card>

          <Card className="p-5">
            <SectionTitle title="How does engagement vary across categories?" sub={`Median engagement rate = (likes + comments) / views. Categories with at least ${d.category.min_n_for_test} videos. Overall median ${fmtRate(d.category.overall_median_engagement_rate, 2)}.`} />
            <HBar rows={cats.map((x) => ({ label: x.name, value: x.median_engagement_rate, highlight: x.median_engagement_rate >= d.category.overall_median_engagement_rate }))} format={(n) => fmtRate(n, 1)} height={Math.max(160, cats.length * 32)} />
            {d.category.kruskal && <p className="mt-3 text-xs text-muted">Kruskal-Wallis across {d.category.kruskal.categories} categories: H = {d.category.kruskal.h}, p {d.category.kruskal.p < 0.001 ? '< 0.001' : `= ${d.category.kruskal.p.toFixed(3)}`}, effect size ε² = {d.category.kruskal.epsilon_sq}. Highlighted bars are at or above the overall median.</p>}
          </Card>

          <div className="grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
            <Card className="p-5">
              <SectionTitle title="Relationships between views, likes and comments" sub="Spearman rank correlation (1 = move together)" />
              <CorrMatrix labels={d.correlations.labels} m={d.correlations.spearman} />
              <p className="mt-3 text-xs text-muted">{d.takeaways[0]}</p>
            </Card>
            <Card className="p-5">
              <SectionTitle title="Can videos be grouped into distinct patterns?" sub="Silhouette score by number of clusters (higher = better separated)" />
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={Object.entries(d.model.silhouette_by_k).map(([kk, v]) => ({ k: `k=${kk}`, v, chosen: Number(kk) === d.model.k }))} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#24303D" strokeDasharray="3 6" vertical={false} />
                  <XAxis dataKey="k" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 0.6]} stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} width={34} />
                  <Tooltip cursor={{ fill: 'rgba(255,255,255,.03)' }} contentStyle={{ background: '#161D26', border: '1px solid #24303D', borderRadius: 12, fontSize: 12 }} formatter={(v) => [Number(v).toFixed(3), 'Silhouette']} />
                  <Bar dataKey="v" radius={[6, 6, 0, 0]} animationDuration={600}>{Object.keys(d.model.silhouette_by_k).map((kk) => <Cell key={kk} fill={Number(kk) === d.model.k ? '#22D3EE' : '#33465a'} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="mt-2 text-xs text-muted">Answer: only weakly. Silhouette {d.model.silhouette.toFixed(2)} at k=3 means {d.model.silhouette_reading}. {d.model.best_silhouette_k !== d.model.k && `k=${d.model.best_silhouette_k} scores higher, but k=${d.model.k} is used so groups read as lower, moderate and higher engagement.`} Agreement with a Gaussian mixture is ARI {d.model.gmm_agreement_ari.toFixed(2)}, so the exact boundaries depend on the algorithm.</p>
            </Card>
          </div>

          <Card className="p-5">
            <SectionTitle title="Engagement groups" sub={`KMeans on four standardized, log-scaled features. ${d.model.pca_note} Axes explain ${(d.scatter.explained_variance.reduce((a, b) => a + b, 0) * 100).toFixed(0)}% of the variance.`} />
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid stroke="#24303D" strokeDasharray="3 6" />
                <XAxis type="number" dataKey="x" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} name="Component 1" />
                <YAxis type="number" dataKey="y" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} width={34} name="Component 2" />
                <ZAxis range={[22, 22]} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: '#161D26', border: '1px solid #24303D', borderRadius: 12, fontSize: 12 }} />
                {d.clusters.map((c) => <Scatter key={c.id} name={c.label} data={d.scatter.points.filter((p) => p[2] === c.id).map((p) => ({ x: p[0], y: p[1] }))} fill={toneOf(c.id, k)} fillOpacity={0.55} isAnimationActive={false} />)}
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted">{d.clusters.map((c) => <span key={c.id} className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: toneOf(c.id, k) }} />{c.label}</span>)}<span>1,200 randomly sampled videos shown</span></div>
          </Card>

          <div>
            <SectionTitle title="What distinguishes each group?" sub={d.model.tiers_consistent ? 'Groups are ordered by the combined position of views, likes, comments and engagement rate.' : 'Groups are ordered by the combined position of all four measures; they are not ordered the same way on reach and on rate in this country.'} />
            <motion.div variants={stagger} initial="initial" animate="animate" className="grid gap-4 lg:grid-cols-3 [&>*]:min-w-0">{d.clusters.map((c) => <ClusterCard key={c.id} c={c} k={k} />)}</motion.div>
          </div>

          <Card className="p-5">
            <SectionTitle title="Observations for creators" sub="Generated from this dataset's numbers" />
            <ul className="space-y-2.5 text-sm">{d.takeaways.map((t, i) => <li key={i} className="flex gap-3"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" /><span>{t}</span></li>)}</ul>
            <div className="mt-5 border-t border-line pt-4"><div className="text-xs font-medium uppercase tracking-wider text-muted">Limitations</div>
              <ul className={clsx('mt-2 space-y-1.5 text-xs text-muted')}>{d.caveats.map((t, i) => <li key={i}>{t}</li>)}</ul></div>
          </Card>

          <Card className="p-5">
            <SectionTitle title="Method" />
            <ol className="list-decimal space-y-1 pl-5 text-sm text-muted">
              <li>One row per video: the latest trending record ({fmtInt(d.dataset.rows_raw)} rows reduced to {fmtInt(d.dataset.videos_unique)} unique videos).</li>
              <li>Excluded videos whose engagement cannot be measured: {Object.entries(d.dataset.excluded).map(([a, b]) => `${a.replaceAll('_', ' ')} (${b})`).join(', ')}.</li>
              <li>Features: {d.model.features.join(', ')}. {d.features_definition} {d.model.scaling}.</li>
              <li>{d.model.algorithm} with k = {d.model.k}; silhouette checked for k = 2 to 8; Gaussian-mixture cross-check; stability by 10 subsample refits.</li>
            </ol>
          </Card>
        </>
      )}
    </div>
  )
}
