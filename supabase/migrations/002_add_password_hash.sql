-- Only needed if you already ran 001 before sign-in/sign-up existed.
alter table users add column if not exists password_hash text;
