"""
Aaditya Tg Store - Vercel Mini App API (Flask).

This file is the Python serverless entrypoint Vercel expects: it exports a
top-level `app` (a Flask WSGI application). It verifies the Telegram Mini App
`initData` on the server (HMAC-SHA256) and serves the read-only / safe subset of
the store used by `index.html`.

It intentionally does NOT expose Telegram account inventory, OTP retrieval,
login codes, session strings, or account/session delivery, and it never credits
a wallet from an unverified browser request.

Environment variables (set these in Vercel -> Project -> Settings -> Env Vars):
  BOT_TOKEN      - Telegram bot token (used to verify initData)
  DATABASE_URL   - PostgreSQL connection string (Neon / Supabase / etc.)
  BOT_USERNAME   - bot username without "@" (used by the "open" endpoint)
  SUPPORT_URL    - optional support link
  UPDATES_URL    - optional updates channel link
  CHANNEL_URL    - optional main channel link
"""

import os
import json
import time
import hmac
import hashlib
from urllib.parse import parse_qsl

from flask import Flask, request, jsonify, send_from_directory

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - psycopg is in requirements.txt
    psycopg = None
    dict_row = None

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()
BOT_USERNAME = (os.environ.get("BOT_USERNAME") or "").strip().lstrip("@")

SUPPORT_URL = (os.environ.get("SUPPORT_URL") or "https://t.me/AADITYAXOFFICAL").strip()
UPDATES_URL = (os.environ.get("UPDATES_URL") or "").strip()
CHANNEL_URL = (os.environ.get("CHANNEL_URL") or "").strip()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# Only legitimate digital-product / SMM tiles are advertised in the Mini App.
STORE_TILES = [
    {"id": "shop", "label": "Digital Shop"},
    {"id": "smm", "label": "Social Media Booster"},
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _conn():
    if psycopg is None:
        raise RuntimeError("psycopg is not installed")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def verify_init_data(init_data):
    """Validate Telegram WebApp initData and return the user dict (or None)."""
    if not init_data or not BOT_TOKEN:
        return None
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True, keep_blank_values=True))
    except Exception:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        return None

    # Reject stale initData (older than 24h).
    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except Exception:
        return None
    if auth_date and (time.time() - auth_date) > 86400:
        return None

    try:
        user = json.loads(pairs.get("user", "{}"))
    except Exception:
        return None
    if not isinstance(user, dict) or "id" not in user:
        return None
    return user


def _authed_user():
    return verify_init_data(request.headers.get("X-Init-Data", ""))


def _uid(user):
    try:
        return int(user["id"])
    except Exception:
        return None


def _ts(value):
    """Convert a DB timestamp to unix seconds for the frontend."""
    try:
        return int(value.timestamp())
    except Exception:
        return 0


def _ensure_user(cur, uid, name, username):
    cur.execute(
        """
        INSERT INTO web_users (tg_user_id, display_name, username)
        VALUES (%s, %s, %s)
        ON CONFLICT (tg_user_id) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            username     = EXCLUDED.username
        """,
        (uid, name or "User", username or ""),
    )


# --------------------------------------------------------------------------- #
# Endpoint handlers
# --------------------------------------------------------------------------- #
def ep_me(cur, uid, user):
    _ensure_user(cur, uid, user.get("first_name") or user.get("username"), user.get("username"))
    cur.execute("SELECT * FROM web_users WHERE tg_user_id = %s", (uid,))
    row = cur.fetchone() or {}
    return {
        "uid": str(uid),
        "name": row.get("display_name") or "User",
        "balance": float(row.get("balance") or 0),
        "deposited": float(row.get("deposited") or 0),
        "joined": row["joined_at"].isoformat() if row.get("joined_at") else "",
        "support": SUPPORT_URL,
        "updates": UPDATES_URL,
        "channel": CHANNEL_URL,
    }


