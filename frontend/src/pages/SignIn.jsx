import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuth } from '../lib/auth.jsx'
import AuthShell from './AuthShell.jsx'

export default function SignIn() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [f, setF] = useState({ email: '', password: '' })
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  if (user) return <Navigate to={loc.state?.from || '/'} replace />

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setError(null)
    try { await login(f.email.trim(), f.password); nav(loc.state?.from || '/', { replace: true }) }
    catch (err) { setError(err.message); setBusy(false) }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to see your tickets." footer={<>New here? <Link to="/signup" className="font-semibold text-primary-hover hover:underline">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate={false}>
        <div><label className="label" htmlFor="email">Email</label><input id="email" type="email" required autoComplete="email" className="field" placeholder="name@gmail.com" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <div className="relative">
            <input id="password" type={show ? 'text' : 'password'} required autoComplete="current-password" className="field !pr-11" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
            <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-secondary hover:text-heading">{show ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}</button>
          </div>
        </div>
        {error && <p role="alert" className="rounded-xl border border-status-critical/30 bg-status-critical/5 p-3 text-sm text-status-critical">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? <><Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Signing in</> : 'Sign in'}</button>
      </form>
    </AuthShell>
  )
}
