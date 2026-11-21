import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { Card } from '../ui/primitives'
import { AnomalyList, BestTimesBlock, CategoriesBlock, EngagementChangeBlock, PeriodBlock, PlatformComparisonBlock, PredictionBlock, ProfileBlock, StrategyBlock, TopContentList } from './blocks'
import { fmtCompact, fmtPct, fmtRate } from '../../data/format'
import type { AssistantCard } from '../../types/api'
import { Stat } from '../ui/primitives'

/* Renders the structured result of an assistant tool call. Cards are driven by real tool output, never by model prose. */
export function CardRenderer({ card }: { card: AssistantCard }) {
  const c = card as Record<string, any> // tool payloads are validated server-side; shapes vary per card type
  let title = '', body: ReactNode = null
  switch (card.type) {
    case 'platform_comparison': title = 'Platform comparison'; body = <PlatformComparisonBlock data={c as never} compact />; break
    case 'engagement_change': title = 'What changed in engagement'; body = <EngagementChangeBlock d={c as never} />; break
    case 'top_content': title = c.worst ? 'Weakest content' : 'Top content'; body = <TopContentList items={c.items} />; break
    case 'best_times': title = 'Best publishing windows'; body = <BestTimesBlock platforms={c.by_platform} />; break
    case 'categories': title = 'Performance by topic'; body = <CategoriesBlock rows={c.categories} />; break
    case 'anomalies': title = 'Unusual activity'; body = <AnomalyList data={c as never} />; break
    case 'profile': title = 'Creator profile'; body = <ProfileBlock p={c as never} />; break
    case 'prediction': title = 'Predicted performance'; body = <PredictionBlock pred={c as never} />; break
    case 'strategy': title = 'Recommended plan'; body = <StrategyBlock d={c as never} />; break
    case 'period_compare': title = 'Period comparison'; body = <PeriodBlock d={c as never} />; break
    case 'summary':
      title = `Last ${c.window_days} days`
      body = (<div className="grid grid-cols-3 gap-4"><Stat label="Views">{fmtCompact(c.current.views)}</Stat><Stat label="Engagement">{fmtRate(c.current.engagement_rate)}</Stat><Stat label="Followers">{c.followers.available ? fmtPct(c.followers.pct) : 'n/a'}</Stat></div>)
      break
    default: return null
  }
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card standalone className="p-5"><h4 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted">{title}</h4>{body}</Card>
    </motion.div>
  )
}