def ep_orders(cur, uid, user):
    cur.execute(
        "SELECT * FROM web_orders WHERE tg_user_id = %s ORDER BY created_at DESC LIMIT 100",
        (uid,),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "id": r["id"],
            "kind": r.get("kind"),
            "name": r.get("title"),
            "country": r.get("title"),
            "service": r.get("title"),
            "price": float(r.get("price") or 0),
            "status": r.get("status"),
            "ts": _ts(r.get("created_at")),
        })
    return out


def ep_payments(cur, uid, user):
    cur.execute(
        "SELECT * FROM web_payments WHERE tg_user_id = %s ORDER BY created_at DESC LIMIT 100",
        (uid,),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "id": r["id"],
            "type": r.get("payment_type"),
            "amount": float(r.get("amount") or 0),
            "method": r.get("method"),
            "status": r.get("status"),
            "ts": _ts(r.get("created_at")),
        })
    return out


def ep_store(cur, uid, user):
    return {"tiles": STORE_TILES}


def ep_tickets(cur, uid, user):
    cur.execute(
        """
        SELECT t.id, t.category, t.subject, t.status, t.created_at,
               (SELECT COUNT(*) FROM web_ticket_messages m
                 WHERE m.ticket_id = t.id AND m.sender = 'support') AS replies,
               (SELECT COUNT(*) FROM web_ticket_messages m
                 WHERE m.ticket_id = t.id AND m.sender = 'support'
                   AND m.is_read = FALSE) AS unread
          FROM web_tickets t
         WHERE t.tg_user_id = %s
         ORDER BY t.created_at DESC
         LIMIT 100
        """,
        (uid,),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "id": r["id"],
            "category": r.get("category"),
            "subject": r.get("subject"),
            "status": r.get("status"),
            "replies": int(r.get("replies") or 0),
            "unread": int(r.get("unread") or 0),
            "ts": _ts(r.get("created_at")),
        })
    return out


def ep_ticket(cur, uid, user, arg):
    try:
        tid = int(arg)
    except Exception:
        return {"ok": False, "msg": "Invalid ticket id"}
    cur.execute(
        "SELECT * FROM web_tickets WHERE id = %s AND tg_user_id = %s", (tid, uid)
    )
    t = cur.fetchone()
    if not t:
        return {"ok": False, "msg": "Ticket not found"}
    cur.execute(
        "SELECT * FROM web_ticket_messages WHERE ticket_id = %s ORDER BY id ASC", (tid,)
    )
    messages = [
        {"from": m.get("sender"), "text": m.get("body"), "ts": _ts(m.get("created_at"))}
        for m in cur.fetchall()
    ]
    cur.execute(
        "UPDATE web_ticket_messages SET is_read = TRUE "
        "WHERE ticket_id = %s AND sender = 'support'",
        (tid,),
    )
    return {
        "id": t["id"],
        "category": t.get("category"),
        "subject": t.get("subject"),
        "status": t.get("status"),
        "ts": _ts(t.get("created_at")),
        "messages": messages,
    }


def ep_ticket_new(cur, uid, user):
    body = request.get_json(silent=True) or {}
    category = str(body.get("category") or "other")[:32]
    message = str(body.get("message") or "").strip()
    if not message:
        return {"ok": False, "msg": "Message is required"}
    subject = message[:60]
    cur.execute(
        "INSERT INTO web_tickets (tg_user_id, category, subject, status) "
        "VALUES (%s, %s, %s, 'open') RETURNING id",
        (uid, category, subject),
    )
    tid = cur.fetchone()["id"]
    cur.execute(
        "INSERT INTO web_ticket_messages (ticket_id, tg_user_id, sender, body) "
        "VALUES (%s, %s, 'user', %s)",
        (tid, uid, message),
    )
    return {"ok": True, "id": tid}


