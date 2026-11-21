import { motion } from 'motion/react'
import { ArrowRight, BrainCircuit, GitCompareArrows, LineChart, LockKeyhole, MessageSquareText, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Logo } from '../components/Logo'
import { PlatformMark } from '../components/ui/PlatformMark'
import { Button } from '../components/ui/primitives'
import { useAuth } from '../hooks/useAuth'
import { rise, stagger } from '../animations/variants'
import { PLATFORM_IDS } from '../types/api'

const PILLARS = [
  { icon: GitCompareArrows, t: 'One view, four platforms', d: 'YouTube, Instagram, X and LinkedIn normalized into one schema, so you compare like with like.' },
  { icon: LineChart, t: 'Why, not just what', d: 'Engagement fell 17%? See which platform and topic drove it, and whether it is statistically real.' },
  { icon: BrainCircuit, t: 'Predict before you post', d: 'A trained model scores your idea 0-100, shows its uncertainty and explains every factor with SHAP.' },
  { icon: MessageSquareText, t: 'A copilot that shows its work', d: 'Ask in plain language. It calls real analytics tools and never invents a number.' },
  { icon: LockKeyhole, t: 'Privacy you can inspect', d: 'OAuth only, read-only scopes, encrypted tokens, one-click disconnect and deletion.' },
  { icon: Sparkles, t: 'Honest by design', d: 'Demo data is always labelled. Unavailable platform data is reported as unavailable.' },
]

