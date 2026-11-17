import { motion } from 'motion/react'
import { ArrowLeft, KeyRound, Eye, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Logo } from '../components/Logo'
import { PlatformMark } from '../components/ui/PlatformMark'
import { Button, Segmented } from '../components/ui/primitives'
import { useAuth } from '../hooks/useAuth'
import { PLATFORM_IDS, PLATFORM_LABEL } from '../types/api'

export default function Connect() {
  const { user, login, register, startDemo } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState<'register' | 'login'>('register')
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [name, setName] = useState('')
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null)
  if (user && !user.is_demo) return <Navigate to="/app/privacy" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null)
    try { if (mode === 'register') await register(email, password, name); else await login(email, password); nav('/app/privacy') }
    catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  const demo = async () => { setBusy(true); try { await startDemo(); nav('/app') } catch (x) { setErr((x as Error).message) } finally { setBusy(false) } }
  const input = 'h-11 w-full rounded-xl border border-line bg-graphite px-3.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-cyan/60'

  return (
    <div className="glow-bg min-h-screen">
      <div className="mx-auto grid min-h-screen max-w-5xl items-center gap-10 px-5 py-10 lg:grid-cols-2">
        <div>
          <Link to="/" className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" />Back</Link>
          <Logo />
          <h1 className="mt-8 text-3xl font-semibold tracking-tight">Connect with confidence</h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">Create a SocialIQ account first, then connect each platform with its own secure sign-in screen. Connections are independent: link one or all four.</p>
          <ul className="mt-6 space-y-3 text-sm">
            {[[KeyRound, 'SocialIQ never sees or stores your social-media passwords.'], [Eye, 'We request read-only access. SocialIQ cannot post, edit or delete anything.'], [ShieldCheck, 'Tokens are encrypted at rest. Disconnect or delete your data any time.']].map(([I, t], i) => {
              const Icon = I as typeof KeyRound
              return <li key={i} className="flex gap-3"><Icon className="mt-0.5 h-4 w-4 shrink-0 text-mint" /><span className="text-muted">{t as string}</span></li>
            })}
          </ul>
          <div className="mt-8 flex gap-3">{PLATFORM_IDS.map((p) => <span key={p} title={PLATFORM_LABEL[p]}><PlatformMark platform={p} size={24} /></span>)}</div>
        </div>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-6 sm:p-8">
          <Segmented value={mode} onChange={setMode} options={[{ value: 'register', label: 'Create account' }, { value: 'login', label: 'Sign in' }]} className="mb-6" />
          <form onSubmit={submit} className="space-y-3.5">
            {mode === 'register' && <input className={input} placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} autoComplete="name" />}
            <input className={input} type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            <input className={input} type="password" required minLength={mode === 'register' ? 10 : 1} placeholder={mode === 'register' ? 'Password (10+ characters)' : 'Password'} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
            {err && <p role="alert" className="text-sm text-rose">{err}</p>}
            <Button type="submit" loading={busy} className="w-full" size="lg">{mode === 'register' ? 'Create account' : 'Sign in'}</Button>
          </form>
          <p className="mt-3 text-[11px] leading-relaxed text-muted">This is your SocialIQ login only. It is separate from your social accounts.</p>
          <div className="my-6 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" /></div>
          <Button variant="outline" className="w-full" onClick={demo} disabled={busy}>Explore with demo data instead</Button>
        </motion.div>
      </div>
    </div>
  )
}
