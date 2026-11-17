import { AnimatePresence, motion } from 'motion/react'
import { Sparkles, Info, Wand2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { PredictionBlock } from '../components/cards/blocks'
import { Button, Card, SectionTitle, Skeleton, Modal } from '../components/ui/primitives'
import { PlatformMark } from '../components/ui/PlatformMark'
import { useApi } from '../hooks/useApi'
import { api, ApiError } from '../services/api'
import { CATEGORIES, CONTENT_TYPES, PLATFORM_IDS, PLATFORM_LABEL, type ModelCard, type PlatformId, type Prediction, type Recommendation } from '../types/api'
import { cap, fmtRate, localInputValue } from '../data/format'
import clsx from 'clsx'

const field = 'h-11 w-full rounded-xl border border-line bg-graphite px-3.5 text-sm outline-none transition-colors focus:border-cyan/60'

export default function Predictions() {
  const tomorrow = useMemo(() => { const d = new Date(); d.setDate(d.getDate() + 1); d.setHours(10, 0, 0, 0); return d }, [])
  const [title, setTitle] = useState('How to build a RAG pipeline in 20 minutes')
  const [platform, setPlatform] = useState<PlatformId>('youtube')
  const [category, setCategory] = useState<string>('Tutorials')
  const [ctype, setCtype] = useState('video')
  const [duration, setDuration] = useState('12')
  const [when, setWhen] = useState(localInputValue(tomorrow))
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null)
  const [runs, setRuns] = useState<Prediction[]>([])
  const [card, setCard] = useState(false)
  const mc = useApi<ModelCard>(card ? '/ml/model-card' : null)
  const hasDuration = platform === 'youtube' || (platform === 'instagram' && ctype === 'reel')

  const setPlat = (p: PlatformId) => { setPlatform(p); setCtype(CONTENT_TYPES[p][0]) }
  const run = async (override?: Partial<{ title: string; category: string; ctype: string; when: string }>) => {
    setBusy(true); setErr(null)
    const t = override?.title ?? title, c = override?.category ?? category, ct = override?.ctype ?? ctype, w = override?.when ?? when
    try {
      const r = await api<Prediction>('/ml/predict', { method: 'POST', body: { title: t, platform, category: c, content_type: ct, duration_sec: hasDuration && duration ? Math.round(Number(duration) * 60) : null, publish_at: new Date(w).toISOString() } })
      setRuns((x) => [r, ...x].slice(0, 4))
    } catch (e) { setErr(e instanceof ApiError ? e.message : 'Prediction failed') } finally { setBusy(false) }
  }
  const apply = (r: Recommendation) => {
    const ch = r.change; const n = { title, category, ctype, when }
    if (ch.title) { setTitle(ch.title); n.title = ch.title }
    if (ch.category) { setCategory(ch.category); n.category = ch.category }
    if (ch.content_type) { setCtype(ch.content_type); n.ctype = ch.content_type }
    if (ch.publish_at) { const w = localInputValue(new Date(ch.publish_at)); setWhen(w); n.when = w }
    run(n)
  }
  const latest = runs[0]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h1 className="text-2xl font-semibold tracking-tight">Content performance simulator</h1><p className="mt-1 max-w-2xl text-sm text-muted">Describe a post before you publish it. A model trained on your history predicts its Performance Score and shows what drives it.</p></div>
        <Button variant="outline" size="sm" icon={<Info className="h-3.5 w-3.5" />} onClick={() => setCard(true)}>Model details</Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[400px_1fr]">
        <Card className="h-fit p-5">
          <form onSubmit={(e) => { e.preventDefault(); run() }} className="space-y-4">
            <div><label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="t">Title or hook</label><textarea id="t" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} rows={2} className={clsx(field, 'h-auto resize-none py-2.5')} /></div>
            <div><span className="mb-1.5 block text-xs font-medium text-muted">Platform</span>
              <div className="grid grid-cols-4 gap-2">{PLATFORM_IDS.map((p) => (<button type="button" key={p} onClick={() => setPlat(p)} aria-pressed={platform === p} title={PLATFORM_LABEL[p]} className={clsx('flex h-11 items-center justify-center rounded-xl border transition-colors', platform === p ? 'border-cyan/60 bg-cyan/10' : 'border-line hover:bg-elevated')}><PlatformMark platform={p} size={20} /></button>))}</div></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="c">Topic</label><select id="c" value={category} onChange={(e) => setCategory(e.target.value)} className={field}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></div>
              <div><label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="f">Format</label><select id="f" value={ctype} onChange={(e) => setCtype(e.target.value)} className={field}>{CONTENT_TYPES[platform].map((c) => <option key={c} value={c}>{cap(c)}</option>)}</select></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="d">Length (min)</label><input id="d" type="number" min={0} step="0.5" disabled={!hasDuration} value={hasDuration ? duration : ''} placeholder={hasDuration ? '' : 'n/a'} onChange={(e) => setDuration(e.target.value)} className={clsx(field, !hasDuration && 'opacity-50')} /></div>
              <div><label className="mb-1.5 block text-xs font-medium text-muted" htmlFor="w">Publish time (your local)</label><input id="w" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className={field} /></div>
            </div>
            {err && <p role="alert" className="text-sm text-rose">{err}</p>}
            <Button type="submit" size="lg" className="w-full" loading={busy} icon={!busy && <Sparkles className="h-4 w-4" />}>Predict performance</Button>
            <p className="text-[11px] text-muted">Times are converted to UTC for the model. Change any input and predict again to compare.</p>
          </form>
        </Card>

        <div className="space-y-4">
          {busy && !latest && <Skeleton className="h-72" />}
          {!latest && !busy && <Card standalone className="grid h-72 place-items-center p-8 text-center"><div><Wand2 className="mx-auto h-7 w-7 text-cyan" /><p className="mt-3 text-sm text-muted">Your prediction will appear here, with the reasons behind it.</p></div></Card>}
          <AnimatePresence mode="popLayout">
            {latest && (
              <motion.div key={runs.length} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <Card standalone className="p-5">
                  <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-muted"><PlatformMark platform={latest.spec.platform} size={16} /><span className="truncate">{latest.spec.title || '(no title)'}</span><span>· {latest.spec.category} · {cap(latest.spec.content_type)}</span></div>
                  <PredictionBlock pred={latest} />
                </Card>
              </motion.div>)}
          </AnimatePresence>
          {latest?.recommendations && latest.recommendations.length > 0 && (
            <Card standalone className="p-5"><SectionTitle title="Try this" sub="Each suggestion was re-scored by the model with exactly one change" />
              <ul className="space-y-2">{latest.recommendations.map((r, i) => (<li key={i}><button onClick={() => apply(r)} disabled={busy} className="flex w-full items-center gap-3 rounded-xl border border-line p-3 text-left text-sm transition-colors hover:bg-elevated"><span className="flex-1">{r.text}</span><span className="num font-semibold text-mint">+{r.delta.toFixed(1)}</span></button></li>))}</ul></Card>)}
          {latest?.recommendations && latest.recommendations.length === 0 && <Card standalone className="p-5 text-sm text-muted">No single change was predicted to improve this post meaningfully. It is already near the best option the model can find.</Card>}
          {runs.length > 1 && (
            <Card standalone className="p-5"><SectionTitle title="Compare runs" />
              <div className="overflow-x-auto"><table className="w-full min-w-[480px] text-sm"><thead><tr className="text-left text-xs text-muted"><th className="pb-2 font-medium">Post</th><th className="pb-2 font-medium">Platform</th><th className="pb-2 font-medium">Score</th><th className="pb-2 font-medium">Range</th></tr></thead>
                <tbody className="divide-y divide-line">{runs.map((r, i) => (<tr key={i} className={i === 0 ? '' : 'text-muted'}><td className="max-w-[220px] truncate py-2.5">{r.spec.title || '(no title)'}<div className="text-[11px]">{r.spec.category} · {r.spec.content_type} · {new Date(r.spec.publish_at).toLocaleString('en-US', { weekday: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })} UTC</div></td><td>{PLATFORM_LABEL[r.spec.platform]}</td><td className="num font-semibold">{r.score.toFixed(0)} <span className="text-[11px] font-normal">{r.label}</span></td><td className="num">{r.interval.low.toFixed(0)}–{r.interval.high.toFixed(0)}</td></tr>))}</tbody></table></div></Card>)}
        </div>
      </div>

      <Modal open={card} onClose={() => setCard(false)} title="Model card" width="max-w-2xl">
        {mc.error ? <p className="text-sm text-rose">{mc.error}</p> : !mc.data ? <Skeleton className="h-64" /> : (
          <div className="space-y-5 text-sm">
            <p className="text-muted"><b className="text-ink">Target:</b> {mc.data.target}. {mc.data.classes}.</p>
            <div><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Model selection (time-series cross-validation, MAE: lower is better)</h4>
              <table className="w-full text-[13px]"><tbody className="divide-y divide-line">{mc.data.candidates.map((c) => (<tr key={c.name} className={c.selected ? 'text-mint' : ''}><td className="py-1.5">{c.name}{c.selected && ' ✓ selected'}</td><td className="num text-right">MAE {c.cv_mae.toFixed(1)} ± {c.cv_mae_std.toFixed(1)}</td><td className="num text-right">R² {c.cv_r2.toFixed(2)}</td></tr>))}</tbody></table></div>
            <div><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Held-out test ({mc.data.n_test} newest posts)</h4>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{[['MAE', mc.data.test.mae.toFixed(1)], ['vs baseline MAE', mc.data.test.baseline_mae.toFixed(1)], ['Rank corr. (Spearman)', mc.data.test.spearman.toFixed(2)], ['Top-third hit rate', mc.data.test.top_third_hit_rate == null ? 'n/a' : fmtRate(mc.data.test.top_third_hit_rate, 0)], ['Bias (pts)', (mc.data.test.bias > 0 ? '+' : '') + mc.data.test.bias.toFixed(1)], [`${Math.round(mc.data.interval.level * 100)}% interval coverage`, fmtRate(mc.data.interval.empirical_test_coverage, 0)]].map(([k, v]) => <div key={k} className="rounded-xl border border-line p-2.5"><div className="text-[10px] uppercase tracking-wider text-muted">{k}</div><div className="num mt-0.5 font-semibold">{v}</div></div>)}</div></div>
            <div><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">What drives the model overall</h4><ul className="space-y-1">{mc.data.global_importance.slice(0, 5).map((g) => <li key={g.group} className="flex justify-between"><span>{g.group}</span><span className="num text-muted">{g.importance.toFixed(1)}</span></li>)}</ul></div>
            <div><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Leakage controls</h4><ul className="list-disc space-y-1 pl-5 text-muted">{mc.data.leakage_controls.map((l) => <li key={l}>{l}</li>)}</ul></div>
            <div><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber">Caveats</h4><ul className="list-disc space-y-1 pl-5 text-muted">{mc.data.caveats.map((l) => <li key={l}>{l}</li>)}</ul></div>
            <p className="text-xs text-muted">{mc.data.split}. Trained on {mc.data.n_posts} posts ({mc.data.data_mode} data).</p>
          </div>)}
      </Modal>
    </div>
  )
}
