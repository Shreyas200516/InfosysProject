import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Inbox } from 'lucide-react'

// dot = the exact status colour from the palette; the pill itself is a light tint with dark text so it stays readable.
const TONES = {
  critical: { dot: '#DC2626', cls: 'bg-status-critical/10 ring-status-critical/30 text-heading' },
  high: { dot: '#F97316', cls: 'bg-status-high/10 ring-status-high/30 text-heading' },
  medium: { dot: '#EAB308', cls: 'bg-status-medium/15 ring-status-medium/40 text-heading' },
  low: { dot: '#2563EB', cls: 'bg-status-low/10 ring-status-low/30 text-heading' },
  resolved: { dot: '#16A34A', cls: 'bg-status-resolved/10 ring-status-resolved/30 text-heading' },
  neutral: { dot: null, cls: 'bg-page ring-line text-secondary' },
}
const ALIASES = { ok: 'resolved', warn: 'high', bad: 'critical', lav: 'neutral', muted: 'neutral' }

export function Badge({ tone = 'neutral', children, className = '' }) {
  const t = TONES[ALIASES[tone] || tone] || TONES.neutral
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${t.cls} ${className}`}>
      {t.dot && <i aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: t.dot }} />}
      {children}
    </span>
  )
}

export function Card({ title, action, children, className = '', pad = true, ai = false }) {
  return (
    <section className={`${ai ? 'ai-panel' : 'glass'} ${pad ? 'p-5' : ''} ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="font-display text-lg font-semibold text-heading">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight text-heading sm:text-[2.1rem]">{title}</h1>
        {subtitle && <p className="muted mt-1 max-w-2xl text-[15px]">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

export function Stat({ label, value, hint, icon: Icon, index = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05, duration: 0.35 }} className="glass p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-secondary">{label}</span>
        {Icon && <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ai"><Icon className="h-4 w-4 text-primary" aria-hidden /></span>}
      </div>
      <div className="mt-2 font-display text-3xl font-bold text-heading">{value}</div>
      {hint && <div className="muted mt-1 text-xs">{hint}</div>}
    </motion.div>
  )
}

export function Spinner({ label = 'Loading' }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-secondary">
      <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden /> <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div role="alert" className="rounded-2xl border border-status-critical/30 bg-status-critical/5 p-4 text-sm">
      <p className="font-semibold text-status-critical">Something went wrong</p>
      <p className="mt-1 text-heading">{error.message || String(error)}</p>
      {onRetry && <button onClick={onRetry} className="btn-ghost mt-3">Try again</button>}
    </div>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <Inbox className="h-7 w-7 text-secondary/70" aria-hidden />
      <p className="font-display text-base font-semibold text-heading">{title}</p>
      {children && <p className="muted max-w-sm text-sm">{children}</p>}
    </div>
  )
}

/** Tiny data hook: { data, error, loading, reload }. */
export function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((error) => alive && setState({ data: null, error, loading: false }))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { ...state, reload: () => setTick((t) => t + 1) }
}

export function useDebounced(value, delay = 450) {
  const [v, setV] = useState(value)
  useEffect(() => { const t = setTimeout(() => setV(value), delay); return () => clearTimeout(t) }, [value, delay])
  return v
}
