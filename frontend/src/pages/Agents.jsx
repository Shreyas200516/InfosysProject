import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Stethoscope, BookOpen, Wand2, ArrowUpFromLine, Loader2, Play } from 'lucide-react'
import { api } from '../lib/api'
import { ms, parseStep, pct, summarizeRun, timeAgo } from '../lib/format'
import { Badge, Card, Empty, ErrorBox, PageHeader, Spinner, useApi } from '../components/ui.jsx'

const AGENTS = [
  { name: 'Diagnosis Agent', icon: Stethoscope, blurb: 'Reads the ticket, pulls out error codes and scope, and builds the search query.' },
  { name: 'Knowledge Retrieval Agent', icon: BookOpen, blurb: 'Finds the most relevant knowledge-base articles with semantic search.' },
  { name: 'Resolution Agent', icon: Wand2, blurb: 'Writes cited, step-by-step instructions using only what the articles say.' },
  { name: 'Escalation Agent', icon: ArrowUpFromLine, blurb: 'Decides when a person must take over and routes it to the right team.' },
]

function Playground() {
  const [f, setF] = useState({ subject: 'Outlook not syncing', description: 'Outlook has not received new emails on my laptop since Monday.' })
  const [state, setState] = useState({ loading: false, data: null, error: null })
  async function run(e) {
    e.preventDefault()
    setState({ loading: true, data: null, error: null })
    try { setState({ loading: false, data: await api.ragResolve(f), error: null }) } catch (error) { setState({ loading: false, data: null, error }) }
  }
  const d = state.data
  return (
    <Card ai title="Try the resolution engine" action={<span className="muted text-xs">Preview only. Nothing is saved.</span>}>
      <form onSubmit={run} className="grid gap-3 md:grid-cols-[1fr_1.4fr_auto] md:items-end">
        <div><label className="label" htmlFor="ps">Subject</label><input id="ps" className="field" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} required minLength={3} /></div>
        <div><label className="label" htmlFor="pd">Description</label><input id="pd" className="field" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></div>
        <button className="btn-primary" disabled={state.loading}>{state.loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />} Resolve</button>
      </form>
      {state.error && <p role="alert" className="mt-3 text-sm text-status-critical">{state.error.message}</p>}
      {d && (
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div>
            <div className="mb-3 flex flex-wrap gap-2">
              <Badge tone="lav">{d.category}</Badge>
              <Badge tone={d.grounding.is_grounded ? 'resolved' : 'medium'}>{d.grounding.is_grounded ? `Grounded · ${pct(d.grounding.confidence_score)}` : 'Not supported by the knowledge base'}</Badge>
              <Badge tone="muted">{d.provider} · {ms(d.processing_time_ms)}</Badge>
            </div>
            {d.step_by_step_steps.length ? (
              <ol className="space-y-2.5">{d.step_by_step_steps.map((s, i) => { const p = parseStep(s); return <li key={i} className="flex gap-2.5 text-sm"><span className="font-display font-bold text-secondary">{i + 1}.</span><div><span className="text-heading">{p.text}</span>{p.source && <span className="muted"> ({p.source})</span>}</div></li> })}</ol>
            ) : <p className="text-sm text-heading">{d.grounding.escalation_reason || 'No steps generated.'}</p>}
          </div>
          <div>
            <h3 className="mb-2 font-display text-sm font-semibold text-heading">Context given to the model</h3>
            <ul className="space-y-2">{d.retrieved_documents.map((x) => <li key={x.doc_id} className="rounded-xl bg-white p-3 text-sm ring-1 ring-line"><div className="flex justify-between gap-2"><span className="font-medium text-heading">{x.title}</span><span className="muted">{pct(x.relevance_score)}</span></div></li>)}
              {d.retrieved_documents.length === 0 && <li className="muted text-sm">No article passed the relevance threshold.</li>}</ul>
          </div>
        </div>
      )}
    </Card>
  )
}

export default function Agents() {
  const runs = useApi(() => api.agentRuns(60), [])
  const stats = useApi(() => api.analytics(), [])
  const lat = Object.fromEntries((stats.data?.agent_latency_ms || []).map((x) => [x.name, x]))
  return (
    <>
      <PageHeader title="AI Agent" subtitle="Four agents work every ticket in order. This is what each one does and what they just did." />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {AGENTS.map(({ name, icon: Icon, blurb }) => (
          <div key={name} className="glass p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ai ring-1 ring-orange-200"><Icon className="h-5 w-5 text-primary" aria-hidden /></div>
            <h3 className="mt-3 font-display text-lg font-semibold text-heading">{name}</h3>
            <p className="muted mt-1 text-sm">{blurb}</p>
            <p className="mt-3 text-xs text-secondary">{lat[name] ? `${lat[name].runs} runs · avg ${ms(lat[name].value)}` : 'No runs yet'}</p>
          </div>
        ))}
      </div>
      <div className="mt-5"><Playground /></div>
      <Card title="Recent agent activity" className="mt-5">
        {runs.error ? <ErrorBox error={runs.error} onRetry={runs.reload} /> : runs.loading && !runs.data ? <Spinner /> : runs.data.items.length === 0 ? <Empty title="No agent runs yet">Submit a ticket to see the agents work.</Empty> : (
          <ul className="divide-y divide-line">
            {runs.data.items.map((r) => (
              <li key={r.run_id} className="flex flex-wrap items-start gap-x-3 gap-y-1 py-3">
                <Badge tone={r.status === 'failed' ? 'bad' : 'lav'}>{r.agent_name}</Badge>
                <span className="min-w-0 flex-1 basis-64 text-sm text-heading">{summarizeRun(r)}</span>
                <Link to={`/tickets/${r.ticket_id}`} className="text-xs text-secondary hover:text-heading">{r.ticket_id}</Link>
                <span className="muted w-24 text-right text-xs">{ms(r.duration_ms)} · {timeAgo(r.started_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
