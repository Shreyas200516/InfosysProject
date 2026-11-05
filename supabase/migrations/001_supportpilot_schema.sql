-- SupportPilot schema (Supabase / Postgres). Run in the Supabase SQL editor, or `supabase db push`.
-- The 7 tables from the project PDF + agent_runs and notifications (needed for Milestone 3).
-- The FastAPI backend connects with the SERVICE ROLE key, so RLS is enabled with no public policies:
-- the anon key cannot read or write anything directly.

create table if not exists users (
  user_id text primary key,
  name text, email text unique not null, department text, password_hash text,
  role text not null default 'employee' check (role in ('employee','support_engineer','admin')),
  created_at timestamptz not null default now()
);

create table if not exists tickets (
  ticket_id text primary key,
  user_id text references users(user_id),
  subject text not null, description text not null, ticket_text text,
  category text, category_confidence real,
  priority text check (priority in ('Critical','High','Medium','Low')), priority_confidence real,
  severity text check (severity in ('Critical','High','Medium','Low')), severity_score integer,
  business_impact text, affected_users integer, service_tier text, sla_response text, sla_resolution text,
  status text not null default 'New', source text default 'portal', resolution_type text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), resolved_at timestamptz
);

create table if not exists ticket_responses (
  response_id text primary key,
  ticket_id text not null references tickets(ticket_id) on delete cascade,
  generated_response text, steps jsonb, sources jsonb, retrieved jsonb,
  confidence_score real, grounded boolean, provider text, model text, processing_time_ms real,
  generated_at timestamptz not null default now()
);

create table if not exists knowledge_base (
  article_id text primary key, title text, content text, category text, source text, embedding_id text,
  created_at timestamptz not null default now()
);

create table if not exists escalations (
  escalation_id text primary key,
  ticket_id text not null references tickets(ticket_id) on delete cascade,
  assigned_team text, escalation_reason text, status text not null default 'Open', priority text,
  created_at timestamptz not null default now()
);

create table if not exists jira_tickets (
  jira_id text primary key,
  ticket_id text not null references tickets(ticket_id) on delete cascade,
  jira_issue_key text, jira_status text, jira_url text, mode text,
  last_updated timestamptz not null default now()
);

create table if not exists activity_logs (
  log_id text primary key,
  ticket_id text references tickets(ticket_id) on delete cascade,
  action text, performed_by text, details jsonb,
  "timestamp" timestamptz not null default now()
);

create table if not exists agent_runs (
  run_id text primary key,
  ticket_id text references tickets(ticket_id) on delete cascade,
  agent_name text, status text, input jsonb, output jsonb, duration_ms real,
  started_at timestamptz not null default now()
);

create table if not exists role_requests (
  request_id text primary key,
  user_id text not null references users(user_id) on delete cascade,
  requested_role text not null check (requested_role in ('support_engineer','admin')),
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  reviewed_by text, created_at timestamptz not null default now(), reviewed_at timestamptz
);

create table if not exists notifications (
  notification_id text primary key,
  ticket_id text references tickets(ticket_id) on delete cascade,
  recipient text, subject text, body text, channel text, status text,
  created_at timestamptz not null default now()
);

create index if not exists idx_tickets_status on tickets(status);
create index if not exists idx_tickets_created on tickets(created_at desc);
create index if not exists idx_tickets_category on tickets(category);
create index if not exists idx_responses_ticket on ticket_responses(ticket_id);
create index if not exists idx_escalations_ticket on escalations(ticket_id);
create index if not exists idx_logs_ticket on activity_logs(ticket_id, "timestamp");
create index if not exists idx_runs_ticket on agent_runs(ticket_id, started_at);

alter table users enable row level security;
alter table tickets enable row level security;
alter table ticket_responses enable row level security;
alter table knowledge_base enable row level security;
alter table escalations enable row level security;
alter table jira_tickets enable row level security;
alter table activity_logs enable row level security;
alter table agent_runs enable row level security;
alter table notifications enable row level security;
alter table role_requests enable row level security;
