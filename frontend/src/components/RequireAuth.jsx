import { Navigate, useLocation } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useAuth } from '../lib/auth.jsx'
import { Spinner } from './ui.jsx'

/** Redirects to sign-in when signed out. With `roles`, shows a "no access" panel for other roles. */
export default function RequireAuth({ roles, children }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <div className="p-10"><Spinner label="Restoring your session" /></div>
  if (!user) return <Navigate to="/signin" state={{ from: loc.pathname + loc.search }} replace />
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="glass mx-auto mt-10 max-w-md p-8 text-center">
        <ShieldAlert className="mx-auto h-8 w-8 text-primary" aria-hidden />
        <h1 className="mt-3 font-display text-xl font-bold text-heading">You don’t have access to this page</h1>
        <p className="muted mt-1 text-sm">Your role is {user.role.replace('_', ' ')}. Ask an admin if you need more access.</p>
      </div>
    )
  }
  return children
}
