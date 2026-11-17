import { Check, Download, KeyRound, ShieldCheck, Trash2, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'
import { PlatformMark } from '../components/ui/PlatformMark'
import { Button, Card, ErrorState, Modal, SectionTitle, Skeleton } from '../components/ui/primitives'
import { useApi } from '../hooks/useApi'
import { useAuth } from '../hooks/useAuth'
import { api, ApiError } from '../services/api'
import { fmtDateLong } from '../data/format'
import type { LayoutCtx } from '../layouts/AppLayout'
import type { PlatformConn, PlatformId, PrivacyOverview } from '../types/api'

const STATUS: Record<PlatformConn['status'], { t: string; c: string }> = {
  connected: { t: 'Connected', c: 'text-mint' }, available: { t: 'Not connected', c: 'text-muted' },
  not_configured: { t: 'Not configured on this server', c: 'text-amber' }, demo: { t: 'Demo data', c: 'text-amber' },
}

export default function Privacy() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const ctx = useOutletContext<LayoutCtx>()
  const [sp, setSp] = useSearchParams()
  const ov = useApi<PrivacyOverview>('/privacy/overview')
  const pl = useApi<PlatformConn[]>('/platforms')
  const [confirm, setConfirm] = useState<{ kind: 'disconnect'; p: PlatformId } | { kind: 'data' } | { kind: 'account' } | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    const c = sp.get('connected'), e = sp.get('error')
    if (c) setMsg({ ok: true, text: `${c} connected. ${sp.get('synced') ?? 0} posts synced.` })
    if (e) setMsg({ ok: false, text: e })
    if (c || e) { setSp({}, { replace: true }); pl.reload(); ov.reload(); ctx.reloadSource() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const refresh = () => { pl.reload(); ov.reload(); ctx.reloadSource() }
  const act = async (key: string, fn: () => Promise<unknown>, ok: string) => {
    setBusy(key); setMsg(null)
    try { await fn(); setMsg({ ok: true, text: ok }); refresh() } catch (e) { setMsg({ ok: false, text: e instanceof ApiError ? e.message : 'Something went wrong' }) } finally { setBusy(null); setConfirm(null) }
  }
  const connect = (p: PlatformId) => act(`c-${p}`, async () => { const r = await api<{ authorization_url: string }>(`/connect/${p}/start`, { method: 'POST' }); window.location.href = r.authorization_url }, 'Redirecting…')
  const exportData = async () => {
    try {
      const d = await api<unknown>('/privacy/export')
      const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }))
      const a = document.createElement('a'); a.href = url; a.download = 'socialiq-export.json'; a.click(); URL.revokeObjectURL(url)
    } catch (e) { setMsg({ ok: false, text: e instanceof ApiError ? e.message : 'Export failed' }) }
  }
  const o = ov.data

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold tracking-tight">Security &amp; Privacy Center</h1><p className="mt-1 text-sm text-muted"><b className="text-ink">SocialIQ never needs your social-media password.</b> Here is exactly what it can access, what it stores, and how to remove it.</p></div>
      {msg && <div role="status" className={`rounded-xl border p-3 text-sm ${msg.ok ? 'border-mint/30 bg-mint/5 text-mint' : 'border-rose/30 bg-rose/5 text-rose'}`}>{msg.text}</div>}
      {user?.is_demo && <div className="rounded-xl border border-amber/30 bg-amber/5 p-3 text-sm text-amber">You are in demo mode. The accounts below show synthetic data and cannot be connected or deleted. Create an account to connect real platforms.</div>}

      <Card className="p-5">
        <SectionTitle title="Connected accounts" sub="Each platform connects independently with read-only access." />
        {pl.error ? <ErrorState message={pl.error} onRetry={pl.reload} /> : !pl.data ? <Skeleton className="h-60" /> : (
          <ul className="divide-y divide-line">{pl.data.map((p) => (
            <li key={p.platform} className="flex flex-wrap items-center gap-4 py-4">
              <PlatformMark platform={p.platform} size={30} />
              <div className="min-w-0 flex-1 basis-56">
                <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{p.label}</span><span className={`text-xs ${STATUS[p.status].c}`}>{STATUS[p.status].t}</span>{p.account_label && p.status === 'connected' && <span className="text-xs text-muted">{p.account_label}</span>}</div>
                <p className="mt-1 text-xs leading-relaxed text-muted">{p.notes}</p>
                <p className="mt-1 text-[11px] text-muted">Permission requested: {p.scopes.map((s) => <code key={s} className="mr-1.5 break-all rounded bg-elevated px-1.5 py-0.5">{s.split('/').pop()}</code>)}{p.last_synced_at && <> · synced {fmtDateLong(p.last_synced_at)}</>}</p>
              </div>
              {p.status === 'connected' ? <Button variant="danger" size="sm" onClick={() => setConfirm({ kind: 'disconnect', p: p.platform })}>Disconnect</Button>
                : p.status === 'available' ? <Button size="sm" loading={busy === `c-${p.platform}`} icon={<KeyRound className="h-3.5 w-3.5" />} onClick={() => connect(p.platform)}>Connect</Button>
                : <Button size="sm" variant="outline" disabled>{p.status === 'demo' ? 'Demo only' : 'Unavailable'}</Button>}
            </li>))}</ul>)}
      </Card>

      {o ? (<>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="p-5"><SectionTitle title="What SocialIQ stores" /><ul className="space-y-2 text-sm">{o.stores.map((s) => <li key={s} className="flex gap-2.5"><Check className="mt-0.5 h-4 w-4 shrink-0 text-mint" /><span className="text-muted">{s}</span></li>)}</ul>
            <h4 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wider text-muted">Never stored</h4><ul className="space-y-2 text-sm">{o.never_stores.map((s) => <li key={s} className="flex gap-2.5"><X className="mt-0.5 h-4 w-4 shrink-0 text-rose" /><span className="text-muted">{s}</span></li>)}</ul>
            <p className="mt-4 text-xs text-muted">{o.stored_content_rows} post records currently stored for your account.</p></Card>
          <Card className="p-5"><SectionTitle title="How the AI uses your data" /><p className="mb-3 text-sm text-muted">{o.ai.note}</p>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">May be sent to the AI provider</h4><ul className="list-disc space-y-1 pl-5 text-sm text-muted">{o.ai.sends.map((s) => <li key={s}>{s}</li>)}</ul>
            <h4 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-muted">Never sent</h4><ul className="list-disc space-y-1 pl-5 text-sm text-muted">{o.ai.never_sends.map((s) => <li key={s}>{s}</li>)}</ul></Card>
        </div>
        <Card className="p-5"><SectionTitle title="Security, stated honestly" />
          <div className="grid gap-4 sm:grid-cols-2"><ul className="space-y-2 text-sm text-muted"><li className="flex gap-2.5"><ShieldCheck className="h-4 w-4 shrink-0 text-mint" />OAuth only; read-only scopes</li><li className="flex gap-2.5"><ShieldCheck className="h-4 w-4 shrink-0 text-mint" />Tokens: {o.security.token_encryption}</li><li className="flex gap-2.5"><ShieldCheck className="h-4 w-4 shrink-0 text-mint" />SocialIQ passwords: {o.security.password_hashing}</li><li className="flex gap-2.5"><ShieldCheck className="h-4 w-4 shrink-0 text-mint" />{o.security.transport}</li></ul>
            <div><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber">What we do not claim</h4><ul className="list-disc space-y-1 pl-5 text-sm text-muted">{o.security.not_claimed.map((s) => <li key={s}>{s}</li>)}</ul></div></div></Card>
      </>) : <Skeleton className="h-60" />}

      <Card className="p-5"><SectionTitle title="Your data, your control" />
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" icon={<Download className="h-4 w-4" />} onClick={exportData} disabled={!!user?.is_demo}>Export my data (JSON)</Button>
          <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirm({ kind: 'data' })} disabled={!!user?.is_demo}>Delete all synced data</Button>
          <Button variant="danger" onClick={() => setConfirm({ kind: 'account' })} disabled={!!user?.is_demo}>Delete my account</Button>
        </div>
        <p className="mt-3 text-xs text-muted">Disconnecting deletes the stored tokens. To fully revoke access, also remove SocialIQ in each platform's own security settings.</p></Card>

      <Modal open={!!confirm} onClose={() => setConfirm(null)} title={confirm?.kind === 'disconnect' ? 'Disconnect platform?' : confirm?.kind === 'data' ? 'Delete all synced data?' : 'Delete your account?'}>
        <p className="text-sm text-muted">{confirm?.kind === 'disconnect' ? 'Stored tokens and this platform\'s synced posts will be permanently deleted.' : confirm?.kind === 'data' ? 'All synced posts are deleted and every platform is disconnected. Your SocialIQ login is kept.' : 'Your login, connections, tokens and all data are permanently deleted. This cannot be undone.'}</p>
        <div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={() => setConfirm(null)}>Cancel</Button>
          <Button variant="danger" loading={busy === 'confirm'} onClick={() => {
            if (!confirm) return
            if (confirm.kind === 'disconnect') act('confirm', () => api(`/connections/${confirm.p}`, { method: 'DELETE' }), 'Disconnected. Tokens and data removed.')
            else if (confirm.kind === 'data') act('confirm', () => api('/privacy/data', { method: 'DELETE' }), 'All synced data deleted.')
            else act('confirm', async () => { await api('/privacy/account', { method: 'DELETE' }); logout(); nav('/') }, 'Account deleted.')
          }}>Confirm</Button></div>
      </Modal>
    </div>
  )
}
