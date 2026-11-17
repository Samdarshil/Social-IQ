import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { InsightView, PlatformTag } from '../components/cards/blocks'
import { Card, EmptyState, ErrorState, SectionTitle, Skeleton } from '../components/ui/primitives'
import { useApi } from '../hooks/useApi'
import { stagger } from '../animations/variants'
import type { Idea, Insights as InsightsT } from '../types/api'
import { cap } from '../data/format'

export default function Insights() {
  const ins = useApi<InsightsT>('/insights')
  const ideas = useApi<{ items: Idea[] }>('/ml/ideas')
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold tracking-tight">Insights</h1><p className="mt-1 text-sm text-muted">What happened, why it happened, and what to do next. Each card is computed from your data.</p></div>
      {ins.error ? <ErrorState message={ins.error} onRetry={ins.reload} /> : !ins.data ? <Skeleton className="h-48" /> : ins.data.cards.length === 0 ? <EmptyState title="No insights yet" body="Insights appear once there is enough posting history to analyse." /> : (
        <motion.div variants={stagger} initial="initial" animate="animate" className="grid gap-4 md:grid-cols-2">{ins.data.cards.map((c, i) => <InsightView key={i} c={c} />)}</motion.div>)}
      <Card className="p-5">
        <SectionTitle title="Model-suggested ideas for tomorrow" sub="Every platform, topic and format scored by the prediction model at its best hour" right={<Link to="/app/predictions" className="text-sm text-cyan hover:underline">Open simulator</Link>} />
        {ideas.error ? <p className="text-sm text-muted">{ideas.error}</p> : !ideas.data ? <Skeleton className="h-40" /> : (
          <ul className="divide-y divide-line">{ideas.data.items.map((i, k) => (
            <li key={k} className="flex items-center gap-3 py-3 text-sm"><PlatformTag p={i.platform} className="w-28" /><span className="flex-1">{i.category} · {cap(i.content_type)}<span className="text-muted"> · {i.day} ~{String(i.hour).padStart(2, '0')}:00 UTC</span></span><span className="num font-semibold text-mint">{i.score.toFixed(0)}</span></li>))}</ul>)}
      </Card>
    </div>
  )
}
