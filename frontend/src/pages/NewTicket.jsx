import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, ChevronDown, Clock, BookOpen } from 'lucide-react'
import { api } from '../lib/api'
import { pct } from '../lib/format'
import { Badge, Card, PageHeader, useDebounced } from '../components/ui.jsx'
import { ScoreRing } from '../components/charts.jsx'
import { LEVEL_HEX, LEVEL_TONE } from '../lib/format'
import { useAuth } from '../lib/auth.jsx'

export default function NewTicket() {
  const nav = useNavigate()
  const { user } = useAuth()
  const [f, setF] = useState({ subject: '', description: '', business_impact: '', affected_users: '', service_criticality: '' })
  const [adv, setAdv] = useState(false)
  const [live, setLive] = useState({ state: 'idle', data: null, error: null })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }))

  const probe = useDebounced(JSON.stringify([f.subject, f.description, f.business_impact, f.affected_users, f.service_criticality]), 500)
  const ctl = useRef(null)
  useEffect(() => {
    if ((f.subject + f.description).trim().length < 8) { setLive({ state: 'idle', data: null, error: null }); return undefined }
    ctl.current?.abort()
    const c = new AbortController(); ctl.current = c
    setLive((s) => ({ ...s, state: 'loading' }))
    api.analyze({
      subject: f.subject, description: f.description, business_impact: f.business_impact || null,
      affected_users: f.affected_users ? Number(f.affected_users) : null, service_criticality: f.service_criticality || null,
    }, c.signal)
      .then((data) => setLive({ state: 'ready', data, error: null }))
      .catch((error) => { if (error.name !== 'AbortError') setLive({ state: 'error', data: null, error }) })
    return () => c.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [probe])

  async function submit(e) {
    e.preventDefault()
    setSubmitting(true); setError(null)
    try {
      const res = await api.createTicket({
        subject: f.subject, description: f.description, source: 'portal', business_impact: f.business_impact || null,
        affected_users: f.affected_users ? Number(f.affected_users) : null, service_criticality: f.service_criticality || null,
      })
      nav(`/tickets/${res.ticket.ticket_id}?new=1`)
    } catch (err) { setError(err); setSubmitting(false) }
  }

  const d = live.data
  return (
    <>
      <PageHeader title="New ticket" subtitle="Describe the problem. SupportPilot reads it as you type, so you can see how it will be triaged before you send it." />
      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
        <form onSubmit={submit} className="glass space-y-4 p-5 sm:p-6">
          <p className="rounded-xl bg-page px-3.5 py-2.5 text-sm text-secondary">Filing as <b className="text-heading">{user.name}</b> ({user.email}). Updates will be emailed here.</p>
          <div><label className="label" htmlFor="s">What’s wrong?</label><input id="s" className="field" required minLength={5} maxLength={200} value={f.subject} onChange={set('subject')} placeholder="e.g. VPN keeps disconnecting" /></div>
          <div><label className="label" htmlFor="x">Details</label><textarea id="x" className="field min-h-[130px]" required minLength={10} maxLength={5000} value={f.description} onChange={set('description')} placeholder="When did it start? Any error message? How many people are affected?" /></div>

          <button type="button" onClick={() => setAdv(!adv)} aria-expanded={adv} className="flex items-center gap-1.5 text-sm font-medium text-secondary hover:text-heading">
            <ChevronDown className={`h-4 w-4 transition-transform ${adv ? 'rotate-180' : ''}`} aria-hidden /> Business impact <span className="muted font-normal">(optional, otherwise inferred)</span>
          </button>
          <AnimatePresence initial={false}>
            {adv && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="grid gap-4 pb-1 sm:grid-cols-3">
                  <div><label className="label" htmlFor="bi">Impact</label>
                    <select id="bi" className="field" value={f.business_impact} onChange={set('business_impact')}><option value="">Infer</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>
                  <div><label className="label" htmlFor="au">People affected</label><input id="au" type="number" min="1" className="field" value={f.affected_users} onChange={set('affected_users')} placeholder="Infer" /></div>
                  <div><label className="label" htmlFor="sc">Service tier</label>
                    <select id="sc" className="field" value={f.service_criticality} onChange={set('service_criticality')}><option value="">Infer</option><option value="tier_1">Tier 1: mission-critical</option><option value="tier_2">Tier 2: business operations</option><option value="tier_3">Tier 3: productivity</option><option value="tier_4">Tier 4: non-essential</option></select></div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {error && <p role="alert" className="rounded-xl border border-status-critical/30 bg-status-critical/5 p-3 text-sm text-status-critical">{error.message}</p>}
          <div className="flex justify-end pt-1">
            <button className="btn-primary" disabled={submitting}>{submitting ? <><Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Sending</> : <><Send className="h-4 w-4" aria-hidden /> Submit ticket</>}</button>
          </div>
        </form>

        <div className="space-y-5">
          <Card ai title="Live triage" action={live.state === 'loading' && <Loader2 className="h-4 w-4 animate-spin text-secondary" aria-label="Analyzing" />}>
            {live.state === 'idle' && <p className="muted text-sm">Start typing and the category, priority, severity and likely fixes will show up here.</p>}
            {live.state === 'error' && <p role="alert" className="text-sm text-status-critical">{live.error.message}</p>}
            {d && (
              <motion.div key={d.classification.category + d.triage.severity} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }} className="space-y-5">
                <div className="flex flex-wrap items-center gap-5">
                  <ScoreRing value={d.triage.severity_score} label="severity" tone={LEVEL_HEX[d.triage.severity]} />
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="lav">{d.classification.category} · {pct(d.classification.confidence)}</Badge>
                      <Badge tone={LEVEL_TONE[d.triage.priority]}>{d.triage.priority} priority</Badge>
                      <Badge tone={LEVEL_TONE[d.triage.severity]}>{d.triage.severity} severity</Badge>
                    </div>
                    <p className="flex items-center gap-1.5 text-sm text-heading"><Clock className="h-3.5 w-3.5" aria-hidden /> First response within {d.triage.sla.response_time}; fix target {d.triage.sla.resolution_time}</p>
                  </div>
                </div>
                <p className="text-sm text-secondary">{d.triage.severity_reasoning}</p>
                <div>
                  <h3 className="mb-2 flex items-center gap-1.5 font-display text-sm font-semibold text-heading"><BookOpen className="h-4 w-4" aria-hidden /> Articles that may help</h3>
                  {d.articles.length === 0 && <p className="muted text-sm">Nothing in the knowledge base matches yet. A human engineer will take this one.</p>}
                  <ul className="space-y-2">
                    {d.articles.map((a) => (
                      <li key={a.doc_id} className="rounded-xl bg-white p-3 ring-1 ring-line">
                        <div className="flex items-center justify-between gap-2"><span className="font-medium text-heading">{a.title}</span><Badge tone="muted">{pct(a.relevance_score)} match</Badge></div>
                        <p className="muted mt-1 line-clamp-2 text-xs">{a.content.replace(/\n/g, ' ')}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              </motion.div>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