def ep_ticket_reply(cur, uid, user):
    body = request.get_json(silent=True) or {}
    try:
        tid = int(body.get("id"))
    except Exception:
        return {"ok": False, "msg": "Invalid ticket id"}
    message = str(body.get("message") or "").strip()
    if not message:
        return {"ok": False, "msg": "Message is required"}
    cur.execute(
        "SELECT id FROM web_tickets WHERE id = %s AND tg_user_id = %s", (tid, uid)
    )
    if not cur.fetchone():
        return {"ok": False, "msg": "Ticket not found"}
    cur.execute(
        "INSERT INTO web_ticket_messages (ticket_id, tg_user_id, sender, body) "
        "VALUES (%s, %s, 'user', %s)",
        (tid, uid, message),
    )
    cur.execute("UPDATE web_tickets SET status = 'open' WHERE id = %s", (tid,))
    return {"ok": True}


def ep_ticket_close(cur, uid, user):
    body = request.get_json(silent=True) or {}
    try:
        tid = int(body.get("id"))
    except Exception:
        return {"ok": False, "msg": "Invalid ticket id"}
    cur.execute(
        "UPDATE web_tickets SET status = 'closed' WHERE id = %s AND tg_user_id = %s",
        (tid, uid),
    )
    return {"ok": True}


def ep_open(cur, uid, user):
    url = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else ""
    return {"ok": True, "url": url}


# endpoint name -> handler
GET_ENDPOINTS = {
    "me": ep_me,
    "orders": ep_orders,
    "payments": ep_payments,
    "store": ep_store,
    "tickets": ep_tickets,
    "ticket": ep_ticket,
}
POST_ENDPOINTS = {
    "ticket_new": ep_ticket_new,
    "ticket_reply": ep_ticket_reply,
    "ticket_close": ep_ticket_close,
    "open": ep_open,
}


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def _resolve_path(p):
    """Return (endpoint, arg) from either ?__p=..., the path, or <path:p>."""
    raw = request.args.get("__p")
    if raw is None:
        raw = p or ""
        for pref in ("/api/index", "/api"):
            if raw.startswith(pref):
                raw = raw[len(pref):]
                break
    raw = (raw or "").strip("/")
    segs = raw.split("/") if raw else []
    endpoint = segs[0] if segs else ""
    arg = segs[1] if len(segs) > 1 else None
    return endpoint, arg


def _dispatch(p=""):
    endpoint, arg = _resolve_path(p)

    # Health / root of the API function.
    if not endpoint:
        return jsonify({
            "ok": True,
            "service": "Aaditya Tg Store Mini App API",
            "time": int(time.time()),
        })

    user = _authed_user()
    if not user:
        return jsonify({"ok": False, "msg": "Unauthorized (invalid initData)"}), 401
    uid = _uid(user)
    if uid is None:
        return jsonify({"ok": False, "msg": "Unauthorized (no user id)"}), 401

    method = request.method.upper()
    if method == "GET":
        handler = GET_ENDPOINTS.get(endpoint)
    else:
        handler = POST_ENDPOINTS.get(endpoint)

    if handler is None:
        return jsonify({"ok": False, "msg": f"Unknown endpoint: {endpoint}"}), 404

    try:
        with _conn() as conn, conn.cursor() as cur:
            if endpoint == "ticket":
                result = handler(cur, uid, user, arg)
            else:
                result = handler(cur, uid, user)
    except Exception as ex:  # noqa: BLE001
        app.logger.exception("API error on %s", endpoint)
        return jsonify({"ok": False, "msg": f"Server error: {ex}"}), 500

    if isinstance(result, dict) and result.get("ok") is False:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/index", methods=["GET", "POST"])
@app.route("/api/index/<path:p>", methods=["GET", "POST"])
@app.route("/api/<path:p>", methods=["GET", "POST"])
def api_route(p=""):
    return _dispatch(p)


@app.route("/")
def index_page():
    try:
        return send_from_directory(ROOT_DIR, "index.html")
    except Exception:
        return jsonify({"ok": True, "service": "Aaditya Tg Store Mini App API"})


@app.route("/health")
def health():
    return jsonify({"ok": True, "time": int(time.time())})


# Vercel's Python runtime looks for one of these top-level names.
application = app
handler = app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "3000")), debug=True)
