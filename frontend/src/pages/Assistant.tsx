import { AnimatePresence, motion } from 'motion/react'
import { ArrowUp, Cpu, Wrench } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { CardRenderer } from '../components/cards/CardRenderer'
import { Card } from '../components/ui/primitives'
import { api, ApiError } from '../services/api'
import type { ChatResponse } from '../types/api'
import clsx from 'clsx'

const SUGGESTED = ['Why did my engagement drop?', 'Which platform is performing best?', 'What should I post next?', 'Compare my platforms', 'Show my best-performing content']
const STEPS = ['Choosing tools', 'Querying your analytics', 'Reasoning over results']

type Msg = { role: 'user'; content: string } | { role: 'assistant'; res: ChatResponse } | { role: 'error'; content: string }

function Thinking() {
  const [i, setI] = useState(0)
  useEffect(() => { const t = setInterval(() => setI((x) => Math.min(x + 1, STEPS.length - 1)), 900); return () => clearInterval(t) }, [])
  return (
    <div className="flex items-center gap-3 text-sm text-muted" role="status" aria-live="polite">
      <span className="flex gap-1">{[0, 1, 2].map((d) => <motion.span key={d} className="h-1.5 w-1.5 rounded-full bg-cyan" animate={{ opacity: [0.25, 1, 0.25] }} transition={{ duration: 1, repeat: Infinity, delay: d * 0.15 }} />)}</span>
      <AnimatePresence mode="wait"><motion.span key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>{STEPS[i]}…</motion.span></AnimatePresence>
    </div>
  )
}

export default function Assistant() {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [msgs, busy])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || busy) return
    const history: { role: 'user' | 'assistant'; content: string }[] = []
    for (const m of msgs) {
      if (m.role === 'user') history.push({ role: 'user', content: m.content })
      else if (m.role === 'assistant') history.push({ role: 'assistant', content: m.res.answer })
    }
    setMsgs((m) => [...m, { role: 'user', content: message }]); setInput(''); setBusy(true)
    try {
      const res = await api<ChatResponse>('/assistant/chat', { method: 'POST', body: { message, history: history.slice(-8) } })
      setMsgs((m) => [...m, { role: 'assistant', res }])
    } catch (e) { setMsgs((m) => [...m, { role: 'error', content: e instanceof ApiError ? e.message : 'The assistant could not answer.' }]) }
    finally { setBusy(false) }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-170px)] max-w-3xl flex-col">
      {msgs.length === 0 ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-1 flex-col items-center justify-center py-10 text-center">
          <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">What would you like to <span className="text-gradient">know?</span></h1>
          <p className="mt-3 max-w-md text-sm text-muted">Ask about your own analytics. The copilot calls real SocialIQ tools and shows you the evidence.</p>
          <div className="mt-8 flex max-w-xl flex-wrap justify-center gap-2.5">
            {SUGGESTED.map((s, i) => (<motion.button key={s} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }} whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }} onClick={() => send(s)} className="rounded-full border border-line bg-graphite px-4 py-2.5 text-sm transition-colors hover:border-cyan/50 hover:bg-elevated">{s}</motion.button>))}
          </div>
        </motion.div>
      ) : (
        <div className="flex-1 space-y-6 pb-6">
          {msgs.map((m, i) => m.role === 'user' ? (
            <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-md bg-elevated px-4 py-2.5 text-sm ring-1 ring-line">{m.content}</div></motion.div>
          ) : m.role === 'error' ? (
            <div key={i} role="alert" className="rounded-xl border border-rose/30 bg-rose/5 p-4 text-sm text-rose">{m.content}</div>
          ) : (
            <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
              {m.res.tool_calls.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted"><Wrench className="h-3 w-3" />Used:{m.res.tool_calls.map((t, k) => <span key={k} className={clsx('rounded-md border px-1.5 py-0.5 font-mono', t.ok ? 'border-line' : 'border-rose/40 text-rose')}>{t.name}</span>)}</div>
              )}
              {m.res.notice && <p className="rounded-lg border border-amber/30 bg-amber/5 p-2.5 text-xs text-amber">{m.res.notice}</p>}
              <div className="whitespace-pre-wrap text-[15px] leading-relaxed">{m.res.answer}</div>
              {m.res.cards.map((c, k) => <CardRenderer key={k} card={c} />)}
              <p className="flex items-center gap-1.5 text-[11px] text-muted"><Cpu className="h-3 w-3" />{m.res.mode_label}{m.res.source.mode === 'demo' && ' · demo data'}</p>
            </motion.div>
          ))}
          {busy && <Thinking />}
          <div ref={end} />
        </div>
      )}
      <div className="sticky bottom-4">
        <Card className="flex items-end gap-2 p-2 shadow-2xl shadow-black/40">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} maxLength={1000} aria-label="Ask the assistant" placeholder="Ask about your reach, engagement, timing or what to post…"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) } }}
            className="max-h-32 min-h-[40px] flex-1 resize-none bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-muted/70" />
          <motion.button whileTap={{ scale: 0.92 }} onClick={() => send(input)} disabled={busy || !input.trim()} aria-label="Send" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan text-obsidian transition-opacity disabled:opacity-40"><ArrowUp className="h-4 w-4" /></motion.button>
        </Card>
      </div>
    </div>
  )
}
