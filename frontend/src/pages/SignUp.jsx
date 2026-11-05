import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuth } from '../lib/auth.jsx'
import AuthShell from './AuthShell.jsx'

const ROLES = [
  { value: 'employee', label: 'Employee', help: 'Submit tickets and follow your own requests.' },
  { value: 'support_engineer', label: 'Support engineer', help: 'See all tickets, handle escalations, view analytics. Needs admin approval.' },
  { value: 'admin', label: 'Admin', help: 'Everything above, plus settings and approvals. Needs admin approval.' },
]

function passwordProblem(p) {
  if (p.length < 8) return 'Use at least 8 characters.'
  if (!/[A-Za-z]/.test(p) || !/\d/.test(p)) return 'Include at least one letter and one number.'
  return null
}

export default function SignUp() {
  const { user, signup } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ name: '', email: '', password: '', role: 'employee' })
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [touched, setTouched] = useState(false)
  if (user) return <Navigate to="/" replace />

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const problem = passwordProblem(f.password)
  const role = ROLES.find((r) => r.value === f.role)

  async function submit(e) {
    e.preventDefault()
    setTouched(true)
    if (problem) return
    setBusy(true); setError(null)
    try {
      await signup({ name: f.name.trim(), email: f.email.trim(), password: f.password, role: f.role })
      nav('/', { replace: true })
    } catch (err) { setError(err.message); setBusy(false) }
  }

  return (
    <AuthShell title="Create your account" subtitle="It takes under a minute." footer={<>Already have an account? <Link to="/signin" className="font-semibold text-primary-hover hover:underline">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="name">Name</label><input id="name" required minLength={2} maxLength={100} autoComplete="name" className="field" value={f.name} onChange={set('name')} /></div>
        <div><label className="label" htmlFor="email">Email</label><input id="email" type="email" required autoComplete="email" className="field" placeholder="name@gmail.com" value={f.email} onChange={set('email')} /></div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <div className="relative">
            <input id="password" type={show ? 'text' : 'password'} required autoComplete="new-password" aria-describedby="pw-hint" className="field !pr-11" value={f.password} onChange={set('password')} />
            <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-secondary hover:text-heading">{show ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}</button>
          </div>
          <p id="pw-hint" className={`mt-1.5 text-xs ${touched && problem ? 'text-status-critical' : 'text-secondary'}`}>{touched && problem ? problem : 'At least 8 characters, with a letter and a number.'}</p>
        </div>
        <div>
          <label className="label" htmlFor="role">Role</label>
          <select id="role" className="field" value={f.role} onChange={set('role')}>{ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select>
          <p className="mt-1.5 text-xs text-secondary">{role.help}</p>
        </div>
        {f.role !== 'employee' && (
          <p role="note" className="rounded-xl border border-line bg-ai p-3 text-sm text-heading">
            You can start right away as an <b>Employee</b>. An admin is notified of your request for <b>{role.label}</b> access and will approve or decline it. If it is declined, you stay an employee.
          </p>
        )}
        {error && <p role="alert" className="rounded-xl border border-status-critical/30 bg-status-critical/5 p-3 text-sm text-status-critical">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? <><Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Creating account</> : 'Create account'}</button>
      </form>
    </AuthShell>
  )
}
