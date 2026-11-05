import { api } from '../lib/api'
import { colorForName, ms, pct } from '../lib/format'
import { Card, ErrorBox, PageHeader, Spinner, Stat, useApi } from '../components/ui.jsx'
import { AreaChart, BarList, Donut } from '../components/charts.jsx'
import { Bot, ArrowUpFromLine, Timer, Gauge } from 'lucide-react'

export default function Analytics() {
  const { data: d, error, loading, reload } = useApi(() => api.analytics(), [])
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (loading && !d) return <Spinner />
  return (
    <>
      <PageHeader title="Analytics" subtitle="Volume, mix, and how well the agents are doing against the project targets." />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat index={0} icon={Bot} label="Automation rate" value={pct(d.totals.automation_rate)} hint="resolved without a person" />
        <Stat index={1} icon={ArrowUpFromLine} label="Escalation rate" value={pct(d.totals.escalation_rate)} />
        <Stat index={2} icon={Timer} label="Avg answer time" value={ms(d.avg_response_ms)} hint="target under 5s" />
        <Stat index={3} icon={Gauge} label="Avg confidence" value={pct(d.avg_confidence)} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card title="Ticket volume, last 14 days" className="xl:col-span-3"><AreaChart data={d.volume} height={230} /></Card>
        <Card title="Category"><Donut data={d.by_category} label="Tickets by category" /></Card>
        <Card title="Priority"><Donut data={d.by_priority} label="Tickets by priority" colorFor={colorForName} /></Card>
        <Card title="Severity"><Donut data={d.by_severity} label="Tickets by severity" colorFor={colorForName} /></Card>
        <Card title="Escalations by team">{d.escalations_by_team.length ? <BarList data={d.escalations_by_team} /> : <p className="muted text-sm">No escalations yet.</p>}</Card>
        <Card title="Agent speed (average)">{d.agent_latency_ms.length ? <BarList data={d.agent_latency_ms} unit="ms" color="#1E293B" /> : <p className="muted text-sm">No agent runs yet.</p>}</Card>
        <Card title="Status">{d.by_status.length ? <BarList data={d.by_status} color="#64748B" colorFor={colorForName} /> : <p className="muted text-sm">No tickets yet.</p>}</Card>
      </div>
    </>
  )
}
