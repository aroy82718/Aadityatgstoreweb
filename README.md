# Aaditya Tg Store — Vercel Mini App API (safe subset)

This package keeps the supplied Mini App layout, and adds a Vercel Python API for:
- Telegram Mini App `initData` verification (server-side HMAC + auth_date check)
- Profile display
- Legitimate digital-product / SMM order history (separate `web_orders` table)
- Payment history (read-only)
- Support tickets and replies
- Opening the Telegram bot from the Mini App

It intentionally does **not** expose Telegram account inventory, OTP retrieval, login codes,
session strings, or account/session delivery. It does not credit wallet balances from an
unverified browser request.

## Files
- `index.html` — existing UI with account/OTP stock tiles removed; styling retained
- `api/index.py` — Vercel serverless API
- `schema.sql` — PostgreSQL schema
- `vercel.json` — rewrites `/api/*` to the Python function
- `requirements.txt` — PostgreSQL driver

## Deploy
1. Create a managed PostgreSQL database (Neon or another PostgreSQL provider).
2. Run `schema.sql` once in that database's SQL editor.
3. Upload the contents of this folder to the root of your GitHub repo. Keep `index.html` at the root.
4. Redeploy the Vercel project.
5. In Vercel → Project → Settings → Environment Variables, add:
   - `DATABASE_URL` = PostgreSQL connection string (use SSL-enabled URL)
   - `BOT_TOKEN` = a newly rotated Telegram bot token
   - `BOT_USERNAME` = bot username without `@`
6. Redeploy after adding environment variables.

## Important integration limitation
Your uploaded Telethon bot uses a local SQLite database (`otp_bot_final.db`) and runs a
continuous Telethon connection. Vercel serverless functions cannot run that long-lived
process, and this API's PostgreSQL tables are not automatically synchronized with that
SQLite database. Therefore this package makes the Mini App API deployable, but it does not
make the existing Telethon bot run on Vercel or sync its existing wallet/orders by itself.
A separate safe bot worker and explicit sync for digital-product/SMM records are still
needed. Do not use a local SQLite file as Vercel persistent storage.

## Security
The previously uploaded source contained hard-coded credentials. Revoke/rotate the bot
token and any exposed API/app passwords before deployment. Store all secrets only in
Vercel environment variables. Never commit `.env` or database connection strings.
