import { Search } from 'lucide-react'
import { useState } from 'react'
import { FilterBar } from '../components/FilterBar'
import { TopContentList } from '../components/cards/blocks'
import { Card, EmptyState, ErrorState, Modal, Segmented, Skeleton } from '../components/ui/primitives'
import { useApi } from '../hooks/useApi'
import { useFilters } from '../hooks/useFilters'
import { CATEGORIES } from '../types/api'
import type { ContentDetail, ContentItem, ContentList } from '../types/api'
import { cap, fmtInt, fmtRate } from '../data/format'

export default function Content() {
  const { params } = useFilters()
  const [sort, setSort] = useState<'perf_index' | 'published_at' | 'views' | 'engagement_rate'>('perf_index')
  const [category, setCategory] = useState('')
  const [q, setQ] = useState('')
  const [sel, setSel] = useState<ContentItem | null>(null)
  const list = useApi<ContentList>('/content', { ...params, sort, category, search: q, limit: 100 })
  const det = useApi<ContentDetail>(sel ? `/content/${encodeURIComponent(sel.content_id)}` : null)
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h1 className="text-2xl font-semibold tracking-tight">Content</h1><p className="mt-1 text-sm text-muted">Every post, normalized across platforms.</p></div>
        <FilterBar />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search titles" maxLength={80} aria-label="Search titles" className="h-10 w-56 rounded-xl border border-line bg-graphite pl-9 pr-3 text-sm outline-none focus:border-cyan/60" /></div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category" className="h-10 rounded-xl border border-line bg-graphite px-3 text-sm outline-none focus:border-cyan/60"><option value="">All topics</option>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select>
        <Segmented value={sort} onChange={setSort} options={[{ value: 'perf_index', label: 'Best' }, { value: 'published_at', label: 'Newest' }, { value: 'views', label: 'Views' }, { value: 'engagement_rate', label: 'Engagement' }]} />
      </div>
      {list.error ? <ErrorState message={list.error} onRetry={list.reload} /> : !list.data ? <Skeleton className="h-96" /> : list.data.items.length === 0 ? <EmptyState title="No content matches" body="Try widening the date range or clearing filters." /> : (
        <Card className="p-4"><p className="mb-1 px-1 text-xs text-muted">{fmtInt(list.data.total)} posts · showing {list.data.items.length}</p><TopContentList items={list.data.items} onSelect={setSel} /></Card>
      )}
      <Modal open={!!sel} onClose={() => setSel(null)} title={sel?.title || 'Post details'}>
        {det.error ? <p className="text-sm text-rose">{det.error}</p> : !det.data ? <Skeleton className="h-40" /> : (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-3">{[['Views', fmtInt(det.data.views)], ['Engagement', fmtRate(det.data.engagement_rate)], ['Likes', fmtInt(det.data.likes)], ['Comments', fmtInt(det.data.comments)], ['Shares', fmtInt(det.data.shares)], ['Performance index', det.data.perf_index.toFixed(0)]].map(([k, v]) => <div key={k} className="rounded-xl border border-line p-3"><div className="text-[11px] uppercase tracking-wider text-muted">{k}</div><div className="num mt-1 text-lg font-semibold">{v}</div></div>)}</div>
            <p className="text-muted">{cap(det.data.content_type)} · {det.data.category} · published {det.data.publish_slot}{det.data.duration_sec ? ` · ${Math.round(det.data.duration_sec / 60 * 10) / 10} min` : ''}</p>
            <p>Views are <b>{det.data.vs_platform_median.views_ratio.toFixed(1)}×</b> and engagement <b>{det.data.vs_platform_median.engagement_rate_ratio.toFixed(1)}×</b> your median on this platform.</p>
          </div>)}
      </Modal>
    </div>
  )
}
