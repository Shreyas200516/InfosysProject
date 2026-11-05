import { Link } from 'react-router-dom'
import { Ticket, Bot, ArrowUpFromLine, Timer, Gauge, Plus } from 'lucide-react'
import { api } from '../lib/api'
import { LEVEL_TONE, STATUS_TONE, ms, pct, timeAgo } from '../lib/format'
import { Badge, Card, Empty, ErrorBox, PageHeader, Spinner, Stat, useApi } from '../components/ui.jsx'
import { AreaChart, Donut } from '../components/charts.jsx'

export default function Dashboard() {
  const a = useApi(() => api.analytics(), [])
  const t = useApi(() => api.listTickets({ limit: 6 }), [])
  if (a.error) return <ErrorBox error={a.error} onRetry={a.reload} />
  if (a.loading && !a.data) return <Spinner label="Loading dashboard" />
  const d = a.data
  const empty = d.totals.tickets === 0
  const stages = ['Open', 'In Progress', 'Resolved']
  const escMap = Object.fromEntries(d.escalation_status.map((e) => [e.name, e.value]))

  return (
    <>
      <PageHeader title="Dashboard" subtitle="How much of the support queue SupportPilot is handling, and what it handed to people.">
        <Link to="/tickets/new" className="btn-primary"><Plus className="h-4 w-4" aria-hidden /> New ticket</Link>
      </PageHeader>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat index={0} icon={Ticket} label="Tickets" value={d.totals.tickets} hint={`${d.totals.open} open`} />
        <Stat index={1} icon={Bot} label="Resolved by AI" value={pct(d.totals.automation_rate)} hint={`${d.totals.ai_resolved} tickets`} />
        <Stat index={2} icon={ArrowUpFromLine} label="Escalated" value={pct(d.totals.escalation_rate)} hint={`${d.totals.escalated} tickets`} />
        <Stat index={3} icon={Timer} label="Avg answer time" value={ms(d.avg_response_ms)} hint="target under 5s" />
        <Stat index={4} icon={Gauge} label="Avg confidence" value={pct(d.avg_confidence)} hint="of generated answers" />
      </div>

      {empty ? (
        <Card className="mt-5"><Empty title="No tickets yet">Submit a ticket, or run <code className="rounded bg-page px-1.5">python -m scripts.seed_demo</code> in the backend to load sample data.</Empty></Card>
      ) : (
        <div className="mt-5 grid gap-5 xl:grid-cols-3">
          <Card title="Ticket volume, last 14 days" className="xl:col-span-2"><AreaChart data={d.volume} /></Card>
          <Card title="By category"><Donut data={d.by_category} label="Tickets by category" /></Card>

          <Card title="Escalation workflow" className="xl:col-span-1">
            <div className="grid grid-cols-3 gap-2">
              {stages.map((s) => (
                <div key={s} className="rounded-xl bg-page p-3 text-center ring-1 ring-line">
                  <div className="font-display text-2xl font-bold text-heading">{escMap[s] || 0}</div>
                  <div className="muted text-xs">{s}</div>
                </div>
              ))}
            </div>
            <ul className="mt-4 space-y-2">
              {d.recent_escalations.slice(0, 4).map((e) => (
                <li key={e.escalation_id}><Link to={`/tickets/${e.ticket_id}`} className="flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-sm hover:bg-page"><span className="truncate text-heading">{e.assigned_team}</span><Badge tone={e.status === 'Resolved' ? 'ok' : e.status === 'In Progress' ? 'lav' : 'warn'}>{e.status}</Badge></Link></li>
              ))}
              {d.recent_escalations.length === 0 && <li className="muted text-sm">No escalations. Everything was resolved automatically.</li>}
            </ul>
          </Card>

          <Card title="Latest tickets" className="xl:col-span-2" action={<Link to="/tickets" className="text-sm text-secondary hover:text-heading">View all</Link>}>
            {t.loading && !t.data ? <Spinner /> : (
              <ul className="divide-y divide-line">
                {(t.data?.items || []).map((x) => (
                  <li key={x.ticket_id}>
                    <Link to={`/tickets/${x.ticket_id}`} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-2 py-3 hover:bg-page">
                      <span className="min-w-0 flex-1 truncate font-medium text-heading">{x.subject}</span>
                      <Badge tone="lav">{x.category}</Badge><Badge tone={LEVEL_TONE[x.priority]}>{x.priority}</Badge><Badge tone={STATUS_TONE[x.status] || 'lav'}>{x.status}</Badge>
                      <span className="muted w-16 text-right text-xs">{timeAgo(x.created_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </>
  )
}
