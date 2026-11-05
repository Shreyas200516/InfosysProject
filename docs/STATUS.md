# Status, verification, and known issues

## What was verified, and how
Built in a sandbox that could not install FastAPI, ChromaDB, Vite, Tailwind or Framer Motion.

| Area | Verified | How |
|---|---|---|
| Ticket pipeline, agents, Jira/email mocks, storage, analytics, validation | Yes | 57 pytest tests passing (SQLite) |
| Sign-up, sign-in, tokens, password hashing, login lockout, role rules, employee ticket isolation | Yes | 27 of those tests: tampered/expired/forged tokens rejected, wrong password and unknown email give the same error, employees get 404 on others' tickets, password hash never appears in any response. Role approval: sign-up never grants a staff role, admins are emailed, approve/reject change the role (even on an already-issued token), a request can be decided only once, `make_admin` works |
| Team severity engine | Yes | their 8-case script: 8/8 |
| Frontend logic, auth flow, and role-based screens | Yes | driven in Chromium: 49/49 checks, no unexpected console errors. Covers sign-up validation, sign-in errors, session restore and sign-out, employee vs engineer vs admin navigation and blocked pages, the whole approval flow (request, pending banner, admin sees it with a count, approve, reject, role changes on next load), ticket submit with the live agent pipeline, status updates. Ran against the real backend code through stand-ins for React Router / Framer Motion / lucide |
| **FastAPI wiring** (routes, CORS, 422 handling) | **No** | `tests/test_api_http.py` is written and skips here. Run `pytest` after `pip install -r requirements.txt` |
| **ChromaDB + MiniLM retrieval** | **No** | needs the model download. Run `python -m scripts.build_index` then `python -m scripts.evaluate` |
| **Tailwind styling, Framer Motion animation, fonts** | **No** | never rendered. The palette was checked statically instead: all 14 hex values match the spec and every colour class resolves to a defined token. Expect to tweak spacing on first run |
| **Supabase backend** | **No** | SQL and `SupabaseRepository` written, not run against a project |
| **Real Jira, SMTP, Claude** | **No** | need credentials; code paths written, untested |

## Measured results (offline engine, local TF-IDF fallback retriever)
- Category model: **81% accuracy** on held-out phrasings (target was 90%). Training data is hand-written ticket phrasings plus weakly-labelled real tickets, so it is not a benchmark on human-labelled tickets. Security recall is weak for unseen wording, hence the rule override. See `backend/ml/models/category_report.json`.
- Retrieval: top-1 **81%** (16 queries), 0 of 5 off-topic queries falsely answered. Misses are paraphrases. Re-measure with ChromaDB.
- End to end: p50 ~6 ms with the offline engine (target under 5 s). A cloud LLM adds its own round trip.
- Of 16 evaluation tickets, 14 produced grounded, cited answers and 3 were escalated (security and critical-severity rules).

## Issues found in the inherited work (please read)
1. **Priority model accuracy.** The shipped `priority_model.joblib` reports **58.1%** accuracy (640 rows, 3 classes: high/medium/low) in its own metadata. The README claims 90.91% on 44 rows with 4 classes. These don't match. The 90.9% figure appears to describe the severity *rule engine* on a tiny sample, not the model. Severity levels (Critical/High/Medium/Low) come from the rule engine, so the "≥85% severity accuracy" target has not been measured on a real labelled set.
2. **No saved category model, wrong labels.** The team script classified `type` (Incident/Request/Problem/Change), not network/software/etc. Replaced by `ml/train_category.py`.
3. **Knowledge base had 8 articles**, mostly one sentence. 14 sample articles were added (clearly generic). **Replace them with your company's real documents**, and rerun `build_index`.
4. **Guardrail change.** Their grounding check required every step to share a keyword with the ticket, which rejected valid answers (for example "Contact IT support if it still fails"). Now it requires at least one step to match; per-step evidence and citation checks are unchanged. Marked in `rag_pipeline/grounding_guardrails.py`.
5. **One of their RAG tests fails** (`test_resolve_password_reset_ticket`) in an environment without ChromaDB, with or without my changes. It should pass on your machine once the index is built. Confirm.
6. **TF-IDF fallback scores are calibrated** so the retrieval threshold maps to the guardrail's 0.5 floor. This only applies when ChromaDB is unavailable.

## Not built
- Email verification and password reset. Anyone can register with any email address, and a forgotten password cannot be recovered yet.
- Supabase Auth. Sign-in is handled by the FastAPI backend with accounts in the `users` table. It works on SQLite and Supabase alike, but the token code is hand-written (standard HS256), so consider moving to Supabase Auth or a vetted JWT library before a public launch.
- Inbound email ingestion (tickets from a mailbox). The API accepts `source: "email"` but nothing polls a mailbox.
- Reading very large datasets from Supabase: list calls are capped at 5,000 rows for analytics.

## Security notes on sign-in
1. **Staff roles need admin approval.** Sign-up always creates an employee. The first admin is made with `python -m scripts.make_admin EMAIL` on the server. Email is not verified, so approve only people you recognise: a request shows the name and email they typed, not proof of who they are. A rejected person cannot ask again from the website (they would need a new email). Pending requests are not time-limited.
2. The session token is kept in the browser's `localStorage`, so a cross-site-scripting bug would expose it. An httpOnly cookie is safer if you later put the API and site on one domain.
3. The login lockout counter lives in memory: it resets when the API restarts and is not shared between several server processes.
4. Set a permanent `AUTH_SECRET`. Without it a random one is made on each start and everyone is signed out.
5. Never put the Supabase service-role key in the frontend or commit `.env`.
