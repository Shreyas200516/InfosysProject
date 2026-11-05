const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

let token = null
export const setToken = (t) => { token = t }

async function request(path, { method = 'GET', body, signal, auth = true } = {}) {
  let res
  try {
    const headers = {}
    if (body) headers['Content-Type'] = 'application/json'
    if (token) headers.Authorization = `Bearer ${token}`
    res = await fetch(`${BASE}${path}`, { method, signal, headers, body: body ? JSON.stringify(body) : undefined })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new ApiError(`Cannot reach the API at ${BASE}. Start the backend with "uvicorn app.main:app --port 8000".`, 0)
  }
  if (res.status === 401 && auth && token) window.dispatchEvent(new Event('sp:unauthorized'))  // expired or revoked session
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = Array.isArray(j.detail) ? j.detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ') : j.detail || detail
    } catch { /* keep statusText */ }
    throw new ApiError(detail, res.status)
  }
  return res.json()
}

export const api = {
  base: BASE,
  signup: (b) => request('/api/v1/auth/signup', { method: 'POST', body: b, auth: false }),
  login: (b) => request('/api/v1/auth/login', { method: 'POST', body: b, auth: false }),
  me: () => request('/api/v1/auth/me'),
  roleRequests: (status = 'pending') => request(`/api/v1/admin/role-requests?status=${status}`),
  approveRole: (id) => request(`/api/v1/admin/role-requests/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
  rejectRole: (id) => request(`/api/v1/admin/role-requests/${encodeURIComponent(id)}/reject`, { method: 'POST' }),
  health: () => request('/api/v1/health'),
  analyze: (b, signal) => request('/api/v1/tickets/analyze', { method: 'POST', body: b, signal }),
  createTicket: (b) => request('/api/v1/tickets', { method: 'POST', body: b }),
  listTickets: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
    return request(`/api/v1/tickets${q ? `?${q}` : ''}`)
  },
  getTicket: (id) => request(`/api/v1/tickets/${encodeURIComponent(id)}`),
  setStatus: (id, status, note) => request(`/api/v1/tickets/${encodeURIComponent(id)}/status`, { method: 'PATCH', body: { status, note } }),
  articles: () => request('/api/v1/knowledge/articles'),
  search: (query, top_k = 3) => request('/api/v1/knowledge/search', { method: 'POST', body: { query, top_k } }),
  ragResolve: (b) => request('/api/v1/rag/resolve', { method: 'POST', body: b }),
  agentRuns: (limit = 60) => request(`/api/v1/agents/runs?limit=${limit}`),
  integrations: () => request('/api/v1/integrations'),
  analytics: () => request('/api/v1/analytics/summary'),
}
