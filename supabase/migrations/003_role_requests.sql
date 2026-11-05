-- Role approval workflow. Run this if you already ran 001 before it existed (safe to run twice).
create table if not exists role_requests (
  request_id text primary key,
  user_id text not null references users(user_id) on delete cascade,
  requested_role text not null check (requested_role in ('support_engineer','admin')),
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  reviewed_by text, created_at timestamptz not null default now(), reviewed_at timestamptz
);
alter table role_requests enable row level security;
notify pgrst, 'reload schema';
