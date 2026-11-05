import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LayoutDashboard, Ticket, Bot, Plug, BarChart3, Settings, Plus, LogOut, UserCheck, Info } from 'lucide-react'
import { useAuth } from '../lib/auth.jsx'
import { api } from '../lib/api'
import { ROLE_LABEL } from '../lib/format'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true, roles: ['support_engineer', 'admin'] },
  { to: '/tickets', label: 'Tickets', icon: Ticket, roles: ['support_engineer', 'admin'], employeeLabel: 'My tickets', employee: true },
  { to: '/agents', label: 'AI Agent', icon: Bot, roles: ['support_engineer', 'admin'] },
  { to: '/integrations', label: 'Integrations', icon: Plug, roles: ['support_engineer', 'admin'] },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, roles: ['support_engineer', 'admin'] },
  { to: '/approvals', label: 'Approvals', icon: UserCheck, roles: ['admin'], badge: true },
  { to: '/settings', label: 'Settings', icon: Settings, roles: ['admin'] },
]

function navFor(user) {
  return NAV.filter((n) => n.roles.includes(user.role) || (user.role === 'employee' && n.employee))
    .map((n) => ({ ...n, label: user.role === 'employee' && n.employeeLabel ? n.employeeLabel : n.label }))
}

function Logo() {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
        <svg viewBox="0 0 32 32" className="h-5 w-5" aria-hidden><path d="M7 22l9-15 9 15h-6l-3-5-3 5z" fill="#FFFFFF" /></svg>
      </div>
      <span className="font-display text-xl font-bold tracking-tight text-white">SupportPilot</span>
    </div>
  )
}

function UserChip({ user, onLogout, dark }) {
  const initial = (user.name || '?').trim().charAt(0).toUpperCase()
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary font-display font-bold text-white" aria-hidden>{initial}</div>
      <div className="min-w-0 flex-1 leading-tight">
        <p className={`truncate text-sm font-semibold ${dark ? 'text-white' : 'text-heading'}`}>{user.name}</p>
        <p className={`truncate text-xs ${dark ? 'text-slate-400' : 'text-secondary'}`}>{ROLE_LABEL[user.role]}</p>
      </div>
      <button onClick={onLogout} aria-label="Sign out" title="Sign out" className={`rounded-lg p-2 transition ${dark ? 'text-slate-300 hover:bg-white/10 hover:text-white' : 'text-secondary hover:bg-page hover:text-heading'}`}><LogOut className="h-4 w-4" aria-hidden /></button>
    </div>
  )
}

const POLL_MS = 30000

// Admins: number of access requests waiting. Employees with a pending request: notice, refreshed until an admin decides.
function useAccessStatus(user, pendingRole, refresh) {
  const [pendingCount, setPendingCount] = useState(0)
  const [notice, setNotice] = useState(null)
  const hadPending = useRef(pendingRole)

  const loadCount = useCallback(() => {
    if (user.role !== 'admin') return
    api.roleRequests('pending').then((r) => setPendingCount(r.pending || 0)).catch(() => {})
  }, [user.role])

  useEffect(() => {
    loadCount()
    window.addEventListener('sp:approvals-changed', loadCount)
    const t = user.role === 'admin' ? setInterval(loadCount, POLL_MS) : null
    return () => { window.removeEventListener('sp:approvals-changed', loadCount); if (t) clearInterval(t) }
  }, [user.role, loadCount])

  useEffect(() => {
    if (!pendingRole) return undefined
    const t = setInterval(() => { refresh().catch(() => {}) }, POLL_MS)
    return () => clearInterval(t)
  }, [pendingRole, refresh])

  useEffect(() => {
    if (hadPending.current && !pendingRole) {
      setNotice(user.role === 'employee'
        ? 'Your request for extra access was declined. Your account stays an employee account.'
        : `Your request was approved. You are now ${ROLE_LABEL[user.role]}.`)
    }
    hadPending.current = pendingRole
  }, [pendingRole, user.role])

  return { pendingCount, notice, dismiss: () => setNotice(null) }
}

function AccessBanner({ pendingRole, notice, dismiss }) {
  if (!pendingRole && !notice) return null
  return (
    <div role="status" data-testid="access-banner" className="mb-5 flex items-start gap-3 rounded-2xl border border-line bg-ai p-4 text-sm text-heading">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
      <p className="flex-1">{pendingRole
        ? <>Your request for <b>{ROLE_LABEL[pendingRole]}</b> access is waiting for an admin. Until then you have employee access.</>
        : notice}</p>
      {!pendingRole && <button onClick={dismiss} className="text-secondary hover:text-heading" aria-label="Dismiss">Dismiss</button>}
    </div>
  )
}

export default function Layout() {
  const { user, logout, pendingRole, refresh } = useAuth()
  const nav = useNavigate()
  const items = navFor(user)
  const access = useAccessStatus(user, pendingRole, refresh)
  const signOut = () => { logout(); nav('/signin') }
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-sidebar p-4 lg:flex">
        <Logo />
        <Link to="/tickets/new" className="btn-primary mt-6"><Plus className="h-4 w-4" aria-hidden /> New ticket</Link>
        <nav className="mt-6 flex flex-col gap-1" aria-label="Main">
          {items.map(({ to, label, icon: Icon, end, badge }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors ${isActive ? 'text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`}>
              {({ isActive }) => (
                <>
                  {isActive && <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-xl bg-white/10" transition={{ type: 'spring', stiffness: 400, damping: 34 }} />}
                  {isActive && <span aria-hidden className="absolute left-0 top-2 h-[calc(100%-1rem)] w-1 rounded-full bg-primary" />}
                  <Icon className="relative h-[18px] w-[18px]" aria-hidden /><span className="relative">{label}</span>
                  {badge && access.pendingCount > 0 && <span data-testid="approvals-count" aria-label={`${access.pendingCount} pending`} className="relative ml-auto rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-white">{access.pendingCount}</span>}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-white/10 pt-4"><UserChip user={user} onLogout={signOut} dark /></div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="frost sticky top-0 z-20 flex items-center justify-between gap-3 border-x-0 border-t-0 px-4 py-3 lg:hidden">
          <span className="flex items-center gap-2 font-display text-lg font-bold text-heading"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary"><svg viewBox="0 0 32 32" className="h-4 w-4" aria-hidden><path d="M7 22l9-15 9 15h-6l-3-5-3 5z" fill="#fff" /></svg></span>SupportPilot</span>
          <div className="flex items-center gap-2">
            <Link to="/tickets/new" className="btn-primary !px-3 !py-2"><Plus className="h-4 w-4" aria-hidden /> New</Link>
            <button onClick={signOut} aria-label="Sign out" className="rounded-lg p-2 text-secondary hover:bg-page"><LogOut className="h-4 w-4" aria-hidden /></button>
          </div>
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b border-line bg-white p-1.5 lg:hidden" aria-label="Main">
          {items.map(({ to, label, end, badge }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-sidebar text-white' : 'text-secondary'}`}>{label}{badge && access.pendingCount > 0 ? ` (${access.pendingCount})` : ''}</NavLink>
          ))}
        </nav>
        <div className="frost sticky top-0 z-20 hidden items-center justify-end gap-3 border-x-0 border-t-0 px-8 py-3 lg:flex">
          <span className="text-sm text-secondary">Signed in as <b className="font-semibold text-heading">{user.email}</b></span>
        </div>
        <main className="mx-auto max-w-[1300px] p-4 sm:p-6 lg:p-8"><AccessBanner pendingRole={pendingRole} notice={access.notice} dismiss={access.dismiss} /><Outlet /></main>
      </div>
    </div>
  )
}
