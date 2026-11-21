import { AnimatePresence, motion } from 'motion/react'
import { BarChart3, Boxes, FileText, LayoutDashboard, Lightbulb, LogOut, Menu, MessageSquareText, ShieldCheck, Sparkles, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { PlatformMark } from '../components/ui/PlatformMark'
import { DemoBadge, LiveBadge, Skeleton } from '../components/ui/primitives'
import { Logo } from '../components/Logo'
import { FilterProvider } from '../hooks/useFilters'
import { useApi } from '../hooks/useApi'
import { useAuth } from '../hooks/useAuth'
import { pageVariants } from '../animations/variants'
import type { PlatformConn, SourceInfo } from '../types/api'

const NAV = [
  { to: '/app', end: true, label: 'Overview', icon: LayoutDashboard },
  { to: '/app/clusters', label: 'Engagement Clusters', icon: Boxes },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/content', label: 'Content', icon: FileText },
  { to: '/app/predictions', label: 'Predictions', icon: Sparkles },
  { to: '/app/insights', label: 'Insights', icon: Lightbulb },
  { to: '/app/assistant', label: 'Assistant', icon: MessageSquareText },
  { to: '/app/privacy', label: 'Privacy Center', icon: ShieldCheck },
]

function Sidebar({ conns, onNavigate }: { conns: PlatformConn[] | null; onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pb-6 pt-5"><Logo /></div>
      <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} onClick={onNavigate}
            className={({ isActive }) => clsx('relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors', isActive ? 'text-ink' : 'text-muted hover:bg-graphite hover:text-ink')}>
            {({ isActive }) => (<>
              {isActive && <motion.span layoutId="nav-active" className="absolute inset-0 rounded-xl bg-elevated ring-1 ring-line" transition={{ type: 'spring', stiffness: 500, damping: 38 }} />}
              <n.icon className={clsx('relative h-[18px] w-[18px]', isActive && 'text-cyan')} /><span className="relative">{n.label}</span>
            </>)}
          </NavLink>
        ))}
      </nav>
      <div className="mt-4 border-t border-line px-5 py-4">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Platforms</div>
        <ul className="space-y-2">
          {conns ? conns.map((c) => (
            <li key={c.platform} className="flex items-center gap-2.5 text-[13px]">
              <PlatformMark platform={c.platform} size={18} /><span className="flex-1">{c.label}</span>
              <span className={clsx('text-[11px]', c.status === 'connected' ? 'text-mint' : c.status === 'demo' ? 'text-amber' : 'text-muted')}>
                {c.status === 'connected' ? 'Live' : c.status === 'demo' ? 'Demo' : c.status === 'available' ? 'Not connected' : 'Not configured'}
              </span>
            </li>
          )) : [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-5" />)}
        </ul>
        <div className="mt-4 text-[11px] text-muted">Built by Darshil</div>
      </div>
    </div>
  )
}

export interface LayoutCtx { source: SourceInfo | null; conns: PlatformConn[] | null; reloadSource: () => void }

export default function AppLayout() {
  const { user, loading, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  const src = useApi<SourceInfo>(user ? '/source' : null)
  const conns = useApi<PlatformConn[]>(user ? '/platforms' : null)
  if (loading) return <div className="grid min-h-screen place-items-center"><Skeleton className="h-10 w-40" /></div>
  if (!user) return <Navigate to="/connect" replace />
  const mode = src.data?.source.mode

  return (
    <FilterProvider>
      <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
        <aside className="sticky top-0 hidden h-screen border-r border-line bg-obsidian lg:block"><Sidebar conns={conns.data} /></aside>
        <div className="min-w-0">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-obsidian/85 px-4 py-3 backdrop-blur-md sm:px-8">
            <button className="rounded-lg p-1.5 text-muted hover:bg-graphite lg:hidden" aria-label="Open menu" onClick={() => setOpen(true)}><Menu className="h-5 w-5" /></button>
            <div className="lg:hidden"><Logo compact /></div>
            <div className="ml-auto flex items-center gap-3">
              {mode === 'demo' && <DemoBadge />}{mode === 'live' && <LiveBadge />}
              {mode === 'empty' && <span className="rounded-full border border-line px-2.5 py-1 text-[11px] font-semibold tracking-wide text-muted">NO DATA YET</span>}
              <span className="hidden text-sm text-muted sm:inline">{user.display_name}</span>
              <button onClick={() => { logout(); nav('/') }} aria-label="Sign out" title="Sign out" className="rounded-lg p-2 text-muted hover:bg-graphite hover:text-ink"><LogOut className="h-4 w-4" /></button>
            </div>
          </header>
          {mode === 'demo' && (
            <div className="border-b border-amber/20 bg-amber/5 px-4 py-2 text-center text-xs text-amber sm:px-8">
              You are exploring DEMO DATA: a synthetic creator, not a real account. <button className="underline underline-offset-2" onClick={() => { logout(); nav('/connect') }}>Create an account</button> to connect your own platforms.
            </div>
          )}
          <main className="mx-auto max-w-[1280px] px-4 py-6 sm:px-8 sm:py-8">
            <AnimatePresence mode="wait">
              <motion.div key={loc.pathname} variants={pageVariants} initial="initial" animate="animate" exit="exit">
                <Outlet context={{ source: src.data, conns: conns.data, reloadSource: () => { src.reload(); conns.reload() } } satisfies LayoutCtx} />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.div className="fixed inset-0 z-50 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
            <motion.div className="relative h-full w-[270px] border-r border-line bg-obsidian" initial={{ x: -270 }} animate={{ x: 0 }} exit={{ x: -270 }} transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}>
              <button className="absolute right-3 top-4 rounded-lg p-1.5 text-muted" aria-label="Close menu" onClick={() => setOpen(false)}><X className="h-5 w-5" /></button>
              <Sidebar conns={conns.data} onNavigate={() => setOpen(false)} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </FilterProvider>
  )
}
