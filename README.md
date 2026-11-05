# SupportPilot

AI-powered IT support: a ticket comes in, SupportPilot classifies it, scores priority and severity, retrieves the right knowledge-base articles, writes a cited step-by-step fix, and either replies to the user or escalates to the right human team. Jira and email are updated along the way.

**Stack:** React 18 · Tailwind CSS · Framer Motion · FastAPI (Python) · Supabase (Postgres) · ChromaDB · Claude API.
**Look:** dark slate sidebar, white cards, orange primary actions, a warm panel for everything the AI does. Ticket status colours (Critical red, High orange, Medium yellow, Low blue, Resolved green) are separate from the brand colours.
**Scope built:** Milestone 1 (classification, priority, severity, ingestion API), Milestone 2 (knowledge base, semantic search, RAG, troubleshooting responses) and Milestone 3 (four-agent workflow, Jira, email). The dashboard and escalation views from Milestone 4 are also in.

## Run it

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # works as-is: SQLite + mock Jira/email + offline answer engine
python -c "import secrets;print(secrets.token_urlsafe(48))"   # paste the output as AUTH_SECRET in .env
python -m ml.train_category                            # trains + saves the category model
python -m scripts.build_index                          # builds the ChromaDB index (downloads all-MiniLM-L6-v2 once)
python -m scripts.seed_demo 40                         # optional: demo tickets for the dashboard
uvicorn app.main:app --reload --port 8000              # API docs at http://localhost:8000/docs

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev                                            # http://localhost:5173
```

The app runs with no keys at all. Add them in `backend/.env` to switch pieces on:

| To use | Set |
|---|---|
| Claude for answers | `ANTHROPIC_API_KEY` (model via `ANTHROPIC_MODEL_NAME`) |
| Supabase instead of SQLite | run `supabase/migrations/001_supportpilot_schema.sql` in your project, then `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. If you ran 001 earlier, also run `003_role_requests.sql` |
| Real Jira | `JIRA_MODE=real`, `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` |
| Real email | `EMAIL_MODE=smtp`, `SMTP_*` |

The Supabase service-role key stays on the server. The frontend only talks to the FastAPI backend.

## Accounts and roles

Open http://localhost:5173 and **create an account** (name, email, password, role). Then sign in with email and password.

| Role | Can do |
|---|---|
| Employee | Submit tickets, see only their own tickets and the AI's answer |
| Support engineer | Everything an employee can, plus all tickets, status changes, dashboard, AI Agent, Integrations, Analytics. Granted by an admin |
| Admin | Everything above, plus Settings and Approvals. The first one is created with `make_admin`; later ones by an existing admin |

- Tickets always use the signed-in account's name and email. Nobody can file as someone else.
- Passwords are hashed (PBKDF2-SHA256, salted). Sessions are signed tokens that expire after `TOKEN_TTL_HOURS` (12). Five failed sign-ins lock that email for 15 minutes.
- **Nobody can sign up as staff directly.** Everyone starts as an Employee. If someone picks Support engineer or Admin, the request is emailed to every admin and appears under **Approvals** in the sidebar. **Approve** grants the role immediately (on their next page load). **Reject** leaves them an employee. Each request is decided once, and both outcomes are emailed to the requester.
- **Create the first admin on the server**, because there is nobody to approve it yet: sign up on the website with the email you want to use, then run `python -m scripts.make_admin you@example.com` in `backend`. The website cannot do this, only someone with access to the server can.
- Seeded demo tickets belong to placeholder users who cannot sign in. Sign up as a support engineer to see them.

## How a ticket flows

`POST /api/v1/tickets` →
1. validate input, create `TKT-YYYYMMDD-XXXXXX`, upsert the requester
2. **category** (TF-IDF + Logistic Regression, plus a rule that never lets a security report be missed)
3. **priority** (team's model) and **severity** (team's rule engine: business impact, affected users, service tier) with SLA
4. **Diagnosis Agent** → **Knowledge Retrieval Agent** → **Resolution Agent** (team's RAG pipeline + grounding guardrails) → **Escalation Agent**
5. Jira issue created/updated, emails sent, every step stored in `agent_runs` and `activity_logs`
6. Status becomes `AI Resolved` or `Escalated`

Escalation happens when the answer isn't backed by the knowledge base, confidence is below 0.50, severity is Critical, the category is Security, or an agent fails. A ticket is never left stuck.

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/signup`, `/auth/login`, `GET /auth/me` | Create account (always as employee), sign in, current user |
| `GET /api/v1/admin/role-requests`, `POST .../{id}/approve`, `.../{id}/reject` | Admin only: decide staff-role requests |
| `POST /api/v1/tickets` | Submit and fully process a ticket (needs sign-in) |
| `POST /api/v1/tickets/analyze` | Live preview (nothing stored) |
| `GET /api/v1/tickets`, `/{id}`, `PATCH /{id}/status` | List, detail, update |
| `POST /api/v1/knowledge/search`, `GET /knowledge/articles` | Semantic search, article list |
| `POST /api/v1/rag/resolve` | RAG preview |
| `GET /api/v1/agents/runs`, `/integrations`, `/analytics/summary`, `/health` | Operations |

## Layout

```
backend/
  app/            FastAPI app: routers, agents, integrations, storage, pipeline
  rag_pipeline/   team (Person 3): RAG + guardrails      [edited: Claude provider, guardrail rule]
  severity_priority/  team: priority model + severity engine
  knowledge_base_preparation/, semantic_search/   team: KB prep, Chroma build/search
  ml/             category model training (Person 4 gap) + team's reference scripts and data
  data/knowledge_base_combined.csv   22 chunks: team's 8 + 14 added articles
  scripts/        build_index, seed_demo, evaluate     tests/   57 tests
frontend/         React app (Sign in, Sign up, Dashboard, Tickets, New ticket, Ticket detail, AI Agent, Integrations, Analytics, Settings)
supabase/migrations/   SQL for the 7 PDF tables + agent_runs + notifications
docs/             evaluation_results.json, STATUS.md
```

## Read this before the demo

See `docs/STATUS.md` for what was verified, what was not, and the issues found in the inherited work.
