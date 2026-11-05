import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import { useAuth } from './lib/auth.jsx'
import Dashboard from './pages/Dashboard.jsx'
import NewTicket from './pages/NewTicket.jsx'
import Tickets from './pages/Tickets.jsx'
import TicketDetail from './pages/TicketDetail.jsx'
import Agents from './pages/Agents.jsx'
import Integrations from './pages/Integrations.jsx'
import Analytics from './pages/Analytics.jsx'
import Settings from './pages/Settings.jsx'
import Approvals from './pages/Approvals.jsx'
import SignIn from './pages/SignIn.jsx'
import SignUp from './pages/SignUp.jsx'

const STAFF = ['support_engineer', 'admin']

/** Staff land on the dashboard; employees land on their own tickets. */
function Home() {
  const { user } = useAuth()
  return user.role === 'employee' ? <Navigate to="/tickets" replace /> : <Dashboard />
}

export default function App() {
  return (
    <Routes>
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signup" element={<SignUp />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Home />} />
        <Route path="tickets" element={<Tickets />} />
        <Route path="tickets/new" element={<NewTicket />} />
        <Route path="tickets/:id" element={<TicketDetail />} />
        <Route path="agents" element={<RequireAuth roles={STAFF}><Agents /></RequireAuth>} />
        <Route path="integrations" element={<RequireAuth roles={STAFF}><Integrations /></RequireAuth>} />
        <Route path="analytics" element={<RequireAuth roles={STAFF}><Analytics /></RequireAuth>} />
        <Route path="approvals" element={<RequireAuth roles={['admin']}><Approvals /></RequireAuth>} />
        <Route path="settings" element={<RequireAuth roles={['admin']}><Settings /></RequireAuth>} />
        <Route path="*" element={<div className="glass p-8 text-center"><p className="font-display text-xl text-heading">Page not found</p></div>} />
      </Route>
    </Routes>
  )
}
