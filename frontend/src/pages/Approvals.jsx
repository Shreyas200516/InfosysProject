import { useState } from 'react'
import { Check, X } from 'lucide-react'
import { api } from '../lib/api'
import { Badge, Card, Empty, ErrorBox, PageHeader, Spinner, useApi } from '../components/ui.jsx'
import { ROLE_LABEL, ROLE_REQUEST_TONE, fmtDate, timeAgo } from '../lib/format'

export default function Approvals() {
  const { data, error, loading, reload } = useApi(() => api.roleRequests('all'), [])
  const [busy, setBusy] = useState(null)
  const [actionError, setActionError] = useState(null)

  async function decide(req, approve) {
    setBusy(req.request_id); setActionError(null)
    try {
      await (approve ? api.approveRole(req.request_id) : api.rejectRole(req.request_id))
      window.dispatchEvent(new Event('sp:approvals-changed'))
      await reload()
    } catch (e) { setActionError(e.message); reload() } finally { setBusy(null) }
  }

  const items = data?.items || []
  const pending = items.filter((r) => r.status === 'pending')
  const done = items.filter((r) => r.status !== 'pending').slice(0, 20)

  return (
    <>
      <PageHeader title="Access requests" subtitle="People who signed up asking for support engineer or admin access. Until you approve, they only have employee access." />
      {error ? <ErrorBox error={error} onRetry={reload} /> : loading && !data ? <Spinner /> : (
        <div className="space-y-5">
          {actionError && <p role="alert" className="rounded-xl border border-status-critical/30 bg-status-critical/5 p-3 text-sm text-status-critical">{actionError}</p>}
          <Card title={`Waiting for a decision (${pending.length})`}>
            {pending.length === 0 ? <Empty title="No pending requests">New requests appear here and are emailed to every admin.</Empty> : (
              <ul className="divide-y divide-line">
                {pending.map((r) => (
                  <li key={r.request_id} data-testid="pending-request" className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-heading">{r.name}</p>
                      <p className="truncate text-sm text-secondary">{r.email} · asked for <b className="text-heading">{ROLE_LABEL[r.requested_role]}</b> · {timeAgo(r.created_at)}</p>
                    </div>
                    <div className="flex gap-2">
                      <button className="btn-primary !px-3 !py-2" disabled={busy === r.request_id} onClick={() => decide(r, true)} aria-label={`Approve ${r.name} as ${ROLE_LABEL[r.requested_role]}`}><Check className="h-4 w-4" aria-hidden /> Approve</button>
                      <button className="btn-ghost !px-3 !py-2" disabled={busy === r.request_id} onClick={() => decide(r, false)} aria-label={`Reject ${r.name}`}><X className="h-4 w-4" aria-hidden /> Reject</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          {done.length > 0 && (
            <Card title="Recently decided">
              <ul className="divide-y divide-line">
                {done.map((r) => (
                  <li key={r.request_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                    <span className="min-w-0 truncate"><b className="text-heading">{r.name}</b> <span className="text-secondary">({r.email}) · {ROLE_LABEL[r.requested_role]}</span></span>
                    <span className="flex items-center gap-2 text-secondary"><Badge tone={ROLE_REQUEST_TONE[r.status]}>{r.status === 'approved' ? 'Approved' : 'Rejected'}</Badge>{fmtDate(r.reviewed_at)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </>
  )
}
