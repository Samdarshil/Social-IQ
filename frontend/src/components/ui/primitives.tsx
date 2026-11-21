import { AnimatePresence, animate, motion, useInView, useMotionValue, useTransform } from 'motion/react'
import { AlertTriangle, FlaskConical, Inbox, RefreshCw, X } from 'lucide-react'
import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import clsx from 'clsx'
import { modal, rise } from '../../animations/variants'

export function Card({ children, className, hover, elevated, standalone, ...rest }: { children: ReactNode; className?: string; hover?: boolean; elevated?: boolean; standalone?: boolean } & Omit<React.HTMLAttributes<HTMLDivElement>, 'children'>) {
  return (
    <motion.div variants={rise} {...(standalone ? { initial: 'initial', animate: 'animate' } : {})} whileHover={hover ? { y: -2, transition: { duration: 0.15 } } : undefined}
      className={clsx(elevated ? 'card-elev' : 'card', 'min-w-0 hairline-top', hover && 'transition-colors hover:border-[#33465a]', className)} {...(rest as object)}>
      {children}
    </motion.div>
  )
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'outline' | 'danger'; size?: 'sm' | 'md' | 'lg'; loading?: boolean; icon?: ReactNode }
export function Button({ variant = 'primary', size = 'md', loading, icon, children, className, disabled, ...rest }: BtnProps) {
  const base = 'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors select-none disabled:opacity-50 disabled:pointer-events-none'
  const sizes = { sm: 'h-8 px-3 text-[13px]', md: 'h-10 px-4 text-sm', lg: 'h-12 px-6 text-[15px]' }
  const variants = {
    primary: 'bg-cyan text-obsidian hover:bg-[#4be0f5] font-semibold',
    ghost: 'text-muted hover:text-ink hover:bg-elevated',
    outline: 'border border-line text-ink hover:bg-elevated hover:border-[#33465a]',
    danger: 'border border-rose/40 text-rose hover:bg-rose/10',
  }
  return (
    <motion.button whileTap={{ scale: 0.97 }} transition={{ duration: 0.1 }} disabled={disabled || loading}
      className={clsx(base, sizes[size], variants[variant], className)} {...(rest as object)}>
      {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : icon}
      {children}
    </motion.button>
  )
}

export function Skeleton({ className }: { className?: string }) { return <div className={clsx('skeleton', className)} aria-hidden /> }

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card flex flex-col items-center gap-3 p-8 text-center">
      <AlertTriangle className="h-6 w-6 text-amber" />
      <p className="max-w-md text-sm text-muted">{message}</p>
      {onRetry && <Button variant="outline" size="sm" onClick={onRetry} icon={<RefreshCw className="h-3.5 w-3.5" />}>Try again</Button>}
    </div>
  )
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-3 p-10 text-center">
      <Inbox className="h-6 w-6 text-muted" />
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-muted">{body}</p>
      {action}
    </div>
  )
}

export function DemoBadge({ className }: { className?: string }) {
  return (
    <span title="Synthetic data. This is not a real account." className={clsx('inline-flex items-center gap-1.5 rounded-full border border-amber/40 bg-amber/10 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-amber', className)}>
      <FlaskConical className="h-3 w-3" /> DEMO DATA
    </span>
  )
}

export function LiveBadge() {
  return <span className="inline-flex items-center gap-1.5 rounded-full border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-mint"><span className="h-1.5 w-1.5 rounded-full bg-mint" />LIVE DATA</span>
}

export function CountUp({ value, format = (n: number) => Math.round(n).toLocaleString('en-US'), className }: { value: number; format?: (n: number) => string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const mv = useMotionValue(0)
  const text = useTransform(mv, (v) => format(v))
  useEffect(() => {
    if (!inView) return
    const c = animate(mv, value, { duration: 0.9, ease: [0.22, 1, 0.36, 1] })
    return () => c.stop()
  }, [inView, value, mv])
  return <motion.span ref={ref} className={clsx('num', className)}>{text}</motion.span>
}

export function Delta({ value, invert, className }: { value: number | null | undefined; invert?: boolean; className?: string }) {
  if (value == null) return <span className={clsx('text-xs text-muted', className)}>no prior data</span>
  const good = invert ? value < 0 : value > 0
  const flat = Math.abs(value) < 0.05
  return <span className={clsx('num text-xs font-medium', flat ? 'text-muted' : good ? 'text-mint' : 'text-rose', className)}>{value > 0 ? '▲' : value < 0 ? '▼' : '•'} {Math.abs(value).toFixed(1)}%</span>
}

export function Modal({ open, onClose, title, children, width = 'max-w-lg' }: { open: boolean; onClose: () => void; title: string; children: ReactNode; width?: string }) {
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 backdrop-blur-sm sm:items-center sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={onClose}>
          <motion.div role="dialog" aria-modal="true" aria-label={title} variants={modal} initial="initial" animate="animate" exit="exit" onMouseDown={(e) => e.stopPropagation()}
            className={clsx('card-elev max-h-[90vh] w-full overflow-y-auto rounded-b-none p-6 sm:rounded-b-2xl', width)}>
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-lg font-semibold">{title}</h2>
              <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-graphite hover:text-ink"><X className="h-5 w-5" /></button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function Segmented<T extends string | number>({ value, onChange, options, className }: { value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; className?: string }) {
  return (
    <div role="tablist" className={clsx('relative inline-flex rounded-xl border border-line bg-graphite p-0.5', className)}>
      {options.map((o) => (
        <button key={String(o.value)} role="tab" aria-selected={o.value === value} onClick={() => onChange(o.value)}
          className={clsx('relative z-10 rounded-[10px] px-3 py-1.5 text-[13px] font-medium transition-colors', o.value === value ? 'text-ink' : 'text-muted hover:text-ink')}>
          {o.value === value && <motion.span layoutId={`seg-${options.map((x) => x.value).join('-')}`} className="absolute inset-0 -z-10 rounded-[10px] bg-elevated ring-1 ring-line" transition={{ type: 'spring', stiffness: 500, damping: 36 }} />}
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function SectionTitle({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div><h2 className="text-lg font-semibold tracking-tight">{title}</h2>{sub && <p className="mt-0.5 text-sm text-muted">{sub}</p>}</div>
      {right}
    </div>
  )
}

export function Stat({ label, children, sub }: { label: string; children: ReactNode; sub?: ReactNode }) {
  return (<div><div className="text-xs font-medium uppercase tracking-wider text-muted">{label}</div><div className="mt-1.5 text-2xl font-semibold tracking-tight">{children}</div>{sub && <div className="mt-1">{sub}</div>}</div>)
}
