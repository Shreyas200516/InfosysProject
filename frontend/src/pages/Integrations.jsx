import { Link } from 'react-router-dom'
import { GitBranch, Mail, Cpu, Database, Layers } from 'lucide-react'
import { api } from '../lib/api'
import { timeAgo } from '../lib/format'
import { Badge, Card, Empty, ErrorBox, PageHeader, Spinner, useApi } from '../components/ui.jsx'

function Tile({ icon: Icon, title, status, tone, children }) {
  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-ai ring-1 ring-orange-200"><Icon className="h-[18px] w-[18px] text-primary" aria-hidden /></div><h3 className="font-display text-lg font-semibold text-heading">{title}</h3></div>
        <Badge tone={tone}>{status}</Badge>
      </div>
      <div className="muted mt-3 text-sm">{children}</div>
    </div>
  )
}

export default function Integrations() {
  const { data, error, loading, reload } = useApi(() => api.integrations(), [])
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (loading && !data) return <Spinner />
  const { jira, email, llm, vector_store: vs, database: db } = data
  return (
    <>
      <PageHeader title="Integrations" subtitle="Where tickets are tracked, who gets email, and which models and stores power the answers." />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Tile icon={GitBranch} title="Jira" status={jira.mode === 'real' ? 'Connected' : 'Mock mode'} tone={jira.mode === 'real' ? 'resolved' : 'medium'}>Project {jira.project}. {jira.total} issue{jira.total === 1 ? '' : 's'} created. {jira.mode === 'mock' && 'Set JIRA_MODE=real in the backend .env to create real issues.'}</Tile>
        <Tile icon={Mail} title="Email" status={email.mode === 'smtp' ? 'SMTP' : 'Mock mode'} tone={email.mode === 'smtp' ? 'resolved' : 'medium'}>Sending as {email.from}. {email.total} message{email.total === 1 ? '' : 's'}. {email.mode === 'mock' && 'Messages are stored, not delivered.'}</Tile>
        <Tile icon={Cpu} title="Language model" status={llm.provider === 'offline' ? 'Offline engine' : llm.provider} tone={llm.provider === 'offline' ? 'medium' : 'resolved'}>{llm.model}. {llm.provider === 'offline' && 'Add ANTHROPIC_API_KEY to use Claude.'}</Tile>
        <Tile icon={Layers} title="Knowledge search" status={vs.mode === 'chromadb' ? 'ChromaDB' : 'Local fallback'} tone={vs.mode === 'chromadb' ? 'resolved' : 'medium'}>{vs.articles} articles indexed. {vs.mode !== 'chromadb' && 'Run python -m scripts.build_index to enable semantic search.'}</Tile>
        <Tile icon={Database} title="Database" status={db.backend === 'supabase' ? 'Supabase' : 'SQLite'} tone={db.backend === 'supabase' ? 'resolved' : 'medium'}>{db.backend === 'sqlite' ? 'Using a local file. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY for Postgres.' : 'Postgres on Supabase.'}</Tile>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Card title="Jira issues">
          {jira.items.length === 0 ? <Empty title="No issues yet" /> : <ul className="divide-y divide-line">{jira.items.map((j) => <li key={j.jira_id} className="flex items-center gap-3 py-2.5 text-sm"><b className="w-20 text-heading">{j.jira_issue_key}</b><Link to={`/tickets/${j.ticket_id}`} className="min-w-0 flex-1 truncate text-secondary hover:text-heading">{j.ticket_id}</Link><Badge tone={j.jira_status === 'Done' ? 'ok' : 'lav'}>{j.jira_status}</Badge><span className="muted w-14 text-right text-xs">{timeAgo(j.last_updated)}</span></li>)}</ul>}
        </Card>
        <Card title="Email outbox">
          {email.items.length === 0 ? <Empty title="No emails yet" /> : <ul className="divide-y divide-line">{email.items.map((m) => <li key={m.notification_id} className="py-2.5 text-sm"><div className="flex items-center justify-between gap-2"><span className="truncate font-medium text-heading">{m.subject}</span><Badge tone="muted">{m.status}</Badge></div><p className="muted text-xs">To {m.recipient} · {timeAgo(m.created_at)}</p></li>)}</ul>}
        </Card>
      </div>
    </>
  )
}
