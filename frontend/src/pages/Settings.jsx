import { api } from '../lib/api'
import { Badge, Card, ErrorBox, PageHeader, Spinner, useApi } from '../components/ui.jsx'

export default function Settings() {
  const { data, error, loading, reload } = useApi(() => api.health(), [])
  const rows = data && [
    ['Database', data.database], ['Knowledge search', data.retrieval], ['Language model', `${data.llm_provider} (${data.llm_model})`],
    ['Category model', data.category_model_loaded ? 'Loaded' : 'Missing: run python -m ml.train_category'], ['Jira', data.jira_mode], ['Email', data.email_mode],
  ]
  return (
    <>
      <PageHeader title="Settings" subtitle="Connection and runtime status. Change these in backend/.env and restart the API." />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="API connection">
          <p className="text-sm text-heading">Frontend is calling <code className="rounded bg-page px-1.5">{api.base}</code></p>
          <p className="muted mt-1 text-sm">Set <code className="rounded bg-page px-1.5">VITE_API_URL</code> in frontend/.env to change it.</p>
          <div className="mt-3">{error ? <Badge tone="bad">Unreachable</Badge> : <Badge tone="ok">Connected</Badge>}</div>
        </Card>
        <Card title="Runtime">
          {error ? <ErrorBox error={error} onRetry={reload} /> : loading && !data ? <Spinner /> : (
            <dl className="divide-y divide-line text-sm">{rows.map(([k, v]) => <div key={k} className="flex justify-between gap-4 py-2.5"><dt className="muted">{k}</dt><dd className="text-right text-heading">{v}</dd></div>)}</dl>
          )}
        </Card>
      </div>
    </>
  )
}
