export const pct = (n) => `${Math.round((n || 0) * 100)}%`
export const ms = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}s` : `${Math.round(n || 0)}ms`)

export function timeAgo(iso) {
  if (!iso) return ''
  const s = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '')

/** Ticket status colours. Separate from the brand palette. */
export const LEVEL_HEX = { Critical: '#DC2626', High: '#F97316', Medium: '#EAB308', Low: '#2563EB' }
export const RESOLVED_HEX = '#16A34A'
/** Badge tones: critical | high | medium | low | resolved | neutral */
export const LEVEL_TONE = { Critical: 'critical', High: 'high', Medium: 'medium', Low: 'low' }
export const STATUS_TONE = {
  'AI Resolved': 'resolved', Resolved: 'resolved', Closed: 'neutral', Escalated: 'high', 'In Progress': 'neutral', Processing: 'neutral', Open: 'neutral', New: 'neutral',
}
/** Colour for a chart slice/bar given its label (severity, priority or status labels get their status colour). */
export const colorForName = (name) => LEVEL_HEX[name] || (/resolved|closed/i.test(name) ? RESOLVED_HEX : undefined)

export const ROLE_LABEL = { employee: 'Employee', support_engineer: 'Support engineer', admin: 'Admin' }
export const ROLE_REQUEST_TONE = { pending: 'medium', approved: 'resolved', rejected: 'critical' }
export const isStaff = (user) => !!user && (user.role === 'support_engineer' || user.role === 'admin')

/** "1. **Action**: text. [Source: X] [Evidence: ...]" -> { text, source } */
export function parseStep(raw = '') {
  const source = (raw.match(/\[Source:\s*([^\]]+)\]/i) || [])[1]
  const text = raw.replace(/\[Source:[^\]]*\]/gi, '').replace(/\[Evidence:[\s\S]*?\]\s*$/i, '').replace(/\*\*/g, '').trim()
  return { text, source }
}

export function summarizeRun(run) {
  const o = run.output || {}
  if (run.status === 'failed') return `Failed: ${o.error || 'unknown error'}`
  switch (run.agent_name) {
    case 'Diagnosis Agent': return o.summary || 'Diagnosed the ticket.'
    case 'Knowledge Retrieval Agent':
      return o.count ? `Found ${o.count} article${o.count > 1 ? 's' : ''}: ${(o.articles || []).map((a) => a.title).join(', ')}` : 'No relevant knowledge-base articles found.'
    case 'Resolution Agent':
      return o.grounded ? `Wrote ${o.steps} cited step${o.steps === 1 ? '' : 's'} (confidence ${pct(o.confidence)}).` : 'No verified resolution could be written from the knowledge base.'
    case 'Escalation Agent':
      return o.escalate ? `Escalate to ${o.team}. ${o.reason || ''}` : 'No escalation needed. Resolved automatically.'
    default: return ''
  }
}
