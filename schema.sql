-- Run this once in your managed PostgreSQL database (e.g. Neon).
CREATE TABLE IF NOT EXISTS web_users (
  tg_user_id BIGINT PRIMARY KEY,
  display_name TEXT NOT NULL DEFAULT 'User',
  username TEXT NOT NULL DEFAULT '',
  balance NUMERIC(12,2) NOT NULL DEFAULT 0,
  deposited NUMERIC(12,2) NOT NULL DEFAULT 0,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Only legitimate digital-product / SMM orders belong here.
-- Do not copy Telegram account, OTP, login-code, or session records into these tables.
CREATE TABLE IF NOT EXISTS web_orders (
  id BIGSERIAL PRIMARY KEY,
  tg_user_id BIGINT NOT NULL REFERENCES web_users(tg_user_id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('digital', 'smm')),
  title TEXT NOT NULL,
  price NUMERIC(12,2) NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_web_orders_user_date ON web_orders(tg_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS web_payments (
  id BIGSERIAL PRIMARY KEY,
  tg_user_id BIGINT NOT NULL REFERENCES web_users(tg_user_id) ON DELETE CASCADE,
  payment_type TEXT NOT NULL DEFAULT 'recharge',
  amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  method TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_web_payments_user_date ON web_payments(tg_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS web_tickets (
  id BIGSERIAL PRIMARY KEY,
  tg_user_id BIGINT NOT NULL REFERENCES web_users(tg_user_id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  subject TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS web_ticket_messages (
  id BIGSERIAL PRIMARY KEY,
  ticket_id BIGINT NOT NULL REFERENCES web_tickets(id) ON DELETE CASCADE,
  tg_user_id BIGINT NOT NULL,
  sender TEXT NOT NULL CHECK (sender IN ('user', 'support')),
  body TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_web_ticket_messages_ticket ON web_ticket_messages(ticket_id, id);