export default function Landing() {
  const { startDemo, user } = useAuth()
  const nav = useNavigate()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const demo = async (to = '/app') => {
    setBusy(true); setErr(null)
    try { await startDemo(); nav(to) } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="glow-bg min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <div className="flex items-center gap-2">
          {user ? <Link to="/app"><Button variant="outline" size="sm">Open dashboard</Button></Link> : <Link to="/connect"><Button variant="ghost" size="sm">Sign in</Button></Link>}
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-4xl px-5 pb-16 pt-14 text-center sm:pt-20">
          <motion.div variants={stagger} initial="initial" animate="animate">
            <motion.div variants={rise} className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-graphite px-3.5 py-1.5 text-xs text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-mint" /> Social intelligence for creators
            </motion.div>
            <motion.h1 variants={rise} className="text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-6xl">
              Your social presence.<br /><span className="text-gradient">One intelligent view.</span>
            </motion.h1>
            <motion.p variants={rise} className="mx-auto mt-6 max-w-2xl text-balance text-base leading-relaxed text-muted sm:text-lg">
              Traditional analytics tells you what happened. SocialIQ explains why, predicts what is next, and recommends what to do, across every platform you post on.
            </motion.p>
            <motion.div variants={rise} className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button size="lg" onClick={() => demo()} loading={busy} icon={!busy && <ArrowRight className="h-4 w-4" />} className="w-full sm:w-auto">Explore the live demo</Button>
              <Link to="/connect" className="w-full sm:w-auto"><Button size="lg" variant="outline" className="w-full">Connect my accounts</Button></Link>
            </motion.div>
            {err && <p role="alert" className="mt-4 text-sm text-rose">{err}</p>}
            <motion.p variants={rise} className="mt-4 text-xs text-muted">The demo uses clearly labelled synthetic data. No sign-up needed.</motion.p>
            <motion.div variants={rise} className="mt-10 flex items-center justify-center gap-5 opacity-90">
              {PLATFORM_IDS.map((p) => <PlatformMark key={p} platform={p} size={26} />)}
            </motion.div>
          </motion.div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-16">
          <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-60px' }} transition={{ duration: 0.5 }} className="card overflow-hidden p-2 sm:p-3">
            <div className="rounded-xl border border-line bg-obsidian p-4 sm:p-6">
              <div className="mb-4 flex items-center justify-between"><span className="text-xs font-medium uppercase tracking-wider text-muted">Example from the demo workspace</span><span className="rounded-full border border-amber/40 bg-amber/10 px-2 py-0.5 text-[10px] font-semibold text-amber">DEMO DATA</span></div>
              <div className="grid gap-6 sm:grid-cols-[1fr_1.2fr]">
                <div><div className="num text-4xl font-semibold">4.09%</div><div className="mt-1 text-sm text-rose">▼ 17.1% vs 4.93% in the 28 days before</div><p className="mt-3 text-sm text-muted">Statistically significant. X and Opinions posts pulled the blended rate down most, while YouTube improved. Comments fell from 11.3% to 9.9% of interactions.</p></div>
                <div className="space-y-3">{[['X', -0.91], ['Opinions', -0.69], ['Tutorials', -0.58], ['Instagram', -0.55]].map(([l, v], i) => (
                  <div key={String(l)} className="grid grid-cols-[84px_1fr_56px] items-center gap-3 text-[13px]"><span>{l}</span><div className="h-2 rounded-full bg-elevated"><motion.div initial={{ width: 0 }} whileInView={{ width: `${(Math.abs(v as number) / 0.91) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.1 * i }} className="h-full rounded-full bg-rose" /></div><span className="num text-right text-rose">{(v as number).toFixed(2)} pt</span></div>))}</div>
              </div>
            </div>
          </motion.div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-16">
          <div className="card p-5 sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><span className="text-xs font-medium uppercase tracking-wider text-cyan">YouTube engagement analysis</span>
                <h2 className="mt-1 text-xl font-semibold tracking-tight sm:text-2xl">Clustering 6,229 trending videos by engagement</h2>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">KMeans on scaled views, likes, comments and engagement rate from the Kaggle YouTube Trending dataset (US). It answers the five questions of the brief: category differences, view-like-comment relationships, whether distinct groups exist, what separates them, and what creators can take from it.</p></div>
              <span className="rounded-full border border-line px-2.5 py-1 text-[11px] text-muted">Historical data, descriptive, not predictive</span>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">{[['Lower engagement', '1.1%', '29K median views', '#94A3B8'], ['Moderate engagement', '2.6%', '350K median views', '#22D3EE'], ['Higher engagement', '3.9%', '2.0M median views', '#34D399']].map(([l, r, v, c]) => (
              <div key={l} className="rounded-xl border border-line bg-obsidian p-4"><div className="flex items-center gap-2 text-sm font-medium"><span className="h-2 w-2 rounded-full" style={{ background: c }} />{l}</div><div className="num mt-2 text-2xl font-semibold">{r}</div><div className="text-xs text-muted">median engagement rate · {v}</div></div>))}</div>
            <div className="mt-5"><Button variant="outline" onClick={() => demo('/app/clusters')} loading={busy} icon={!busy && <ArrowRight className="h-4 w-4" />}>Open the clustering analysis</Button></div>
            <p className="mt-4 text-xs text-muted">Silhouette 0.31: the groups overlap, so the data is closer to a continuum than to separate clusters. The app reports this openly.</p>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-20">
          <motion.div variants={stagger} initial="initial" whileInView="animate" viewport={{ once: true, margin: '-60px' }} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PILLARS.map((p) => (
              <motion.div key={p.t} variants={rise} whileHover={{ y: -3 }} className="card p-6">
                <div className="mb-4 inline-flex rounded-xl bg-elevated p-2.5 text-cyan"><p.icon className="h-5 w-5" /></div>
                <h3 className="text-base font-semibold">{p.t}</h3><p className="mt-2 text-sm leading-relaxed text-muted">{p.d}</p>
              </motion.div>
            ))}
          </motion.div>
        </section>
      </main>
      <footer className="border-t border-line px-5 py-8 text-center text-xs text-muted"><div className="mb-1 font-medium text-ink">Built by Darshil · 1st place, Data Analytics and ML Hackathon, Jaipur National University × Samatrix Consulting</div>SocialIQ never asks for your social-media passwords. It uses read-only OAuth access that you can revoke at any time.</footer>
    </div>
  )
}
