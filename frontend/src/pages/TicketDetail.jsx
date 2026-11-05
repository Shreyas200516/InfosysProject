import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BookOpen, Mail, GitBranch, History, CheckCircle2, ArrowUpFromLine, Clock, ExternalLink } from 'lucide-react'
import { api } from '../lib/api'
import { LEVEL_HEX, LEVEL_TONE, STATUS_TONE, fmtDate, isStaff, ms, parseStep, pct, timeAgo } from '../lib/format'
import { useAuth } from '../lib/auth.jsx'
import { Badge, Card, ErrorBox, Spinner, useApi } from '../components/ui.jsx'
import PipelineTimeline from '../components/PipelineTimeline.jsx'
import { ScoreRing } from '../components/charts.jsx'

export default function TicketDetail() {
  const { id } = useParams()
  const { user: me } = useAuth()
  const staff = isStaff(me)
  const [params, setParams] = useSearchParams()
  const { data, error, loading, reload } = useApi(() => api.getTicket(id), [id])
  const [done, setDone] = useState(params.get('new') !== '1')
  const [busy, setBusy] = useState(false)

  if (loading && !data) return <Spinner label="Loading ticket" />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const { ticket: t, user, response, escalation, jira, agent_runs: runs, activity, notifications } = data
  const live = params.get('new') === '1' && !done

  async function setStatus(status) {
    setBusy(true)
    try { await api.setStatus(id, status, 'Updated from the ticket page'); reload() } finally { setBusy(false) }
  }

  const steps = (response?.steps || []).map(parseStep)
  return (
    <div className="space-y-5">
      <div className="glass flex flex-wrap items-start justify-between gap-4 p-5 sm:p-6">
        <div className="min-w-0">
          <Link to="/tickets" className="muted text-sm hover:text-heading">All tickets</Link>
          <h1 className="mt-1 font-display text-2xl font-bold text-heading sm:text-3xl">{t.subject}</h1>
          <p className="muted mt-1 text-sm">{t.ticket_id} · {user?.name} ({user?.email}){user?.department ? ` · ${user.department}` : ''} · {fmtDate(t.created_at)}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone={STATUS_TONE[t.status] || 'lav'}>{t.status}</Badge>
            <Badge tone="lav">{t.category}</Badge>
            <Badge tone={LEVEL_TONE[t.priority]}>{t.priority} priority</Badge>
            <Badge tone={LEVEL_TONE[t.severity]}>{t.severity} severity</Badge>
            {staff && jira && <Badge tone="neutral"><GitBranch className="h-3 w-3" aria-hidden /> {jira.jira_issue_key} · {jira.jira_status}</Badge>}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <ScoreRing value={t.severity_score ?? 0} label="severity" tone={LEVEL_HEX[t.severity]} />
          <div className="text-sm text-heading"><p className="flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" aria-hidden /> Respond in {t.sla_response}</p><p className="muted">Resolve in {t.sla_resolution}</p></div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.25fr_1fr]">
        <div className="space-y-5">
          {live && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
              <Card ai title="SupportPilot is working on it"><PipelineTimeline runs={runs} live onDone={() => { setDone(true); setParams({}, { replace: true }) }} /></Card>
            </motion.div>
          )}

          {!live && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Card ai title={escalation ? 'Handed to a human' : 'Suggested resolution'}>
                {escalation && (
                  <div className="mb-4 rounded-xl border border-status-high/40 bg-white p-4 text-sm">
                    <p className="flex items-center gap-2 font-semibold text-primary-hover"><ArrowUpFromLine className="h-4 w-4" aria-hidden /> Escalated to {escalation.assigned_team}</p>
                    <p className="mt-1 text-heading">{escalation.escalation_reason}</p>
                    <p className="muted mt-1 text-xs">Escalation {escalation.status.toLowerCase()} · {timeAgo(escalation.created_at)}</p>
                  </div>
                )}
                {steps.length > 0 ? (
                  <>
                    {!escalation && <p className="mb-3 flex items-center gap-2 text-sm text-status-resolved"><CheckCircle2 className="h-4 w-4" aria-hidden /> Resolved automatically with {pct(response.confidence_score)} confidence</p>}
                    {escalation && <p className="muted mb-3 text-sm">Interim steps from the knowledge base, while the team picks it up:</p>}
                    <ol className="space-y-3">
                      {steps.map((s, i) => (
                        <motion.li key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }} className="flex gap-3">
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-white">{i + 1}</span>
                          <div><p className="text-[15px] text-heading">{s.text}</p>{s.source && <p className="muted mt-0.5 flex items-center gap-1 text-xs"><BookOpen className="h-3 w-3" aria-hidden /> {s.source}</p>}</div>
                        </motion.li>
                      ))}
                    </ol>
                  </>
                ) : (
                  <p className="text-sm text-heading">{response ? 'The knowledge base has no verified procedure for this issue, so no steps were generated.' : 'No resolution has been generated yet.'}</p>
                )}
                {response && <p className="muted mt-4 text-xs">Generated by {response.provider} ({response.model}) in {ms(response.processing_time_ms)}</p>}
              </Card>
            </motion.div>
          )}

          <Card title="Description"><p className="whitespace-pre-wrap text-[15px] text-heading">{t.description}</p></Card>
          {response?.retrieved?.length > 0 && !live && (
            <Card title="Knowledge used">
              <ul className="space-y-2">{response.retrieved.map((a, i) => <li key={i} className="flex items-center justify-between gap-3 rounded-xl bg-page px-3 py-2 ring-1 ring-line"><span className="text-heading">{a.title}</span><Badge tone="muted">{a.category} · {pct(a.score)}</Badge></li>)}</ul>
            </Card>
          )}
        </div>

        <div className="space-y-5">
          {!live && <Card ai title="Agent activity"><PipelineTimeline runs={runs} /></Card>}
          {staff && <Card title="Support actions">
            <div className="flex flex-wrap gap-2">
              <button className="btn-ghost" disabled={busy} onClick={() => setStatus('In Progress')}>Start work</button>
              <button className="btn-primary" disabled={busy} onClick={() => setStatus('Resolved')}>Mark resolved</button>
              <button className="btn-ghost" disabled={busy} onClick={() => setStatus('Closed')}>Close</button>
            </div>
          </Card>}
          <Card title="Emails sent">
            {notifications.length === 0 ? <p className="muted text-sm">No emails yet.</p> : (
              <ul className="space-y-2">{notifications.map((n) => (
                <li key={n.notification_id} className="rounded-xl bg-page p-3 ring-1 ring-line">
                  <p className="flex items-center gap-2 text-sm font-medium text-heading"><Mail className="h-3.5 w-3.5 shrink-0" aria-hidden /> <span className="truncate">{n.subject}</span></p>
                  <p className="muted mt-0.5 text-xs">To {n.recipient} · {n.status} · {timeAgo(n.created_at)}</p>
                </li>))}</ul>
            )}
          </Card>
          {staff && jira && (
            <Card title="Jira">
              <p className="flex items-center gap-2 text-sm text-heading"><GitBranch className="h-4 w-4" aria-hidden /> <b>{jira.jira_issue_key}</b> <Badge tone={jira.jira_status === 'Done' ? 'resolved' : 'neutral'}>{jira.jira_status}</Badge></p>
              <p className="muted mt-1 text-xs">{jira.mode === 'mock' ? 'Mock mode: no real Jira issue was created.' : <a href={jira.jira_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-heading">Open in Jira <ExternalLink className="h-3 w-3" aria-hidden /></a>}</p>
            </Card>
          )}
          {staff && <Card title="History">
            <ul className="space-y-2.5">
              {activity.map((a) => (
                <li key={a.log_id} className="flex items-start gap-2.5 text-sm"><History className="mt-0.5 h-3.5 w-3.5 shrink-0 text-secondary" aria-hidden /><div><span className="text-heading">{a.action.replace('agent:', '').replaceAll('_', ' ')}</span><span className="muted"> · {a.performed_by} · {timeAgo(a.timestamp)}</span></div></li>
              ))}
            </ul>
          </Card>}
        </div>
      </div>
    </div>
  )
}
