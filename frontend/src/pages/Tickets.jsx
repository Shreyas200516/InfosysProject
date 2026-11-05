import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, Plus } from 'lucide-react'
import { api } from '../lib/api'
import { LEVEL_TONE, STATUS_TONE, isStaff, timeAgo } from '../lib/format'
import { useAuth } from '../lib/auth.jsx'
import { Badge, Card, Empty, ErrorBox, PageHeader, Spinner, useApi, useDebounced } from '../components/ui.jsx'

const STATUSES = ['', 'Processing', 'AI Resolved', 'Escalated', 'In Progress', 'Resolved', 'Closed']
const CATEGORIES = ['', 'Network', 'VPN', 'Email', 'Software', 'Hardware', 'Access', 'Security', 'General IT']
const PRIORITIES = ['', 'Critical', 'High', 'Medium', 'Low']

export default function Tickets() {
  const nav = useNavigate()
  const { user } = useAuth()
  const staff = isStaff(user)
  const [f, setF] = useState({ q: '', status: '', category: '', priority: '' })
  const q = useDebounced(f.q, 300)
  const { data, error, loading, reload } = useApi(() => api.listTickets({ q, status: f.status, category: f.category, priority: f.priority, limit: 200 }), [q, f.status, f.category, f.priority])
  const sel = (k, opts, label) => (
    <select aria-label={label} className="field !w-auto" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })}>
      {opts.map((o) => <option key={o} value={o}>{o || `All ${label.toLowerCase()}`}</option>)}
    </select>
  )
  return (
    <>
      <PageHeader title={staff ? 'Tickets' : 'My tickets'} subtitle={staff ? 'Every request, how it was triaged, and who is handling it.' : 'Your requests, how they were triaged, and where they stand.'}>
        <Link to="/tickets/new" className="btn-primary"><Plus className="h-4 w-4" aria-hidden /> New ticket</Link>
      </PageHeader>
      <Card pad={false}>
        <div className="flex flex-wrap gap-3 border-b border-line p-4">
          <div className="relative min-w-[14rem] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary" aria-hidden />
            <input aria-label="Search tickets" className="field !pl-9" placeholder="Search by subject or ticket ID" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
          </div>
          {sel('status', STATUSES, 'Statuses')}{sel('category', CATEGORIES, 'Categories')}{sel('priority', PRIORITIES, 'Priorities')}
        </div>
        {error ? <div className="p-4"><ErrorBox error={error} onRetry={reload} /></div> : loading && !data ? <Spinner /> : data.items.length === 0 ? (
          <Empty title={staff ? 'No tickets match' : 'No tickets yet'}>{staff ? 'Change the filters, or create a new ticket.' : 'When you submit a request it will show up here.'}</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="text-secondary"><tr><th className="px-4 py-3 font-medium">Ticket</th>{staff && <th className="px-3 py-3 font-medium">Requester</th>}<th className="px-3 py-3 font-medium">Category</th><th className="px-3 py-3 font-medium">Priority</th><th className="px-3 py-3 font-medium">Severity</th><th className="px-3 py-3 font-medium">Status</th>{staff && <th className="px-3 py-3 font-medium">Jira</th>}<th className="px-4 py-3 text-right font-medium">Created</th></tr></thead>
              <tbody>
                {data.items.map((x) => (
                  <tr key={x.ticket_id} tabIndex={0} onClick={() => nav(`/tickets/${x.ticket_id}`)} onKeyDown={(e) => e.key === 'Enter' && nav(`/tickets/${x.ticket_id}`)} className="cursor-pointer border-t border-line transition hover:bg-page focus-visible:bg-page">
                    <td className="max-w-[20rem] px-4 py-3"><div className="truncate font-medium text-heading">{x.subject}</div><div className="muted text-xs">{x.ticket_id}</div></td>
                    {staff && <td className="px-3 py-3 text-heading">{x.requester_name}</td>}
                    <td className="px-3 py-3"><Badge tone="lav">{x.category}</Badge></td>
                    <td className="px-3 py-3"><Badge tone={LEVEL_TONE[x.priority]}>{x.priority}</Badge></td>
                    <td className="px-3 py-3"><Badge tone={LEVEL_TONE[x.severity]}>{x.severity}</Badge></td>
                    <td className="px-3 py-3"><Badge tone={STATUS_TONE[x.status] || 'lav'}>{x.status}</Badge></td>
                    {staff && <td className="px-3 py-3 text-heading">{x.jira_key || '–'}</td>}
                    <td className="muted px-4 py-3 text-right">{timeAgo(x.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted border-t border-line px-4 py-3 text-xs">{data.total} ticket{data.total === 1 ? '' : 's'}</p>
          </div>
        )}
      </Card>
    </>
  )
}
