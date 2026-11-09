import os
import sqlite3
import re
import asyncio
import time
import logging
import csv
import zipfile
import shutil
import sys
import unicodedata
import html
import imaplib
import email
import urllib.request
import urllib.error
import json
import ssl
import hashlib
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

from telethon import TelegramClient, events, Button

# ================= GLOBAL BUTTON STYLE (MIXED SMALL-CAPS + ICONS) =================
# Every Telegram button label is rendered in a premium mixed font:
#   "Aditya"  ->  "Aᴀᴅɪᴛʏᴀ"
# Capital letters stay normal, lowercase letters become Unicode small-caps.
# Numbers, symbols, Devanagari and existing fancy text are left untouched.
# Buttons also carry a Telegram custom-emoji icon (icon_custom_emoji_id) and
# no longer use coloured backgrounds ("style").
_ORIGINAL_BUTTON = Button

_SMALL_CAPS = {
    'a': '\u1d00', 'b': '\u0299', 'c': '\u1d04', 'd': '\u1d05', 'e': '\u1d07',
    'f': '\ua730', 'g': '\u0262', 'h': '\u029c', 'i': '\u026a', 'j': '\u1d0a',
    'k': '\u1d0b', 'l': '\u029f', 'm': '\u1d0d', 'n': '\u0274', 'o': '\u1d0f',
    'p': '\u1d18', 'q': '\u01eb', 'r': '\u0280', 's': '\ua731', 't': '\u1d1b',
    'u': '\u1d1c', 'v': '\u1d20', 'w': '\u1d21', 'x': 'x', 'y': '\u028f',
    'z': '\u1d22',
}


def _button_font(text):
  """Convert lowercase ASCII letters to Unicode small-caps (Aᴀᴅɪᴛʏᴀ).

  Fancy Unicode alphabets (e.g. 𝕋𝕂 𝔸ℂℂ) are first normalised to plain ASCII so
  the whole bot uses one consistent mixed font.
  """
  text = unicodedata.normalize('NFKC', str(text))
  return ''.join(_SMALL_CAPS.get(ch, ch) if 'a' <= ch <= 'z' else ch for ch in text)


# ---- Custom emoji icons for buttons -------------------------------------------
# Telegram renders a custom emoji next to the button label when the button
# carries an icon_custom_emoji_id. Exact labels win; otherwise a keyword match
# is used so every button in the bot gets a fitting icon automatically.
BUTTON_ICONS = {
  "profile": "5832281029204775089",
  "refer": "5834807908788867114",
  "store": "5834918366757786311",
  "tk acc": "5832418158920602346",
  "tg acc": "5832418158920602346",
  "server 2 [ manually added ]": "5832418158920602346",
  "manual acc": "5832418158920602346",
  "smm": "5834694603256632485",
  "tk acccount": "5832418158920602346",
  "add funds": "5834557460655904825",
  "deposit funds": "5834557460655904825",
  "orders history": "5834617968155168912",
  "my orders": "5834617968155168912",
  "refill": "5834807281723642144",
  "redeem code": "5832411746534429224",
  "redeem codes": "5832411746534429224",
  "selling logs": "5834519235446968809",
  "support": "5834461137424356807",
  "updates": "5834588100952594301",
  "server 1 [cheap account]": "5832269497217585375",
  "digital shop": "5834918366757786311",
  "shop": "5834918366757786311",
  "back to shop": "5834918366757786311",
  "social media services": "5834694603256632485",
  "back to main": "5832249985181160265",
  "back to main menu": "5832249985181160265",
  "back": "5832249985181160265",
  "back to admin": "5832249985181160265",
  "back to store": "5834918366757786311",
  "back to countries": "5832249985181160265",
  "back to categories": "5832249985181160265",
  "back to details": "5832249985181160265",
  "back to digital shop": "5834918366757786311",
  "back to payment methods": "5834557460655904825",
  "back to profile": "5832281029204775089",
  "back to servers apis": "5832538679997895284",
  "servers apis": "5832538679997895284",
  "smm api": "5832538679997895284",
  "refresh": "5834807281723642144",
  "try again": "5834807281723642144",
  "check again": "5834807281723642144",
  "generate qr again": "5834807281723642144",
  "get code": "5832432319427776896",
  "check code": "5832432319427776896",
  "get otp again": "5832432319427776896",
  "my numbers": "5834694603256632485",
  "buy a number": "5834918366757786311",
  "buy now": "5834918366757786311",
  "yes, buy now": "5834918366757786311",
  "buy single": "5834918366757786311",
  "buy bulk": "5834918366757786311",
  "prev": "5834792099014251507",
  "next": "5834699366375362698",
  "cancel": "5834870091325378855",
  "no, cancel": "5834870091325378855",
  "confirm": "5834600569242654097",
  "yes": "5834600569242654097",
  "delete": "5834870091325378855",
  "remove admin": "5834870091325378855",
  "remove channel": "5834870091325378855",
  "remove code": "5834870091325378855",
  "remove product": "5834870091325378855",
  "remove category": "5834870091325378855",
  "reject": "5834870091325378855",
  "verify payment": "5834600569242654097",
  "verify joined": "5834600569242654097",
  "add admin": "5834812242410869159",
  "edit admin": "5834812242410869159",
  "manage admins": "5834812242410869159",
  "user info": "5834812242410869159",
  "ban user": "5834870091325378855",
  "change balance": "5832530897517154496",
  "statistics": "5834519235446968809",
  "status": "5834519235446968809",
  "accept": "5834600569242654097",
  "choose year": "5832625820589363805",
  "set profit margin": "5832530897517154496",
  "settings": "5832712733547564784",
  "payments history": "5834519235446968809",
  "broadcast": "5834588100952594301",
  "add channel": "5832538679997895284",
  "channels": "5832538679997895284",
  "payment methods": "5834557460655904825",
  "upi manual": "5834557460655904825",
  "usdt manual": "5834557460655904825",
  "set usdt address & network": "5834557460655904825",
  "send screenshot": "5832705019786302198",
  "fampay automatic": "5834557460655904825",
  "fampay / imap": "5834557460655904825",
  "configure imap (gmail)": "5834557460655904825",
  "set manual upi & name": "5834557460655904825",
  "set fampay upi & name": "5834557460655904825",
  "change manual upi & name": "5834557460655904825",
  "change fampay upi & name": "5834557460655904825",
  "change logs channel": "5834886399316201457",
  "support channel": "5834461137424356807",
  "support user": "5834461137424356807",
  "update welcome photo": "5832705019786302198",
  "backup users": "5834886399316201457",
  "backup": "5834886399316201457",
  "restore": "5834807281723642144",
  "restore users": "5834807281723642144",
  "discount": "5832530897517154496",
  "usdt rate": "5832530897517154496",
  "auto price": "5832530897517154496",
  "set common price": "5832530897517154496",
  "edit common price (all years)": "5832530897517154496",
  "add product": "5834918366757786311",
  "add service": "5834918366757786311",
  "add single acc": "5834918366757786311",
  "bulk add": "5834918366757786311",
  "add zip": "5834886399316201457",
  "manage stock": "5834886399316201457",
  "manage": "5832712733547564784",
  "categories": "5834886399316201457",
  "create category": "5834886399316201457",
  "add custom country": "5832538679997895284",
  "edit country name": "5832538679997895284",
  "create code": "5832411746534429224",
  "test again": "5834807281723642144",
  "finish & logout": "5834791785481638087",
  "back to categories": "5832249985181160265",
  # --- Server 2 [ WhatsApp Accounts ] + Function Management additions ---
  "server 2 [ whatsapp accounts ]": "5832418158920602346",
  "server 3 [ manually added accounts ]": "5832418158920602346",
  "server 3 [manually added accounts]": "5832418158920602346",
  "manually added accounts": "5832418158920602346",
  "server 2 [whatsapp accounts]": "5832418158920602346",
  "whatsapp": "5832418158920602346",
  "whatsapp accounts": "5832418158920602346",
  "buy whatsapp number": "5834557460655904825",
  "buy for": "5834557460655904825",
  "function management": "5832712733547564784",
  "provider balance": "5834557460655904825",
  "home": "5832249985181160265",
  "countries": "5834918366757786311",
  "country": "5834918366757786311",
  "retry": "5834807281723642144",
  "noop": "5834699366375362698",
}

# Premium icons already used by the bot (confirm / cancel) for ON/OFF + selected marks.
_ICON_OK = "5834600569242654097"
_ICON_NO = "5834870091325378855"

_BUTTON_KEYWORD_ICONS = [
  ("back", "5832249985181160265"),
  ("cancel", "5834870091325378855"),
  ("remove", "5834870091325378855"),
  ("delete", "5834870091325378855"),
  ("reject", "5834870091325378855"),
  ("buy", "5834918366757786311"),
  ("add funds", "5834557460655904825"),
  ("deposit", "5834557460655904825"),
  ("balance", "5832530897517154496"),
  ("price", "5832530897517154496"),
  ("stock", "5834886399316201457"),
  ("code", "5832432319427776896"),
  ("otp", "5832432319427776896"),
  ("number", "5834694603256632485"),
  ("order", "5834617968155168912"),
  ("profile", "5832281029204775089"),
  ("admin", "5834812242410869159"),
  ("user", "5834812242410869159"),
  ("channel", "5832538679997895284"),
  ("api", "5832538679997895284"),
  ("test", "5834807281723642144"),
  ("refresh", "5834807281723642144"),
  ("stats", "5834519235446968809"),
  ("accept", "5834600569242654097"),
  ("year", "5832625820589363805"),
  ("profit", "5832530897517154496"),
  ("margin", "5832530897517154496"),
  ("setting", "5832712733547564784"),
  ("del:", "5834870091325378855"),
  ("edit:", "5832712733547564784"),
  ("price", "5832530897517154496"),
]


def _button_icon_id(text):
  """Return the custom-emoji id that should decorate a button label."""
  raw = unicodedata.normalize('NFKC', str(text or ""))
  # Strip any leading unicode emoji/symbols so the lookup uses plain words.
  plain = re.sub(r'^[^\w\u0900-\u097F]+', '', raw).strip().lower()
  if plain in BUTTON_ICONS:
    return BUTTON_ICONS[plain]
  for key, emoji_id in BUTTON_ICONS.items():
    if key and key in plain:
      return emoji_id
  for key, emoji_id in _BUTTON_KEYWORD_ICONS:
    if key in plain:
      return emoji_id
  return None


def _strip_leading_emoji(text):
  """Remove leading unicode emoji from a button label (icons replace them)."""
  return re.sub(r'^[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\s]+',
                '', str(text))


class _StyledButtonProxy:
  """Button factory: mixed small-caps font, no colours, custom-emoji icon."""

  @staticmethod
  def _build(kind, text, target, icon_custom_emoji_id=None, icon=None, **kwargs):
    kwargs.pop("style", None)  # colours removed on purpose
    label = _button_font(_strip_leading_emoji(text))
    emoji_id = icon_custom_emoji_id or icon or _button_icon_id(text)
    try:
      emoji_id = int(emoji_id) if emoji_id else None
    except (TypeError, ValueError):
      emoji_id = None

    factory = (_ORIGINAL_BUTTON.inline if kind == "inline"
               else _ORIGINAL_BUTTON.url)
    if emoji_id:
      try:
        return factory(label, target, icon=emoji_id, **kwargs)
      except TypeError:
        pass  # Telethon Button.* has no `icon` argument -> attach style below
    try:
      btn = factory(label, target, **kwargs)
    except TypeError:
      btn = factory(label, target)
    if emoji_id:
      try:
        from telethon import types as _tl_types
        _Style = getattr(_tl_types, 'KeyboardButtonStyle', None)
        if _Style is not None and getattr(btn, 'button', None) is not None:
          btn.button.style = _Style(icon=emoji_id)
      except Exception:
        pass
    return btn

  @staticmethod
  def inline(text, data=None, icon_custom_emoji_id=None, icon=None, **kwargs):
    return _StyledButtonProxy._build(
      "inline", text, data, icon_custom_emoji_id=icon_custom_emoji_id,
      icon=icon, **kwargs)

  @staticmethod
  def url(text, url, icon_custom_emoji_id=None, icon=None, **kwargs):
    return _StyledButtonProxy._build(
      "url", text, url, icon_custom_emoji_id=icon_custom_emoji_id,
      icon=icon, **kwargs)

  def __getattr__(self, name):
    return getattr(_ORIGINAL_BUTTON, name)


Button = _StyledButtonProxy
from telethon.errors import (
  SessionPasswordNeededError, 
  MessageNotModifiedError,
  UserNotParticipantError,
  ChatAdminRequiredError
)
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.tl.functions.account import GetPasswordRequest
try:
  from telethon.sessions import StringSession as _TGStringSession
except Exception:
  _TGStringSession = None
try:
  from telethon.tl.functions.account import (
    GetAuthorizationsRequest as _TGGetAuthorizations,
    ResetAuthorizationRequest as _TGResetAuthorization,
  )
except Exception:
  _TGGetAuthorizations = None
  _TGResetAuthorization = None

# ================= CONFIGURATION =================
API_ID = 31535678 
API_HASH = "18682b75e0e6e1a7c5bb11fb65452153"
BOT_TOKEN = "8758463468:AAEMnTlr6wE0mBkCO5QUFZQoJ3zdhi53yr4" 
ADMIN_ID = 6914205738 

# ================= TELEGRAM CUSTOM EMOJI CONSTANTS (UPDATED) =================
# Premium custom emoji (Telegram <tg-emoji>) used across the main menu,
# store, profile, wallet and admin panels. Country flags are handled
# separately by COUNTRY_FLAGS so the country section stays untouched.

P_YES = '<tg-emoji emoji-id="5348035934870849516">✅</tg-emoji>'
P_NO = '<tg-emoji emoji-id="5352909795038880233">❌</tg-emoji>'
P_PKG = '<tg-emoji emoji-id="5352718875152639926">🛒</tg-emoji>'
P_MONEY = '<tg-emoji emoji-id="5348418461838098123">💰</tg-emoji>'
P_USDT = '<tg-emoji emoji-id="5350290466283744905">💲</tg-emoji>'
P_INR = '₹'
P_TG = '<tg-emoji emoji-id="5454245266305604993">✈️</tg-emoji>'
P_GIFT = '<tg-emoji emoji-id="5353049621994173706">🎁</tg-emoji>'
P_STATS = '<tg-emoji emoji-id="5350613306090482956">📊</tg-emoji>'
P_CARD = '<tg-emoji emoji-id="5350312748574076353">💳</tg-emoji>'
P_USERS = '<tg-emoji emoji-id="5348136664738839786">👤</tg-emoji>'
P_CAL = '<tg-emoji emoji-id="5350595795508814391">🕓</tg-emoji>'
P_PC = '<tg-emoji emoji-id="5454079785510660283">💻</tg-emoji>'
P_EYE = '<tg-emoji emoji-id="5350803525897054388">👀</tg-emoji>'
P_CW = '<tg-emoji emoji-id="5452002073606384268">🔄</tg-emoji>'
P_ON = '<tg-emoji emoji-id="5348125643852758491">🔔</tg-emoji>'
P_OFF = '<tg-emoji emoji-id="5348296085334934565">🔕</tg-emoji>'
P_ID = '<tg-emoji emoji-id="5454419255430767770">📎</tg-emoji>'
P_KEY = '<tg-emoji emoji-id="5454386656628991407">🔑</tg-emoji>'
P_GLOBE = '<tg-emoji emoji-id="5348540950010412359">🌐</tg-emoji>'
P_CART = '<tg-emoji emoji-id="5352718875152639926">🛒</tg-emoji>'
P_STORE = '<tg-emoji emoji-id="5350295774863311434">💼</tg-emoji>'
P_OTP = '<tg-emoji emoji-id="5350781673103453057">🔐</tg-emoji>'
P_2FA = '<tg-emoji emoji-id="5350806480834553770">🛡</tg-emoji>'
P_FLAG = '<tg-emoji emoji-id="5454310635707853545">🚩</tg-emoji>'
P_PHONE = '<tg-emoji emoji-id="5350280858441903578">📞</tg-emoji>'
P_WAIT = '<tg-emoji emoji-id="5352940967911517739">⏳</tg-emoji>'
P_TIME = '<tg-emoji emoji-id="5348090777308251395">⏰</tg-emoji>'
P_WARN = '<tg-emoji emoji-id="5350477112677515642">⚠️</tg-emoji>'
P_DOC = '<tg-emoji emoji-id="5350727535040684495">📔</tg-emoji>'
P_ASST = '<tg-emoji emoji-id="5350635725819768084">🤖</tg-emoji>'
P_ACC = '<tg-emoji emoji-id="5350763436672305153">👤</tg-emoji>'
P_FIRE = '<tg-emoji emoji-id="5348529413728256481">🔥</tg-emoji>'
P_STAR = '<tg-emoji emoji-id="5350439235360932475">⭐</tg-emoji>'
P_DIAMOND = '<tg-emoji emoji-id="5350431598909089381">💎</tg-emoji>'
P_BELL = '<tg-emoji emoji-id="5352874632141628924">🔔</tg-emoji>'
P_CROWN = '<tg-emoji emoji-id="5352670019899652428">👑</tg-emoji>'
P_LIGHTNING = '<tg-emoji emoji-id="5350618807943576963">⚡</tg-emoji>'
P_ROCKET = '<tg-emoji emoji-id="5350490470025816976">🚀</tg-emoji>'
P_PARTY = '<tg-emoji emoji-id="5350593231413341402">🎉</tg-emoji>'
P_FOLDER = '<tg-emoji emoji-id="5350685478720924701">🗂</tg-emoji>'
P_GEAR = '<tg-emoji emoji-id="5348412779596365405">⚙️</tg-emoji>'
P_PIN = '<tg-emoji emoji-id="5348498060466996739">📌</tg-emoji>'
P_SEARCH = '<tg-emoji emoji-id="5350776428948381533">🔍</tg-emoji>'
P_LINK = '<tg-emoji emoji-id="5350695039318114023">🔗</tg-emoji>'
P_TITLE = '<tg-emoji emoji-id="5350333514740951883">✨</tg-emoji>'
P_DESC = '<tg-emoji emoji-id="5348471079482441278">💬</tg-emoji>'
P_RATE = '<tg-emoji emoji-id="5350613306090482956">📊</tg-emoji>'
P_MIN = '<tg-emoji emoji-id="5350700390847365132">⏬</tg-emoji>'
P_MAX = '<tg-emoji emoji-id="5350305520144106741">⏫</tg-emoji>'
P_QTY = '<tg-emoji emoji-id="5350778250014515913">1️⃣</tg-emoji>'

def strip_custom_emoji(text):
  """Convert <tg-emoji ...>X</tg-emoji> blocks into their plain emoji fallback X."""
  if text is None:
    return text
  return re.sub(r'<tg-emoji\b[^>]*>(.*?)</tg-emoji>', r'\1', str(text),
                flags=re.DOTALL | re.IGNORECASE)


def _telethon_supports_custom_emoji():
  """True when the installed Telethon understands <tg-emoji emoji-id="...">."""
  try:
    from telethon.extensions import html as _tl_html
    from telethon.tl.types import MessageEntityCustomEmoji
    _, _ents = _tl_html.parse('<tg-emoji emoji-id="5348035934870849516">x</tg-emoji>')
    return any(isinstance(en, MessageEntityCustomEmoji) for en in _ents)
  except Exception:
    return False


# Runtime capability flag. If Telegram/Telethon rejects a custom-emoji message
# the sender wrapper below flips this to False and automatically re-sends the
# same message with plain emoji fallbacks, so the bot never breaks.
CUSTOM_EMOJI_ENABLED = _telethon_supports_custom_emoji()


def custom_emoji_text(text):
  """Return message text with plain emoji removed but <tg-emoji> kept intact.

  Country flags are rendered with Telegram custom emoji
  (``<tg-emoji emoji-id="...">fallback</tg-emoji>``). The plain-emoji scrubber
  below would otherwise delete the fallback flag inside that tag and leave an
  invalid/empty custom-emoji entity, so every <tg-emoji> block is protected
  first and restored at the very end.
  """
  if text is None:
    return text
  text = str(text)

  # If custom emoji are unavailable, keep the plain emoji fallbacks instead of
  # deleting them (otherwise every icon would disappear from the UI).
  if not CUSTOM_EMOJI_ENABLED:
    return strip_custom_emoji(text)

  protected = []

  def _keep(match):
    protected.append(match.group(0))
    return f"\x00TGEMOJI{len(protected) - 1}\x00"

  text = re.sub(r'<tg-emoji\b[^>]*>.*?</tg-emoji>', _keep, text,
                flags=re.DOTALL | re.IGNORECASE)
  text = re.sub(r'<emoji\s+id=["\'][^"\']+["\']>(.*?)</emoji>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
  # Remove emoji/pictograph/symbol ranges while retaining ordinary text and currency symbols.
  text = re.sub(r'[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]', '', text)

  for index, block in enumerate(protected):
    text = text.replace(f"\x00TGEMOJI{index}\x00", block)
  return text


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs("sessions", exist_ok=True)

session_name = f"bot_session_{BOT_TOKEN.split(':')[0]}"
bot = TelegramClient(session_name, API_ID, API_HASH)
bot.parse_mode = 'html'


def _looks_like_custom_emoji_error(exc):
  msg = str(exc).lower()
  return ('custom emoji' in msg or 'custom_emoji' in msg or 'emoji' in msg) and (
    'invalid' in msg or 'not allowed' in msg or 'only be used' in msg or 'premium' in msg
  )


def _patch_custom_emoji_fallback(client):
  """Re-send messages without <tg-emoji> if Telegram rejects custom emoji.

  This keeps the bot fully functional on older Telethon builds or on bot
  accounts that are not allowed to use custom emoji: the first rejected send
  disables custom emoji globally and the same message is retried with the
  plain emoji fallbacks.
  """
  import functools
  for name in ('send_message', 'edit_message', 'send_file', 'send_photo', 'send_document'):
    original = getattr(client, name, None)
    if original is None:
      continue

    @functools.wraps(original)
    async def wrapper(*args, __orig=original, **kwargs):
      global CUSTOM_EMOJI_ENABLED
      try:
        return await __orig(*args, **kwargs)
      except Exception as ex:
        if not CUSTOM_EMOJI_ENABLED or not _looks_like_custom_emoji_error(ex):
          raise
        # Only THIS message falls back to plain emoji. The global flag is no
        # longer switched off, otherwise one bad emoji id made every later
        # message in the bot lose its premium emoji.
        logger.warning(f"Custom emoji rejected ({ex}); retrying this message with plain emoji.")
        new_args = tuple(strip_custom_emoji(a) if isinstance(a, str) else a for a in args)
        new_kwargs = {k: (strip_custom_emoji(v) if isinstance(v, str) else v)
                      for k, v in kwargs.items()}
        return await __orig(*new_args, **new_kwargs)

    setattr(client, name, wrapper)


_patch_custom_emoji_fallback(bot)

db = sqlite3.connect("otp_bot_final.db", check_same_thread=False, timeout=20)
db.execute("PRAGMA journal_mode=WAL;")
cur = db.cursor()

active_orders = {}   
waiting_proof = {}   
deposit_input = {} 
admin_dep_state = {}  
user_spam_cooldown = {} 
session_buy_state = {}   
smm_order_state = {}
refill_state = {}
redeem_state = {}
digital_shop_state = {}

# Telegram callback_data is limited to 64 UTF-8 bytes. Country/account names
# can contain fancy Unicode characters which make callback_data exceed that
# limit. Always use a short stable token in buttons and resolve it back to the
# real database value when clicked. This keeps display names fully Unicode-safe.
def _country_token(country):
  return hashlib.sha256(str(country).encode("utf-8")).hexdigest()[:10]

def _resolve_country_ref(ref):
  ref = str(ref or "")
  # New compact token format.
  if re.fullmatch(r"[0-9a-f]{10}", ref):
    rows = cur.execute("SELECT DISTINCT country_name FROM stock").fetchall()
    for (name,) in rows:
      if _country_token(name) == ref:
        return name
  # Backward compatibility for old buttons which stored the literal name.
  return ref

user_locks = {}

def get_user_lock(uid):
  if uid not in user_locks:
    user_locks[uid] = asyncio.Lock()
  return user_locks[uid]

def setup_db():
  cur.executescript("""
  CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    total_deposited INTEGER DEFAULT 0,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    banned INTEGER DEFAULT 0,
    discount INTEGER DEFAULT 0,
    terms_accepted INTEGER DEFAULT 1
  );
  CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
  CREATE TABLE IF NOT EXISTS stock (
    phone TEXT PRIMARY KEY,
    session_file TEXT,
    country_name TEXT,
    country_icon TEXT DEFAULT '',
    account_year INTEGER,
    category TEXT DEFAULT 'Good',
    price INTEGER,
    available INTEGER DEFAULT 1,
    twofa TEXT DEFAULT 'None',
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS auto_prices (
    country TEXT,
    year TEXT,
    price INTEGER,
    PRIMARY KEY (country, year)
  );
  CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    method_name TEXT,
    status TEXT, 
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    country TEXT,
    year INTEGER,
    price INTEGER,
    phone TEXT,
    otp TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS smm_orders (
    bot_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    service_id INTEGER,
    link TEXT,
    quantity INTEGER,
    total_price REAL,
    smm_order_id TEXT,
    status TEXT DEFAULT 'Completed',
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    p_add_stock INTEGER DEFAULT 1,
    p_manage_stock INTEGER DEFAULT 1,
    p_stats INTEGER DEFAULT 1,
    p_bal INTEGER DEFAULT 1,
    p_settings INTEGER DEFAULT 1
  );
  CREATE TABLE IF NOT EXISTS custom_countries (
    code TEXT PRIMARY KEY,
    name TEXT,
    flag TEXT DEFAULT ''
  );
  CREATE TABLE IF NOT EXISTS force_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    invite_url TEXT,
    title TEXT
  );
  CREATE TABLE IF NOT EXISTS force_join_requests (
    channel_id TEXT,
    user_id INTEGER,
    PRIMARY KEY (channel_id, user_id)
  );
  CREATE TABLE IF NOT EXISTS smm_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
  );
  CREATE TABLE IF NOT EXISTS smm_services (
    service_id INTEGER PRIMARY KEY,
    category_id INTEGER,
    name TEXT,
    rate REAL,
    min INTEGER,
    max INTEGER,
    description TEXT
  );
  CREATE TABLE IF NOT EXISTS redeem_codes (
    code TEXT PRIMARY KEY,
    amount INTEGER NOT NULL,
    max_users INTEGER NOT NULL DEFAULT 1,
    used_count INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1
  );
  CREATE TABLE IF NOT EXISTS redeem_claims (
    code TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    claimed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code, user_id)
  );
  CREATE TABLE IF NOT EXISTS s2_orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER,
    country_code TEXT DEFAULT '',
    country_name TEXT DEFAULT '',
    number TEXT DEFAULT '',
    price INTEGER DEFAULT 0,
    status TEXT DEFAULT 'waiting',
    code TEXT DEFAULT '',
    password TEXT DEFAULT '',
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS digital_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price INTEGER NOT NULL,
    photo_file_id TEXT DEFAULT '',
    photo_path TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1
  );
  """)
  
  # Shop migration: optional preview image + separate required delivery file.
  try:
    cur.execute("ALTER TABLE digital_products ADD COLUMN file_path TEXT DEFAULT ''")
  except sqlite3.OperationalError:
    pass

  # Server 1 (Nobelots) migration: batch -> account number + one-time charge flag.
  try:
    cur.execute("ALTER TABLE s2_orders ADD COLUMN account_no TEXT DEFAULT ''")
  except sqlite3.OperationalError:
    pass
  try:
    cur.execute("ALTER TABLE s2_orders ADD COLUMN charged INTEGER DEFAULT 0")
  except sqlite3.OperationalError:
    pass

  # Server 1 terms gate: a user must tap "Agree and Continue" once.
  cur.execute(
    "CREATE TABLE IF NOT EXISTS s1_terms ("
    "user_id INTEGER PRIMARY KEY, accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

  # Migration for payment UTR tracking / duplicate protection.
  try:
    cur.execute("ALTER TABLE deposits ADD COLUMN utr TEXT DEFAULT ''")
  except sqlite3.OperationalError:
    pass
  try:
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deposits_utr ON deposits(utr)")
  except Exception:
    pass

  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('imap_server', 'imap.gmail.com')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('imap_email', 'aroy327154@gmail.com')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('imap_password', 'rerg jyiu dhyx fciq')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fampay_upi', 'fampay@upi')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fampay_name', 'Aaditya Tg Store')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('manual_upi', 'manual@upi')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('manual_name', 'Aaditya Tg Store Manual')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fampay_enabled', 'on')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('manual_enabled', 'on')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usdt_enabled', 'on')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usdt_address', '')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usdt_network', 'TRC20')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('log_channel_id', '-1003940330621')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('support_url', 'https://t.me/AADITYAXOFFICAL')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('support_channel_url', 'https://t.me/+yhaYNpSyF5U3Y2Q9')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('smm_api_url', '')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('smm_api_key', '')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('server1_api_url', 'https://nobelots-reseller-v4-colour-buttons-ysgr.onrender.com/api/v1')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('server1_api_key', '')")
  cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('server1_margin', '0')")

  # Migrate an existing install off the old Phantom API. The old key is cleared
  # so the admin is forced to paste the new Nobelots `nbl_live_...` key.
  cur.execute(
    "UPDATE settings SET value='https://nobelots-reseller-v4-colour-buttons-ysgr.onrender.com/api/v1' "
    "WHERE key='server1_api_url' AND (value LIKE '%phantomtg%' OR value='')")
  cur.execute(
    "UPDATE settings SET value='' WHERE key='server1_api_key' AND value LIKE 'ph_%'")
  db.commit()

setup_db()

# Requested default Support/Updates destinations. Only migrate the old
# built-in defaults; a custom URL previously configured by the admin is kept.
def ensure_requested_default_links():
  defaults = {
    'support_url': 'https://t.me/AADITYAXOFFICAL',
    'support_channel_url': 'https://t.me/+yhaYNpSyF5U3Y2Q9',
  }
  old_defaults = {
    'support_url': {'', 'https://t.me/m/P7am0xdlZmE1'},
    'support_channel_url': {'', 'https://t.me/', 'https://t.me/m/P7am0xdlZmE1'},
  }
  for key, default in defaults.items():
    row = cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    current = (row[0] or '').strip() if row else ''
    valid = current.startswith(('http://', 'https://', 'tg://')) and len(current) > len('https://t.me/')
    if current in old_defaults[key] or not valid:
      cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, default))
  db.commit()

ensure_requested_default_links()

# Migrate previously embedded Gmail App Passwords to the current one.
# A custom password configured by the admin from the panel is preserved.
try:
  _imap_user = cur.execute("SELECT value FROM settings WHERE key='imap_email'").fetchone()
  _imap_pwd = cur.execute("SELECT value FROM settings WHERE key='imap_password'").fetchone()
  _old_pwds = {'yascqrsoaunpdnbc', 'foorirclisyrjcva', ''}
  if ((_imap_user and (_imap_user[0] or '').strip() == 'aroy327154@gmail.com') and
      (_imap_pwd is not None) and
      re.sub(r"\s+", "", (_imap_pwd[0] or '').strip()) in _old_pwds):
    cur.execute("UPDATE settings SET value=? WHERE key='imap_password'", ('rerg jyiu dhyx fciq',))
    db.commit()
except Exception:
  pass

try:
  cur.execute("UPDATE settings SET value='Aaditya Tg Store' WHERE key='fampay_name' AND value IN ('Aaditya','Aaditya Store')")
  cur.execute("UPDATE settings SET value='Aaditya Tg Store Manual' WHERE key='manual_name' AND value IN ('Aaditya Manual','Acc Store Manual')")
  db.commit()
except Exception:
  pass


# Bot status has THREE modes, cycled by one admin button:
#   ON  ->  MAINTENANCE  ->  OFF  ->  ON ...
# Admins can always use the bot. Normal users are blocked in MAINTENANCE and OFF.
BOT_STATUS_NEXT = {'on': 'maintenance', 'maintenance': 'off', 'off': 'on'}
BOT_STATUS_LABEL = {'on': 'Bot ON', 'maintenance': 'Maintenance', 'off': 'Bot OFF'}


def get_bot_status():
  try:
    res = cur.execute("SELECT value FROM settings WHERE key='bot_status'").fetchone()
  except Exception:
    return 'on'
  v = str(res[0]).strip().lower() if res and res[0] is not None else 'on'
  return v if v in BOT_STATUS_NEXT else 'on'


def set_bot_status(value):
  value = value if value in BOT_STATUS_NEXT else 'on'
  cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (value,))
  db.commit()
  return value


def is_bot_online():
  return get_bot_status() == 'on'


def bot_block_text():
  """Message shown to normal users while the bot is not ON."""
  if get_bot_status() == 'maintenance':
    return (f"{P_WARN} <b>Bot is under maintenance.</b>\n\n"
            "We are improving things for you. Please try again in a little while.")
  return (f"{P_OFF} <b>Bot is currently OFF.</b>\n\n"
          "Please come back later.")


def is_admin(uid):
  if uid == ADMIN_ID: return True
  row = cur.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,)).fetchone()
  return bool(row)

def has_perm(uid, perm):
  if uid == ADMIN_ID: return True
  row = cur.execute(f"SELECT {perm} FROM admins WHERE user_id=?", (uid,)).fetchone()
  return bool(row and row[0] == 1)

def get_all_admin_ids():
  """Return the owner plus every admin configured in the admins table, without duplicates."""
  ids = [ADMIN_ID]
  try:
    rows = cur.execute("SELECT user_id FROM admins").fetchall()
    ids.extend(int(row[0]) for row in rows if row and row[0])
  except Exception as ex:
    logger.error(f"Failed to load admin IDs: {ex}")
  return list(dict.fromkeys(ids))

async def send_admins_file(photo, caption, buttons=None):
  """Forward a photo to the owner and all configured admins."""
  sent = 0
  for admin_id in get_all_admin_ids():
    try:
      await bot.send_file(admin_id, photo, caption=custom_emoji_text(caption), buttons=buttons)
      sent += 1
    except Exception as ex:
      logger.error(f"Failed to send admin review to {admin_id}: {ex}")
  return sent

def ensure_user(uid):
  cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
  db.commit()

def get_usdt_rate():
  res = cur.execute("SELECT value FROM settings WHERE key='usdt_rate'").fetchone()
  try: return float(res[0]) if res else 94.0
  except: return 94.0

def _normalize_tg_url(raw_url, fallback=""):
  """Normalize a Telegram username/link without ever returning an invalid t.me root URL."""
  url = str(raw_url or "").strip()
  if not url:
    return fallback
  if url.startswith("@"): 
    url = "https://t.me/" + url[1:]
  elif not url.startswith(("http://", "https://")):
    url = "https://t.me/" + url.lstrip("/")
  # Telegram rejects bare https://t.me/ as a Button.url destination.
  if re.fullmatch(r"https?://t\.me/?", url, flags=re.IGNORECASE):
    return fallback
  # Basic URL sanity check; keep normal t.me invite links and usernames.
  if not re.match(r"^https?://(?:t\.me|telegram\.me)/[^\s<>]+$", url, flags=re.IGNORECASE):
    return fallback
  return url

def _safe_url_button(label, raw_url):
  """Build a Telegram URL button only when the URL is valid. Never let a bad admin/config URL crash a whole message."""
  url = _normalize_tg_url(raw_url, "")
  if not url:
    return None
  try:
    return Button.url(str(label)[:64], url)
  except Exception as ex:
    logger.error(f"Invalid URL button skipped: {ex}")
    return None

def get_support_url():
  # Admin Panel -> Support URL is the single source of truth for Support.
  res = cur.execute("SELECT value FROM settings WHERE key='support_url'").fetchone()
  return _normalize_tg_url(res[0] if res and res[0] else "", "")

def get_support_channel_url():
  # Admin Panel -> Support/Updates Channel is used for the Updates button.
  res = cur.execute("SELECT value FROM settings WHERE key='support_channel_url'").fetchone()
  return _normalize_tg_url(res[0] if res and res[0] else "", "")

def _has_valid_button_url(url):
  return bool(_normalize_tg_url(url, ""))

def get_fampay_upi():
  res = cur.execute("SELECT value FROM settings WHERE key='fampay_upi'").fetchone()
  return res[0] if res and res[0] else "fampay@upi"

def get_fampay_name():
  res = cur.execute("SELECT value FROM settings WHERE key='fampay_name'").fetchone()
  return res[0] if res and res[0] else "Aaditya Tg Store"


def get_setting(key, default=''):
  row = cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
  return row[0] if row and row[0] is not None else default

def set_setting(key, value):
  cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
  db.commit()

def get_usdt_address(): return (get_setting('usdt_address', '') or '').strip()
def get_usdt_network(): return (get_setting('usdt_network', 'TRC20') or 'TRC20').strip()
def usdt_manual_available():
  """USDT Manual is shown to users only when it is ON and an address is configured."""
  return payment_enabled('usdt_enabled') and bool(get_usdt_address())
def get_manual_upi(): return get_setting('manual_upi', 'manual@upi')
def get_manual_name(): return get_setting('manual_name', 'Aaditya Tg Store Manual')
def payment_enabled(key): return get_setting(key, 'on').lower() == 'on'

def get_log_channel_id():
  res = cur.execute("SELECT value FROM settings WHERE key='log_channel_id'").fetchone()
  try: return int(res[0]) if res and res[0] else -1003940330621
  except: return -1003940330621

SELLING_LOGS_DEFAULT_LINK = "https://t.me/+dWA-jgCaNBMyNzRl"


def get_selling_logs_link():
  """Link used by the main-menu 'Selling Logs' button (auto-generated from the
  configured logs channel; falls back to the built-in link)."""
  link = get_setting('selling_logs_link', '').strip()
  return link if link and _has_valid_button_url(link) else SELLING_LOGS_DEFAULT_LINK


async def generate_selling_logs_link(channel_id):
  """Build a join link for the logs channel. Returns (link, reason)."""
  try:
    peer = await _get_channel_entity(channel_id)
    try:
      ent = await bot.get_entity(peer)
      uname = getattr(ent, 'username', None)
      if not uname:
        for u in (getattr(ent, 'usernames', None) or []):
          if getattr(u, 'active', False) and getattr(u, 'username', None):
            uname = u.username
            break
      if uname:
        return f"https://t.me/{uname}", ""
    except Exception:
      pass
    from telethon.tl.functions.messages import ExportChatInviteRequest
    res = await bot(ExportChatInviteRequest(peer=peer))
    link = getattr(res, 'link', '') or ''
    if link:
      return link, ""
    return "", "Telegram did not return an invite link."
  except Exception as ex:
    logger.warning(f"Selling logs link generation failed for {channel_id}: {ex}")
    return "", str(ex)


async def refresh_selling_logs_link(channel_id=None):
  """Generate + store the link. Returns the stored link or ''."""
  link, _ = await generate_selling_logs_link(channel_id if channel_id is not None else get_log_channel_id())
  if link:
    set_setting('selling_logs_link', link)
  return link


def clean_html_url(raw_url):
  if not raw_url: return ""
  clean = re.sub(r'<.*?>', '', raw_url)
  match = re.search(r'https?://[^\s<>"]+', clean)
  if match:
    return match.group(0).strip()
  return clean.strip()

def get_smm_api_config():
  url = cur.execute("SELECT value FROM settings WHERE key='smm_api_url'").fetchone()
  key = cur.execute("SELECT value FROM settings WHERE key='smm_api_key'").fetchone()
  raw_url = url[0].strip() if url and url[0] else ""
  return (clean_html_url(raw_url), key[0].strip() if key and key[0] else "")

def get_ssl_context():
  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE
  return ctx

def fetch_smm_services_from_api(api_url, api_key):
  api_url = clean_html_url(api_url)
  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive'
  }
  try:
    data = urllib.parse.urlencode({'key': api_key, 'action': 'services'}).encode('utf-8')
    req = urllib.request.Request(api_url, data=data, method='POST', headers=headers)
    ctx = get_ssl_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
      res_text = response.read().decode('utf-8', errors='ignore')
      return json.loads(res_text)
  except Exception as e:
    logger.error(f"SMM API POST Fetch Error: {e}")
    try:
      get_url = f"{api_url.rstrip('/')}?key={api_key}&action=services"
      req = urllib.request.Request(get_url, headers=headers)
      ctx = get_ssl_context()
      with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
        res_text = response.read().decode('utf-8', errors='ignore')
        return json.loads(res_text)
    except Exception as e2:
      logger.error(f"SMM API GET Fetch Error: {e2}")
      return None

def place_smm_order_api(api_url, api_key, service_id, link, quantity):
  api_url = clean_html_url(api_url)
  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': api_url.split('/api')[0] if '/api' in api_url else api_url,
    'Referer': api_url,
    'X-Requested-With': 'XMLHttpRequest'
  }
  try:
    data = urllib.parse.urlencode({
      'key': api_key,
      'action': 'add',
      'service': service_id,
      'link': link,
      'quantity': quantity
    }).encode('utf-8')
    
    req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')
    ctx = get_ssl_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
      res_text = response.read().decode('utf-8', errors='ignore')
      
      if "<html" in res_text.lower() or "cloudflare" in res_text.lower():
        logger.error("Cloudflare blocked the SMM API order request.")
        return {"error": "Cloudflare security block! Please whitelist server IP in panel admin."}
        
      return json.loads(res_text)
  except Exception as e:
    logger.error(f"SMM Order API Error: {e}")
    return {"error": f"API Connection Error: {str(e)}"}

def refill_smm_order_api(api_url, api_key, smm_order_id):
  api_url = clean_html_url(api_url)
  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  }
  try:
    data = urllib.parse.urlencode({
      'key': api_key,
      'action': 'refill',
      'order': smm_order_id
    }).encode('utf-8')
    req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')
    ctx = get_ssl_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
      res_text = response.read().decode('utf-8', errors='ignore')
      return json.loads(res_text)
  except Exception as e:
    logger.error(f"SMM Refill API Error: {e}")
    return {"error": str(e)}

# ================= SERVER 1 — NOBELOTS RESELLER API =================
# Server 1 is powered by the Nobelots Reseller API (Server 2 = Telegram numbers).
#   GET  /health                              -> service check (no key)
#   GET  /me                                  -> key info + wallet balance
#   GET  /servers/{s}/countries               -> countries with from_price
#   GET  /servers/{s}/countries/{cc}          -> live stock + price ladder
#   GET  /servers/{s}/countries/{cc}/accounts -> individual accounts
#   POST /orders                              -> buy (Idempotency-Key required)
#   GET  /orders/{batch_id}?wait=20           -> long-poll an order
#   POST /accounts/{order_no}/code            -> Telegram login code (OTP)
#   GET  /accounts/{order_no}/session         -> Telethon StringSession
# Auth: Authorization: Bearer nbl_live_...
# Admin sets the API URL + key from Admin Panel -> Servers APIs.
NOBELOTS_BASE_URL = "https://nobelots-reseller-v4-colour-buttons-ysgr.onrender.com/api/v1"
NOBELOTS_API_SERVER = 1

SERVER_DEFS = {
  1: {
    "name": "Server 1",
    "label": "Server 1 [cheap account]",
    "url_key": "server1_api_url",
    "key_key": "server1_api_key",
    "margin_key": "server1_margin",
    "default_url": NOBELOTS_BASE_URL,
    "api_server": NOBELOTS_API_SERVER,
    "default_margin": 0.0,
    "kind": "nobelots",
  },
  2: {
    "name": "Server 2",
    "label": "Server 2 [ WhatsApp Accounts ]",
    "url_key": "s2_wa_url",
    "key_key": "s2_wa_api_key",
    "margin_key": "s2_wa_margin",
    "default_url": "https://api.tiger-sms.com/stubs/handler_api.php",
    "default_margin": 25.0,
    "kind": "tiger",
  },
}

# Countries are cached briefly so paging does not burn the 60 req/min limit.
_s2_countries_cache = {"ts": 0.0, "data": []}
S2_COUNTRIES_TTL = 60
S2_COUNTRIES_PER_PAGE = 8

# ---- Country flag custom emoji (Telegram custom emoji IDs) ----
# Country code -> Telegram custom emoji id. These render as premium animated
# flags inside message text. Country buttons also carry the same flag as their
# icon (icon_custom_emoji_id).
COUNTRY_FLAGS = {
  "AF": "5291937511591925566", "AX": "5294077418917616055",
  "AL": "5294202819077756005", "DZ": "5294048127240655242",
  "AS": "5291994273879709721", "AD": "5294215205763434181",
  "AO": "5294516785482062829", "AI": "5292186323342350940",
  "AG": "5294005972136647964", "AR": "5292208210495689627",
  "AM": "5291978717508164018", "AW": "5294007002928798927",
  "AU": "5294444247779399477", "AT": "5291975174160145850",
  "AZ": "5294323533428579078", "BS": "5294031587321600012",
  "BH": "5294108398516720753", "BD": "5291824687096027834",
  "BB": "5294526187165471742", "BY": "5294134426018536120",
  "BE": "5291774466043435275", "BZ": "5294171848068584842",
  "BJ": "5293984969746566866", "BT": "5294121983498277263",
  "BO": "5294201479047957700", "BW": "5294026179957772585",
  "BR": "5291892229751723900", "BN": "5292098293692650297",
  "BG": "5294308947719640437", "BF": "5294153164960848949",
  "BI": "5294051631933967760", "KH": "5294225191562400452",
  "CM": "5291997306126626950", "CA": "5292290347450259214",
  "CV": "5292203503211535593", "CF": "5294210571493724819",
  "TD": "5291780728105753403", "CL": "5294231037012888049",
  "CN": "5294068833277990704", "CO": "5294010206974397371",
  "KM": "5294351381996521508", "CG": "5294035229453865597",
  "CK": "5292098684534675100", "CR": "5292063805105263554",
  "CI": "5293991322003200135", "HR": "5291999676948569127",
  "CU": "5291963947115631526", "CY": "5294062721539526918",
  "CZ": "5294242852467923382", "DK": "5294531860817268837",
  "DJ": "5294127214768468283", "DM": "5294485513825178032",
  "DO": "5294522197140857947", "EC": "5292083733753517221",
  "EG": "5293992082212409502", "SV": "5294337307388695687",
  "GB-ENG": "5294410107084365278", "GQ": "5292170045416297012",
  "ER": "5291922054004625949", "EE": "5291951143818123103",
  "ET": "5292245976143124155", "EU": "5291992809295861098",
  "GI": "5292055799286224027", "GM": "5294399820637688352",
  "GL": "5292014752283774878", "FI": "5294049961191690629",
  "FR": "5291817660529533837", "GA": "5294321325815389139",
  "GE": "5294349389131697267", "DE": "5292013274815028523",
  "GH": "5294347396266873249", "GR": "5291948395039054764",
  "GW": "5294409819321550432", "GT": "5294336633078831209",
  "GN": "5291892096607739008", "GY": "5292062692708736193",
  "HT": "5292045130587462814", "HN": "5291901034434682297",
  "HK": "5292166459118606932", "HU": "5294229581018975260",
  "IS": "5294354358408859664", "IN": "5291933173674957761",
  "IR": "5294220170745630736", "IQ": "5294325010897327367",
  "IE": "5294471971793293647", "IM": "5294318478252070646",
  "IL": "5294069056616289553", "IT": "5291826830284709120",
  "JM": "5294505107465982830", "JP": "5291799063321139445",
  "JE": "5291950280529697493", "JO": "5291988613112814801",
  "KZ": "5294227175837290463", "KE": "5292111852904416801",
  "KI": "5294538934628405146", "KP": "5294193812531333564",
  "KR": "5294408281723262763", "KW": "5292066437920218075",
  "KG": "5292091954320922577", "LA": "5291981530711746037",
  "LV": "5292236016113966127", "LB": "5294193108156699621",
  "LS": "5292040693886247604", "LR": "5291793810576137439",
  "LY": "5291858711826946840", "LI": "5292048742654957785",
  "LT": "5294343084119708700", "LU": "5294423709245787718",
  "MK": "5294023611567332075", "MG": "5291991568050312348",
  "MW": "5294241881805312589", "MY": "5291858351049696702",
  "MV": "5292004203844097218", "ML": "5292086972158858331",
  "MT": "5294532213004588353", "MH": "5294180730060954484",
  "MR": "5294429743674840973", "MU": "5294127824653797277",
  "MX": "5294535073452809778", "FM": "5291838156113470124",
  "MD": "5294158486425325375", "MC": "5294378161117614233",
  "MN": "5294316532631883496", "MA": "5292108962391414885",
  "MZ": "5294086708931874940", "MM": "5294254478944393569",
  "NA": "5292021761670404922", "NR": "5294463274484521342",
  "NP": "5294458756178924088", "NL": "5291917797692042265",
  "NZ": "5294189019347833274", "NI": "5294240825243358100",
  "NE": "5291809418487290691", "NG": "5294456308047563965",
  "NU": "5294471336138134209", "NO": "5291761718580502030",
  "OM": "5291813666209946812", "PK": "5291825606219029010",
  "PS": "5294289826525238172", "PA": "5291959935616178405",
  "PG": "5291917995260533077", "PY": "5294525611639852679",
  "PH": "5291798075478661634", "PE": "5292099427564018941",
  "PL": "5292190970496963836", "PT": "5294436555492973610",
  "PR": "5292121516580820347", "QA": "5292166360334357676",
  "RO": "5294107724206856227", "RU": "5294335323113807278",
  "RW": "5294191265615729158", "SM": "5292147350809106831",
  "ST": "5292183188016222701", "SA": "5294163983983463099",
  "GB-SCT": "5294434665707368018", "SN": "5292087023698466689",
  "RS": "5294458584380230360", "SC": "5291891186074672309",
  "SL": "5294494314213167952", "SG": "5294451304410663668",
  "SK": "5294538440707166931", "SI": "5294279359689938006",
  "SB": "5294283890880433237", "SO": "5294058817414255960",
  "ZA": "5294325281480266304", "ES": "5294513087515216901",
  "LK": "5292102670264328257", "SD": "5294177148058228060",
  "SR": "5294396668131692138", "SZ": "5294312482477724867",
  "SE": "5291737091238026321", "CH": "5291791748991835084",
  "SY": "5294013428199869487", "TW": "5294095745543069603",
  "TJ": "5294120269806328883", "TZ": "5292146096678658977",
  "TH": "5293994384314882755", "TG": "5294097669688415562",
  "TO": "5294283689016973348", "TT": "5294362935458548705",
  "TN": "5294484680601521871", "TR": "5293993400767367408",
  "TM": "5294098958178603764", "TC": "5294320866253884749",
  "US": "5294244076533600593", "UG": "5294192317882716626",
  "AE": "5294314831824835370", "GB": "5293993521026453119",
  "UA": "5294263837678131580", "VU": "5294448585696368047",
  "UZ": "5294217645304864345", "UY": "5291928449210932974",
  "VE": "5294476442854247878", "VN": "5294235963340379688",
  "VI": "5294228039125718124", "GB-WLS": "5294139949346476093",
  "YE": "5294058972033076492", "ZM": "5294100109229838880",
  "ZW": "5294422158762592930",
}

# Generic flag used when a country has no mapped custom emoji.
GENERIC_FLAG_EMOJI_ID = "5294236848103643477"

# Set to False if Telegram ever rejects the custom emoji entities.
COUNTRY_FLAGS_ENABLED = True

_SPECIAL_FLAG_FALLBACKS = {
  "GB-ENG": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
  "GB-SCT": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
  "GB-WLS": "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F",
}

# Matches flag emoji, tag sequences and pictographs that panels include in
# country names (e.g. "United States \U0001F1FA\U0001F1F8").
_NAME_EMOJI_RE = re.compile(
  r'[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D'
  r'\U000E0020-\U000E007F\U0001F3F4]')


# Country NAME -> ISO code. The flag is ALWAYS derived from the country name
# first (so name and flag can never disagree) and only then from a given code.
_COUNTRY_ALIASES = {
  "AF": "afghanistan", "AX": "aland islands|aland", "AL": "albania", "DZ": "algeria",
  "AS": "american samoa", "AD": "andorra", "AO": "angola", "AI": "anguilla",
  "AG": "antigua and barbuda|antigua", "AR": "argentina", "AM": "armenia", "AW": "aruba",
  "AU": "australia", "AT": "austria", "AZ": "azerbaijan", "BS": "bahamas",
  "BH": "bahrain", "BD": "bangladesh", "BB": "barbados", "BY": "belarus",
  "BE": "belgium", "BZ": "belize", "BJ": "benin", "BT": "bhutan",
  "BO": "bolivia", "BW": "botswana", "BR": "brazil", "BN": "brunei|brunei darussalam",
  "BG": "bulgaria", "BF": "burkina faso|burkina", "BI": "burundi", "KH": "cambodia",
  "CM": "cameroon", "CA": "canada", "CV": "cape verde|cabo verde", "CF": "central african republic|car",
  "TD": "chad", "CL": "chile", "CN": "china", "CO": "colombia", "KM": "comoros",
  "CG": "congo|republic of the congo|congo brazzaville|congo (brazzaville)",
  "CK": "cook islands", "CR": "costa rica", "CI": "ivory coast|cote d'ivoire|cote divoire|côte d'ivoire",
  "HR": "croatia", "CU": "cuba", "CY": "cyprus", "CZ": "czech republic|czechia|czech",
  "DK": "denmark", "DJ": "djibouti", "DM": "dominica", "DO": "dominican republic|dominican",
  "EC": "ecuador", "EG": "egypt", "SV": "el salvador|salvador", "GB-ENG": "england",
  "GQ": "equatorial guinea", "ER": "eritrea", "EE": "estonia", "ET": "ethiopia",
  "EU": "european union", "GI": "gibraltar", "GM": "gambia|the gambia", "GL": "greenland",
  "FI": "finland", "FR": "france", "GA": "gabon", "GE": "georgia", "DE": "germany",
  "GH": "ghana", "GR": "greece", "GW": "guinea-bissau|guinea bissau", "GT": "guatemala",
  "GN": "guinea", "GY": "guyana", "HT": "haiti", "HN": "honduras",
  "HK": "hong kong|hongkong", "HU": "hungary", "IS": "iceland",
  "IN": "india", "IR": "iran", "IQ": "iraq", "IE": "ireland", "IM": "isle of man",
  "IL": "israel", "IT": "italy", "JM": "jamaica", "JP": "japan", "JE": "jersey",
  "JO": "jordan", "KZ": "kazakhstan", "KE": "kenya", "KI": "kiribati",
  "KP": "north korea|dprk", "KR": "south korea|korea|republic of korea", "KW": "kuwait",
  "KG": "kyrgyzstan|kyrgyz", "LA": "laos|lao", "LV": "latvia", "LB": "lebanon",
  "LS": "lesotho", "LR": "liberia", "LY": "libya", "LI": "liechtenstein",
  "LT": "lithuania", "LU": "luxembourg", "MK": "north macedonia|macedonia",
  "MG": "madagascar", "MW": "malawi", "MY": "malaysia", "MV": "maldives", "ML": "mali",
  "MT": "malta", "MH": "marshall islands", "MR": "mauritania", "MU": "mauritius",
  "MX": "mexico", "FM": "micronesia", "MD": "moldova", "MC": "monaco", "MN": "mongolia",
  "MA": "morocco", "MZ": "mozambique", "MM": "myanmar|burma", "NA": "namibia",
  "NR": "nauru", "NP": "nepal", "NL": "netherlands|holland", "NZ": "new zealand",
  "NI": "nicaragua", "NE": "niger", "NG": "nigeria", "NU": "niue", "NO": "norway",
  "OM": "oman", "PK": "pakistan", "PS": "palestine", "PA": "panama",
  "PG": "papua new guinea", "PY": "paraguay", "PH": "philippines", "PE": "peru",
  "PL": "poland", "PT": "portugal", "PR": "puerto rico", "QA": "qatar", "RO": "romania",
  "RU": "russia|russian federation", "RW": "rwanda", "SM": "san marino",
  "ST": "sao tome and principe|sao tome", "SA": "saudi arabia", "GB-SCT": "scotland",
  "SN": "senegal", "RS": "serbia", "SC": "seychelles", "SL": "sierra leone",
  "SG": "singapore", "SK": "slovakia", "SI": "slovenia", "SB": "solomon islands",
  "SO": "somalia", "ZA": "south africa", "ES": "spain", "LK": "sri lanka",
  "SD": "sudan", "SR": "suriname", "SZ": "eswatini|swaziland", "SE": "sweden",
  "CH": "switzerland", "SY": "syria", "TW": "taiwan", "TJ": "tajikistan",
  "TZ": "tanzania", "TH": "thailand", "TG": "togo", "TO": "tonga",
  "TT": "trinidad and tobago|trinidad", "TN": "tunisia", "TR": "turkey|turkiye|türkiye",
  "TM": "turkmenistan", "TC": "turks and caicos|turks and caicos islands",
  "US": "usa|united states|united states of america|america|us",
  "UG": "uganda", "AE": "uae|united arab emirates|emirates",
  "GB": "uk|united kingdom|great britain|britain", "UA": "ukraine", "VU": "vanuatu",
  "UZ": "uzbekistan", "UY": "uruguay", "VE": "venezuela", "VN": "vietnam|viet nam",
  "VI": "virgin islands us|us virgin islands|virgin islands", "GB-WLS": "wales",
  "YE": "yemen", "ZM": "zambia", "ZW": "zimbabwe",
  # Countries WITHOUT a premium emoji id still resolve to the right ISO code
  # (they get the correct plain unicode flag, never a wrong/generic one).
  "CD": "dr congo|d.r. congo|democratic republic of the congo|congo (kinshasa)|congo kinshasa",
  "BA": "bosnia and herzegovina|bosnia", "ME": "montenegro", "XK": "kosovo",
  "MO": "macao|macau", "TL": "timor-leste|east timor|timor leste", "BM": "bermuda",
  "KY": "cayman islands", "FJ": "fiji", "WS": "samoa", "LC": "saint lucia|st lucia",
  "VC": "saint vincent and the grenadines|saint vincent", "KN": "saint kitts and nevis",
  "GD": "grenada", "BQ": "bonaire", "CW": "curacao", "SX": "sint maarten",
  "NC": "new caledonia", "PF": "french polynesia", "GP": "guadeloupe",
  "MQ": "martinique", "RE": "reunion", "GF": "french guiana", "SS": "south sudan",
  "EH": "western sahara", "FO": "faroe islands", "GU": "guam", "AC": "ascension",
}
_COUNTRY_NAME_TO_ISO = {}
for _iso, _names in _COUNTRY_ALIASES.items():
  for _n in _names.split("|"):
    _COUNTRY_NAME_TO_ISO[_n.strip()] = _iso


def _norm_country_name(name):
  name = re.sub(r'<[^>]+>', '', str(name or ""))
  name = re.sub(r'[\U0001F000-\U0001FAFF☀-➿️‍\U000E0020-\U000E007F]', '', name)
  name = unicodedata.normalize('NFKD', name)
  name = ''.join(ch for ch in name if not unicodedata.combining(ch))
  name = re.sub(r'\s+', ' ', name.replace('_', ' ')).strip().lower()
  return name


def country_code_from_name(name):
  """ISO code for a country name ('' when unknown)."""
  n = _norm_country_name(name)
  if not n:
    return ""
  if n in _COUNTRY_NAME_TO_ISO:
    return _COUNTRY_NAME_TO_ISO[n]
  stripped = re.sub(r'\s*\(.*?\)\s*', ' ', n).strip()
  if stripped in _COUNTRY_NAME_TO_ISO:
    return _COUNTRY_NAME_TO_ISO[stripped]
  if stripped.startswith("the ") and stripped[4:] in _COUNTRY_NAME_TO_ISO:
    return _COUNTRY_NAME_TO_ISO[stripped[4:]]
  return ""


def resolve_country_code(name=None, code=None):
  """Single source of truth: the NAME decides the flag; the code is only a
  fallback when the name is unknown. Keeps country + flag always identical."""
  by_name = country_code_from_name(name) if name else ""
  if by_name:
    return by_name
  c = str(code or "").strip().upper()
  if c in COUNTRY_FLAGS or c in _COUNTRY_ALIASES:
    return c
  return ""


def country_flag_fallback(country_code):
  """Plain unicode flag used as the fallback inside a custom emoji tag."""
  code = str(country_code or "").strip().upper()
  if code in _SPECIAL_FLAG_FALLBACKS:
    return _SPECIAL_FLAG_FALLBACKS[code]
  if len(code) == 2 and code.isalpha():
    return "".join(chr(0x1F1E6 + (ord(ch) - 65)) for ch in code)
  return "\U0001F3F3️"


def country_flag_html(country_code=None, name=None):
  """Custom-emoji flag markup. Pass name= so the flag always matches the
  country name. A country with no premium emoji id shows its REAL unicode flag
  (never a wrong/generic one)."""
  code = resolve_country_code(name, country_code)
  fallback = country_flag_fallback(code)
  if not COUNTRY_FLAGS_ENABLED:
    return fallback
  emoji_id = COUNTRY_FLAGS.get(code)
  if not emoji_id:
    return fallback if code else f'<tg-emoji emoji-id="{GENERIC_FLAG_EMOJI_ID}">{fallback}</tg-emoji>'
  return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def country_flag_icon_id(country_code=None, name=None):
  """Custom emoji id for a button icon; None when the country has no premium flag."""
  code = resolve_country_code(name, country_code)
  return COUNTRY_FLAGS.get(code) or (None if code else GENERIC_FLAG_EMOJI_ID)


def clean_country_name(name):
  """Strip emoji/flags from an API country name, keeping readable text."""
  name = re.sub(r'<[^>]+>', '', str(name or ""))
  name = _NAME_EMOJI_RE.sub('', name)
  return re.sub(r'\s+', ' ', name).strip()


def get_server_api_config(server_no=1):
  conf = SERVER_DEFS.get(int(server_no))
  if not conf:
    return "", ""
  raw_url = (get_setting(conf["url_key"], conf.get("default_url", "")) or "").strip()
  if not raw_url:
    raw_url = conf.get("default_url", "")
  api_key = (get_setting(conf["key_key"], "") or "").strip()
  return clean_html_url(raw_url), api_key


def get_server_margin(server_no=1):
  conf = SERVER_DEFS.get(int(server_no))
  if not conf:
    return 0.0
  try:
    return max(0.0, float(get_setting(conf["margin_key"], str(conf.get("default_margin", 0))) or 0))
  except Exception:
    return 0.0


def server_sell_price(api_price, server_no=1):
  """API price + admin profit margin, rounded up to a whole rupee."""
  try:
    base_price = float(api_price)
  except Exception:
    return 0
  total = base_price * (1 + get_server_margin(server_no) / 100.0)
  whole = int(total)
  return whole if total <= whole else whole + 1


def _mask_secret(value):
  value = str(value or "")
  if not value:
    return "Not set"
  if len(value) <= 8:
    return "Set"
  return value[:4] + "..." + value[-4:]


def _api_error_text(res):
  """Human-readable message from a Nobelots error payload."""
  if not isinstance(res, dict):
    return "Server API did not respond."
  message = str(res.get("message") or "").strip()
  error = str(res.get("error") or "").strip()
  details = res.get("details")
  if isinstance(details, dict):
    extra = ""
    if details.get("cheapest_price") is not None:
      extra = f" (cheapest: ₹{details.get('cheapest_price')})"
    elif details.get("cheapest_prices"):
      try:
        extra = " (available: " + ", ".join(f"₹{p}" for p in details["cheapest_prices"][:5]) + ")"
      except Exception:
        extra = ""
    elif details.get("limit"):
      extra = f" (limit: {details.get('limit')})"
    if message and extra and extra not in message:
      message = message + extra
  if message and error and error not in message:
    return f"{message} ({error})"
  if message:
    return message
  if error:
    return error
  return "Unknown API error."


def _nobelots_call(path, method="GET", payload=None, server_no=1, timeout=30,
                   idempotency_key=None):
  """Call the Nobelots Reseller API with the admin-configured key.

  Always returns a dict. Success: {"ok": True, ...body}. Lists are wrapped as
  {"ok": True, "data": [...]}. Errors follow the API shape and add `status`,
  `retry_after` and `request_id` for the UI.
  """
  base_url, api_key = get_server_api_config(server_no)
  if not api_key:
    return {"ok": False, "error": "missing_api_key",
            "message": "Server API key is not configured by the admin."}

  base = (base_url or NOBELOTS_BASE_URL).strip().rstrip("/")
  if not base.endswith("/api/v1"):
    base += "/api/v1"
  url = base + path

  headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
    "User-Agent": "AadityaTgStoreBot/1.0 (Nobelots-Reseller)",
  }
  if idempotency_key:
    headers["Idempotency-Key"] = str(idempotency_key)

  data = None
  if method.upper() in ("POST", "PUT", "PATCH"):
    headers["Content-Type"] = "application/json"
    data = json.dumps(payload or {}).encode("utf-8")

  req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
  try:
    with urllib.request.urlopen(req, context=get_ssl_context(), timeout=timeout) as resp:
      body = resp.read().decode("utf-8", errors="ignore")
  except urllib.error.HTTPError as ex:
    try:
      body = ex.read().decode("utf-8", errors="ignore")
    except Exception:
      body = ""
    parsed = _server_api_parse_json(body)
    err = {}
    if isinstance(parsed, dict):
      err = parsed.get("error") if isinstance(parsed.get("error"), dict) else parsed
    details = err.get("details") if isinstance(err, dict) else {}
    retry_after = None
    try:
      retry_after = int(ex.headers.get("Retry-After") or 0) or None
    except Exception:
      retry_after = None
    if retry_after is None and isinstance(details, dict):
      try:
        retry_after = int(details.get("retry_after") or 0) or None
      except Exception:
        retry_after = None
    return {
      "ok": False,
      "status": ex.code,
      "error": str(err.get("code") or f"http_{ex.code}") if isinstance(err, dict) else f"http_{ex.code}",
      "message": str(err.get("message") or f"Server API returned HTTP {ex.code}.") if isinstance(err, dict) else f"Server API returned HTTP {ex.code}.",
      "details": details or {},
      "retry_after": retry_after,
      "request_id": err.get("request_id") if isinstance(err, dict) else None,
    }
  except Exception as ex:
    logger.warning(f"Nobelots API call failed ({path}): {ex}")
    return {"ok": False, "error": "network_error",
            "message": f"Could not reach the server API: {ex}"}

  parsed = _server_api_parse_json(body)
  if parsed is None:
    return {"ok": False, "error": "bad_response",
            "message": "Server API returned an invalid response."}
  if isinstance(parsed, list):
    return {"ok": True, "data": parsed}
  if isinstance(parsed, dict):
    parsed.setdefault("ok", True)
    return parsed
  return {"ok": False, "error": "bad_response",
          "message": "Server API returned an unexpected response."}


def _server_api_parse_json(text):
  text = (text or "").strip()
  if not text:
    return None
  try:
    return json.loads(text)
  except Exception:
    pass
  match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
  if match:
    try:
      return json.loads(match.group(1))
    except Exception:
      return None
  return None


def fetch_s2_countries(force_refresh=False):
  """Live country list for Server 1 (list) or {"error": "..."} on failure.

  The Nobelots list endpoint returns `from_price` and `stock: null`; live stock
  is fetched per country on the detail page.
  """
  now = time.time()
  cached = _s2_countries_cache.get("data") or []
  if not force_refresh and cached and (now - _s2_countries_cache.get("ts", 0)) < S2_COUNTRIES_TTL:
    return cached

  api_server = SERVER_DEFS[1].get("api_server", NOBELOTS_API_SERVER)
  res = _nobelots_call(f"/servers/{api_server}/countries")
  if not res.get("ok"):
    if cached:
      return cached
    return {"error": _api_error_text(res)}

  countries = []
  for item in (res.get("data") or []):
    if not isinstance(item, dict):
      continue
    code = str(item.get("country") or "").strip().upper()
    if not code:
      continue
    try:
      price = float(item.get("from_price") or 0)
    except Exception:
      price = 0.0
    countries.append({
      "code": code,
      "name": str(item.get("name") or code),
      "dial": str(item.get("dial") or ""),
      "stock": item.get("stock"),
      "price": price,
    })

  countries.sort(key=lambda c: (c.get("price") or 0, c.get("name") or ""))
  _s2_countries_cache["ts"] = now
  _s2_countries_cache["data"] = countries
  return countries


def find_s2_country(country_code, force_refresh=False):
  code = str(country_code or "").strip().upper()
  data = fetch_s2_countries(force_refresh)
  if isinstance(data, dict):
    return None
  for item in data:
    if item.get("code") == code:
      return item
  return None


def fetch_s1_country_detail(country_code, spam=None, force_refresh=False,
                            premium=None, email=None):
  """Live stock + price ladder for one country (Nobelots country detail)."""
  code = str(country_code or "").strip().upper()
  if not code:
    return {"error": "Invalid country."}
  qs_parts = []
  if str(spam).lower() in ("yes", "no"):
    qs_parts.append("spam=" + str(spam).lower())
  if str(premium).lower() in ("yes", "no"):
    qs_parts.append("premium=" + str(premium).lower())
  if str(email).lower() in ("yes", "no"):
    qs_parts.append("email=" + str(email).lower())
  qs = ("?" + "&".join(qs_parts)) if qs_parts else ""
  res = _nobelots_call(f"/servers/{NOBELOTS_API_SERVER}/countries/{quote(code)}{qs}")
  if not res.get("ok"):
    return {"error": _api_error_text(res)}
  try:
    stock = int(res.get("stock") or 0)
  except Exception:
    stock = 0
  try:
    price = float(res.get("from_price") or 0)
  except Exception:
    price = 0.0
  ladder = []
  for p in (res.get("price_ladder") or []):
    try:
      ladder.append(f"{float(p):.2f}".rstrip("0").rstrip("."))
    except Exception:
      ladder.append(str(p))
  return {
    "code": code,
    "name": clean_country_name(res.get("name") or code),
    "stock": stock,
    "price": price,
    "ladder": ladder,
    "stale": bool(res.get("stale")),
  }


# ---- Per-account listing for Server 1 ----------------------------------------
S1_ITEMS_PATH = "/servers/{server}/countries/{cc}/accounts"
S1_ITEMS_PER_PAGE = 20
_s1_items_cache = {}


def _parse_groups_channels(text):
  """Parse "0 Ch | 0 Grp | 0 Adm" into (channels, groups, admins)."""
  text = str(text or "")
  def grab(pattern):
    m = re.search(pattern, text, re.I)
    return int(m.group(1)) if m else 0
  return (grab(r'(\d+)\s*Ch'), grab(r'(\d+)\s*Grp'), grab(r'(\d+)\s*Adm'))


_MONTHS_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _fmt_api_date(v):
  """Turn an API date (ISO string / epoch / 'dd Mon yyyy') into '20 Sep 2026'."""
  if v in (None, "", False):
    return ""
  try:
    if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"\d{9,13}", v.strip())):
      ts = float(v)
      if ts > 1e11:
        ts /= 1000.0
      d = datetime.utcfromtimestamp(ts)
      return f"{d.day} {_MONTHS_SHORT[d.month - 1]} {d.year}"
    s = str(v).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
      y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
      return f"{da} {_MONTHS_SHORT[mo - 1]} {y}"
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
      da, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
      return f"{da} {_MONTHS_SHORT[mo - 1]} {y}"
    return s[:32]
  except Exception:
    return str(v)[:32]


def _extract_premium_end(it):
  """Find the premium expiry date in whatever shape the API sends it."""
  prem = it.get("premium")
  # premium may itself be an object: {"active": true, "expires_at": "..."}
  if isinstance(prem, dict):
    for k, v in prem.items():
      if re.search(r"end|expir|until|till|valid|date|exp", str(k), re.I) and v not in (None, "", False):
        return _fmt_api_date(v)
  if isinstance(prem, str):
    m = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{4}-\d{2}-\d{2})", prem)
    if m:
      return _fmt_api_date(m.group(1))
  for k, v in it.items():
    kl = str(k).lower()
    if "premium" in kl and re.search(r"end|expir|until|till|valid|date|exp", kl) and v not in (None, "", False):
      return _fmt_api_date(v)
  for k in ("premium_ends", "premium_end", "premium_expires", "premium_expiry",
            "premium_until", "premium_valid_till", "premium_expires_at", "premium_end_date"):
    if it.get(k) not in (None, "", False):
      return _fmt_api_date(it.get(k))
  return ""


def _norm_s1_item(it):
  if not isinstance(it, dict):
    return None
  iid = it.get("account_id") or it.get("item_id") or it.get("id")
  if iid in (None, ""):
    return None
  try:
    price = float(it.get("price") or 0)
  except Exception:
    price = 0.0
  ch, grp, adm = _parse_groups_channels(it.get("groups_channels"))
  return {
    "id": str(iid),
    "price": price,
    "premium": (it.get("premium").get("active", it.get("premium").get("is_premium"))
                if isinstance(it.get("premium"), dict) else it.get("premium")),
    "premium_end": _extract_premium_end(it),
    "raw": it,
    "channels": ch,
    "groups": grp,
    "admins": adm,
    "spam": it.get("spam"),
    "twofa": it.get("two_fa", it.get("twofa")),
    "email": it.get("email"),
    "uploaded": str(it.get("uploaded") or ""),
    "last_seen": str(it.get("last_seen") or ""),
    "origin": str(it.get("origin") or ""),
    "resale_origin": str(it.get("resale_origin") or ""),
    "dial": str(it.get("dial") or ""),
    "country": str(it.get("country") or ""),
    "name": str(it.get("name") or ""),
    "groups_channels": str(it.get("groups_channels") or ""),
  }


def fetch_s1_items(country_code, force_refresh=False, spam=None, limit=20,
                   premium=None, email=None):
  """List individual accounts for a country.

  Returns a list (possibly empty) on success, or {"error": "..."} on failure.
  """
  code = str(country_code or "").strip().upper()
  now = time.time()
  key = f"{code}|{spam or ''}|{premium or ''}|{email or ''}"
  c = _s1_items_cache.get(key)
  if c and not force_refresh and now - c["ts"] < 30:
    return c["data"]

  qs = f"?limit={max(1, min(int(limit or 20), 20))}"
  if str(spam).lower() in ("yes", "no"):
    qs += "&spam=" + str(spam).lower()
  if str(premium).lower() in ("yes", "no"):
    qs += "&premium=" + str(premium).lower()
  if str(email).lower() in ("yes", "no"):
    qs += "&email=" + str(email).lower()
  path = S1_ITEMS_PATH.format(server=NOBELOTS_API_SERVER, cc=quote(code)) + qs
  res = _nobelots_call(path)
  if not res.get("ok"):
    return {"error": _api_error_text(res)}
  raw = res.get("accounts")
  if not isinstance(raw, list):
    raw = res.get("data") if isinstance(res.get("data"), list) else []
  items = [x for x in (_norm_s1_item(i) for i in raw) if x]
  # The API may omit a flag once it has been used as a server-side filter.
  # An account returned for premium=yes IS premium (otherwise the account card
  # shows "Premium : No" while the Premium Only filter is on).
  for _it in items:
    if str(premium).lower() in ("yes", "no") and _it.get("premium") in (None, ""):
      _it["premium"] = "Yes" if str(premium).lower() == "yes" else "No"
    if str(spam).lower() in ("yes", "no") and _it.get("spam") in (None, ""):
      _it["spam"] = "Yes" if str(spam).lower() == "yes" else "No"
    if str(email).lower() in ("yes", "no") and _it.get("email") in (None, ""):
      _it["email"] = "Yes" if str(email).lower() == "yes" else "No"
  _s1_items_cache[key] = {"ts": now, "data": items}
  return items


# ---- Orders ------------------------------------------------------------------
FINAL_ORDER_STATUSES = {"completed", "partial", "failed", "cancelled", "interrupted"}


def create_nobelots_order(country_code=None, account_id=None, max_price=None,
                          spam=None, quantity=1, premium=None, email=None):
  """Create a Server 1 order. Returns the API response (202 body on success)."""
  payload = {}
  if account_id:
    payload["account_id"] = str(account_id)
  else:
    payload["server"] = NOBELOTS_API_SERVER
    payload["country"] = str(country_code or "").strip().upper()
    payload["quantity"] = max(1, int(quantity or 1))
  if max_price not in (None, ""):
    try:
      payload["max_price"] = f"{float(max_price):.2f}"
    except Exception:
      pass
  filters = {}
  if str(spam).lower() in ("yes", "no"):
    filters["spam"] = str(spam).lower()
  if str(premium).lower() in ("yes", "no"):
    filters["premium"] = str(premium).lower()
  if str(email).lower() in ("yes", "no"):
    filters["email"] = str(email).lower()
  if filters:
    payload["filters"] = filters
  return _nobelots_call("/orders", method="POST", payload=payload,
                        idempotency_key=str(uuid.uuid4()), timeout=45)


def wait_nobelots_order(batch_id, max_seconds=120):
  """Long-poll an order until it reaches a final status or time runs out."""
  batch_id = str(batch_id or "").strip()
  if not batch_id:
    return {"ok": False, "error": "bad_batch", "message": "Missing batch id."}
  deadline = time.time() + max(5, int(max_seconds or 120))
  last = None
  while True:
    remaining = deadline - time.time()
    if remaining <= 1:
      return last or {"ok": False, "error": "timeout",
                      "message": "The order is still processing."}
    wait_s = 15 if remaining > 18 else max(1, int(remaining))
    res = _nobelots_call(
      f"/orders/{quote(batch_id, safe='')}?wait={wait_s}",
      timeout=wait_s + 20,
    )
    if not res.get("ok"):
      if last:
        return last
      return res
    last = res
    if str(res.get("status") or "").lower() in FINAL_ORDER_STATUSES:
      return res


def fetch_s2_code(order_no):
  """Fetch the Telegram login code for a bought account."""
  return _nobelots_call(
    f"/accounts/{quote(str(order_no), safe='')}/code", method="POST", timeout=30)


def fetch_account_session(order_no):
  """Fetch a Telethon StringSession for a bought account."""
  return _nobelots_call(
    f"/accounts/{quote(str(order_no), safe='')}/session?format=string", timeout=30)


def fetch_phantom_balance(server_no=1):
  """Wallet + key info (GET /me). Name kept for the admin panel."""
  return _nobelots_call("/me", server_no=server_no)


async def safe_callback_answer(event, message=None, alert=False):
  """Safely acknowledge callback queries without swallowing later error messages."""
  try:
    already_answered = getattr(event, "_store_callback_answered", False)
    if already_answered:
      if message:
        try:
          await event.respond(str(message))
        except Exception:
          pass
      return
    setattr(event, "_store_callback_answered", True)
    await event.answer(message, alert=alert)
  except Exception:
    if message:
      try:
        await event.respond(str(message))
      except Exception:
        pass

_FREE_MAIL_DOMAINS = (
  'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.in', 'outlook.com',
  'hotmail.com', 'live.com', 'proton.me', 'protonmail.com', 'icloud.com',
  'rediffmail.com', 'mail.com', 'yandex.com', 'zoho.com',
)
_UTR_IN_PROGRESS = set()


async def check_payment_in_gmail_async(utr_to_find, gmail_user, gmail_pass,
                                       expected_amount=None, wait_seconds=0):
  """Verify a payment notification from Gmail IMAP (fast + safe).

  * ONE IMAP connection is reused; with wait_seconds > 0 the mailbox is polled
    every ~3s until the mail arrives, so a payment is credited the moment its
    email lands (no new login / full rescan per retry).
  * Search order per poll: Gmail X-GM-RAW (same index as the Gmail search box),
    IMAP TEXT, then a small "newest mails" scan as a last resort.
  * The UTR must literally appear in the mail body; the amount is read from the
    text around the UTR first, then from payment-labelled values.
  * Anti-fake: mails from free-mail senders (anyone can type a fake "payment"
    mail from their own Gmail) and mails whose SPF/DKIM explicitly failed are
    ignored. Optional admin setting `imap_trusted_senders` (comma separated
    substrings, e.g. "fampay,famapp") restricts matches to those senders.
  Returns the paid amount (float) or None.
  """
  def clean_text(value):
    if value is None:
      return ""
    if isinstance(value, (bytes, bytearray)):
      value = value.decode('utf-8', errors='ignore')
    value = html.unescape(str(value))
    value = re.sub(r'<(?:style|script)[^>]*>.*?</(?:style|script)>', ' ', value, flags=re.I | re.S)
    value = re.sub(r'<br\s*/?>', '\n', value, flags=re.I)
    value = re.sub(r'</(?:p|div|li|tr|td|h[1-6])>', ' \n', value, flags=re.I)
    value = re.sub(r'<[^>]+>', ' ', value)
    value = value.replace('\xa0', ' ').replace('\u200b', '')
    return re.sub(r'\s+', ' ', value).strip()

  def norm_ref(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())

  def extract_amounts(text):
    text = clean_text(text).upper()
    patterns = [
      r'(?:₹|RS\.?|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)',
      r'([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:₹|RS\b\.?|INR)',
      r'(?:AMOUNT\s*(?:PAID|RECEIVED|SENT|CREDITED)?|PAID|RECEIVED|CREDITED|TRANSACTION\s+AMOUNT|TRANSFERRED)\s*[:=-]?\s*(?:₹|RS\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)',
    ]
    vals = []
    for pat in patterns:
      for m in re.findall(pat, text, flags=re.I):
        try:
          v = float(str(m).replace(',', ''))
          if 0 < v < 100000000:
            vals.append(v)
        except Exception:
          pass
    return list(dict.fromkeys(vals))

  def decode_part(part):
    try:
      payload = part.get_payload(decode=True)
      if payload is None:
        payload = part.get_payload()
      charset = part.get_content_charset() or 'utf-8'
      if isinstance(payload, (bytes, bytearray)):
        try:
          return payload.decode(charset, errors='ignore')
        except LookupError:
          return payload.decode('utf-8', errors='ignore')
      return str(payload or '')
    except Exception:
      return str(part.get_payload() or '')

  def decode_header_text(value):
    try:
      from email.header import decode_header, make_header
      return str(make_header(decode_header(str(value or ''))))
    except Exception:
      return str(value or '')

  def message_text(msg):
    pieces = [decode_header_text(msg.get('Subject')), str(msg.get('From') or ''), str(msg.get('To') or '')]
    if msg.is_multipart():
      for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
          continue
        if (part.get_content_type() or '').lower() in ('text/plain', 'text/html'):
          pieces.append(decode_part(part))
    else:
      pieces.append(decode_part(msg))
    return clean_text('\n'.join(pieces))

  def sender_ok(msg, trusted):
    frm = str(msg.get('From') or '').lower()
    m = re.search(r'@([a-z0-9.\-]+)', frm)
    domain = m.group(1) if m else ''
    if trusted:
      return any(t in frm for t in trusted)
    if domain and any(domain == d or domain.endswith('.' + d) for d in _FREE_MAIL_DOMAINS):
      return False
    auth = ' '.join(str(h) for h in (msg.get_all('Authentication-Results') or [])).lower()
    if re.search(r'\b(?:dkim|spf|dmarc)=(?:fail|softfail|none)\b', auth) and 'dkim=pass' not in auth and 'spf=pass' not in auth:
      return False
    return True

  def pick_amount(body, utr_norm, expected):
    local = body
    try:
      flexible = r'[^A-Za-z0-9]{0,3}'.join(re.escape(c) for c in utr_norm)
      m = re.search(flexible, body, flags=re.I)
      if m:
        local = body[max(0, m.start() - 400):m.end() + 400]
    except Exception:
      pass
    amounts = extract_amounts(local) or extract_amounts(body)
    if not amounts:
      return None
    if expected is None:
      return max(amounts)
    exact = [a for a in amounts if abs(a - expected) < 0.01]
    if exact:
      return exact[0]
    sufficient = [a for a in amounts if a + 0.01 >= expected]
    if sufficient:
      return min(sufficient)
    return None

  def fetch_sync():
    mail = None
    try:
      user = (gmail_user or '').strip()
      password = re.sub(r'\s+', '', (gmail_pass or '').strip())
      if not user or not password:
        logger.error('Payment verification: Gmail credentials are missing.')
        return None
      server_row = cur.execute("SELECT value FROM settings WHERE key='imap_server'").fetchone()
      server = (server_row[0].strip() if server_row and server_row[0] else 'imap.gmail.com')
      if not re.fullmatch(r'[A-Za-z0-9._-]+', server):
        server = 'imap.gmail.com'
      tr_row = cur.execute("SELECT value FROM settings WHERE key='imap_trusted_senders'").fetchone()
      trusted = [x.strip().lower() for x in (tr_row[0] if tr_row and tr_row[0] else '').split(',') if x.strip()]
      utr_norm = norm_ref(utr_to_find)
      if len(utr_norm) < 6:
        return None
      expected = float(expected_amount) if expected_amount is not None else None
      raw_utr = str(utr_to_find).replace('"', '').replace('\\', '').strip()
      terms = [t for t in dict.fromkeys([raw_utr, utr_norm]) if t]

      mail = imaplib.IMAP4_SSL(server, 993, timeout=30)
      mail.login(user, password)
      is_gmail = 'gmail' in server or 'google' in server

      folders = []
      for f in ('INBOX', '[Gmail]/All Mail', '[Google Mail]/All Mail', '[Gmail]/Spam', '[Google Mail]/Spam'):
        try:
          st, _ = mail.select(f, readonly=True)
          if st == 'OK':
            folders.append(f)
        except Exception:
          pass
      # All Mail already contains INBOX + Spam; keep it first-class but still
      # check INBOX first because it is the fastest for fresh mail.
      if not folders:
        folders = ['INBOX']

      checked = set()
      deadline = time.time() + max(0, int(wait_seconds or 0))
      poll = 0
      while True:
        poll += 1
        for folder in folders:
          try:
            st, _ = mail.select(folder, readonly=True)
            if st != 'OK':
              continue
            ids = []
            for term in terms:
              if is_gmail:
                try:
                  st, data = mail.search(None, 'X-GM-RAW', f'"{term}"')
                  if st == 'OK' and data and data[0]:
                    ids += data[0].split()
                except Exception:
                  pass
              try:
                st, data = mail.search(None, 'TEXT', f'"{term}"')
                if st == 'OK' and data and data[0]:
                  ids += data[0].split()
              except Exception:
                pass
            if not ids:
              # Last resort: newest mails of the last 2 days (index lag).
              since = (datetime.utcnow() - timedelta(days=2)).strftime('%d-%b-%Y')
              st, data = mail.search(None, 'SINCE', since)
              if st == 'OK' and data and data[0]:
                ids = data[0].split()[-60:]
            for mid in reversed(list(dict.fromkeys(ids))[-100:]):
              key = (folder, mid)
              if key in checked:
                continue
              try:
                st, data = mail.fetch(mid, '(BODY.PEEK[])')
                if st != 'OK':
                  continue
                rawparts = [x[1] for x in data if isinstance(x, tuple) and len(x) > 1]
                if not rawparts:
                  continue
                msg = email.message_from_bytes(b''.join(rawparts))
                body = message_text(msg)
                if utr_norm not in norm_ref(body):
                  checked.add(key)
                  continue
                if not sender_ok(msg, trusted):
                  logger.info('Payment verification: ignored mail from untrusted sender %s', msg.get('From'))
                  checked.add(key)
                  continue
                amount = pick_amount(body, utr_norm, expected)
                if amount is not None:
                  logger.info('Payment verification: UTR %s matched, amount %.2f (poll %d)', utr_to_find, amount, poll)
                  return amount
                checked.add(key)
              except Exception as ex:
                logger.warning('IMAP message parse failed: %s', ex)
          except Exception as ex:
            logger.warning('IMAP search failed for %s: %s', folder, ex)
        if time.time() >= deadline:
          break
        time.sleep(3)
        try:
          mail.noop()
        except Exception:
          pass
      logger.info('Payment verification: no matching Gmail payment found for UTR %s', utr_to_find)
      return None
    except imaplib.IMAP4.error as ex:
      logger.error('Payment verification IMAP login/protocol error (check App Password / IMAP enabled): %s', ex)
      return None
    except Exception as ex:
      logger.error('Payment verification IMAP error: %s: %s', type(ex).__name__, ex)
      return None
    finally:
      if mail is not None:
        try: mail.logout()
        except Exception: pass

  return await asyncio.to_thread(fetch_sync)

def to_usd(inr):
  return round(inr / get_usdt_rate(), 2)

def is_user_banned(uid):
  res = cur.execute("SELECT banned FROM users WHERE user_id=?", (uid,)).fetchone()
  return res and res[0] == 1

def update_balance(uid, amount):
  cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
  db.commit()

# ================= FULL BACKUP / RESTORE (script + database + sessions) =================
DB_FILE = "otp_bot_final.db"
SCRIPT_PATH = os.path.abspath(__file__)
BACKUP_EXTRA_FILES = ["23593.jpg"]   # welcome photo
BACKUP_DIRS = ["sessions"]           # all stock .session files

def _restore_path_ok(rel):
  rel = str(rel).replace("\\", "/")
  if not rel or rel.startswith("/") or ".." in rel.split("/"):
    return False
  return rel in BACKUP_EXTRA_FILES or any(rel.startswith(d + "/") for d in BACKUP_DIRS)

def build_full_backup():
  """Create ONE zip: bot script + database snapshot + sessions + welcome photo."""
  ts = datetime.now().strftime('%Y%m%d_%H%M%S')
  zip_path = f"full_backup_{ts}.zip"
  snap = f"_db_snapshot_{ts}.db"
  try:
    db.commit()
    dst = sqlite3.connect(snap)
    try:
      db.backup(dst)
    finally:
      dst.close()
    n_files = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
      zf.write(SCRIPT_PATH, "bot_script.py")
      zf.write(snap, DB_FILE)
      for extra in BACKUP_EXTRA_FILES:
        if os.path.isfile(extra):
          zf.write(extra, "files/" + extra); n_files += 1
      for d in BACKUP_DIRS:
        for root, _, files in os.walk(d):
          for fn in files:
            full = os.path.join(root, fn)
            zf.write(full, "files/" + os.path.relpath(full).replace(os.sep, "/")); n_files += 1
      zf.writestr("backup_info.json", json.dumps({
        "created": ts, "script": os.path.basename(SCRIPT_PATH), "db": DB_FILE, "files": n_files}))
  finally:
    try: os.remove(snap)
    except Exception: pass
  return zip_path, n_files

def restore_full_backup(zip_path):
  """Restore script + database + sessions from a full backup zip. Returns (n_files, script_changed)."""
  ts = datetime.now().strftime('%Y%m%d_%H%M%S')
  work = f"_restore_{ts}"
  os.makedirs(work, exist_ok=True)
  try:
    if not zipfile.is_zipfile(zip_path):
      raise ValueError("This is not a valid backup zip.")
    with zipfile.ZipFile(zip_path) as zf:
      names = zf.namelist()
      if "bot_script.py" not in names or DB_FILE not in names:
        raise ValueError("Not a full backup (bot_script.py / database missing).")
      for info in zf.infolist():
        name = info.filename
        if name.endswith("/"): continue
        ok = name in ("bot_script.py", DB_FILE, "backup_info.json") or (
          name.startswith("files/") and _restore_path_ok(name[6:]))
        if not ok: continue
        target = os.path.realpath(os.path.join(work, name))
        if not target.startswith(os.path.realpath(work) + os.sep): continue
        zf.extract(info, work)

    new_script = os.path.join(work, "bot_script.py")
    new_db = os.path.join(work, DB_FILE)
    with open(new_script, "r", encoding="utf-8") as f:
      try: compile(f.read(), "bot_script.py", "exec")
      except SyntaxError as ex: raise ValueError(f"Script in backup is broken: {ex}")
    chk = sqlite3.connect(new_db)
    try:
      if chk.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Database in backup is corrupted.")
      tables = {r[0] for r in chk.execute("SELECT name FROM sqlite_master WHERE type='table'")}
      if not {"users", "settings"} <= tables:
        raise ValueError("Database in backup has no users/settings tables.")
    finally:
      chk.close()

    # Safety copies of the current state (kept on the server).
    db.commit()
    safety = sqlite3.connect(f"pre_restore_{ts}.db")
    try: db.backup(safety)
    finally: safety.close()
    try: shutil.copyfile(SCRIPT_PATH, SCRIPT_PATH + ".pre_restore.bak")
    except Exception: pass

    # Database -> straight into the live connection.
    src = sqlite3.connect(new_db)
    try: src.backup(db)
    finally: src.close()
    db.commit()

    # Sessions + welcome photo.
    n_files = 0
    files_root = os.path.join(work, "files")
    for root, _, files in os.walk(files_root):
      for fn in files:
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, files_root).replace(os.sep, "/")
        if not _restore_path_ok(rel): continue
        os.makedirs(os.path.dirname(rel) or ".", exist_ok=True)
        shutil.copy2(full, rel); n_files += 1

    # Script last.
    shutil.copyfile(new_script, SCRIPT_PATH)
    return n_files
  finally:
    shutil.rmtree(work, ignore_errors=True)

def _restart_bot():
  os.execv(sys.executable, [sys.executable] + sys.argv)

def delete_session_files(session_path):
  base = session_path if not session_path.endswith('.session') else session_path[:-8]
  for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
    try:
      if os.path.exists(base + ext): os.remove(base + ext)
    except: pass

async def _get_channel_entity(channel_id):
  """Resolve a configured channel ID safely for both public/private channels."""
  raw = str(channel_id or '').strip()
  if not raw:
    raise ValueError("Channel ID is empty")
  try:
    target = int(raw)
  except ValueError:
    target = raw
  return await bot.get_input_entity(target)

async def _is_bot_channel_admin(channel_id):
  """Return (ok, reason) after checking that THIS bot is admin/creator in the channel."""
  try:
    channel = await _get_channel_entity(channel_id)
    me = await bot.get_me()
    result = await bot(GetParticipantRequest(channel=channel, participant=me.id))
    participant = getattr(result, 'participant', result)
    if isinstance(participant, ChannelParticipantCreator):
      return True, ""
    if isinstance(participant, ChannelParticipantAdmin):
      rights = getattr(participant, 'admin_rights', None)
      # Telegram exposes invite_users for the permission needed to create an invite link.
      if rights is not None and getattr(rights, 'invite_users', None) is False:
        return False, 'The bot is an admin, but "Invite Users via Link" permission is disabled.'
      return True, ""
    return False, "The bot is in the channel, but it is not an admin."
  except UserNotParticipantError:
    return False, "The bot is not a member/admin of this channel."
  except ChatAdminRequiredError:
    return False, "Telegram did not allow the bot to inspect this channel. Make the bot an admin first."
  except Exception as ex:
    logger.error(f"Force channel admin check failed for {channel_id}: {ex}")
    return False, f"Could not verify this channel: {ex}"

async def _validate_force_invite_url(raw_url):
  """Accept only a real Telegram URL suitable for a Join button."""
  normalized = _normalize_tg_url(raw_url, "")
  if not normalized:
    return ""
  # Force-join links may be public channel URLs or private +invite links.
  if not re.match(r"^https?://(?:t\.me|telegram\.me)/(?:\+[^\s<>]+|[A-Za-z0-9_][^\s<>]*)$", normalized, re.IGNORECASE):
    return ""
  return normalized

async def _create_force_channel_invite(channel_id):
  """Create a Telegram invite link automatically for a verified channel."""
  try:
    channel = await _get_channel_entity(channel_id)
    result = await bot(ExportChatInviteRequest(peer=channel))
    link = getattr(result, 'link', '') or ''
    link = await _validate_force_invite_url(link)
    if not link:
      return False, '', 'Telegram returned an invalid invite link.'
    return True, link, ''
  except ChatAdminRequiredError:
    return False, '', 'Bot is admin, but Telegram has not granted it permission to create invite links. Enable the channel permission "Invite Users via Link".'
  except Exception as ex:
    logger.error(f"Force channel invite creation failed for {channel_id}: {ex}", exc_info=True)
    return False, '', f'Could not create invite link: {ex}'

async def check_channel_joined(uid):
  if is_admin(uid): return True
  rows = cur.execute("SELECT channel_id FROM force_channels").fetchall()
  if not rows: return True

  for (ch,) in rows:
    ch_key = str(ch).strip()
    # Pending join request (request-approval invite links) counts as joined.
    pending = cur.execute(
      "SELECT 1 FROM force_join_requests WHERE channel_id=? AND user_id=?",
      (ch_key, int(uid))).fetchone()
    try:
      channel = await _get_channel_entity(ch)
      try: user = await bot.get_input_entity(uid)
      except Exception: user = await bot.get_entity(uid)
      await bot(GetParticipantRequest(channel=channel, participant=user))
      # Real member now -> the stored request is no longer needed.
      if pending:
        cur.execute("DELETE FROM force_join_requests WHERE channel_id=? AND user_id=?", (ch_key, int(uid)))
        db.commit()
    except (UserNotParticipantError, ValueError):
      if not pending:
        return False
    except Exception as e:
      logger.error(f"Channel Check Error: {e}")
      if not pending:
        return False
  return True

@bot.on(events.Raw)
async def _force_join_request_tracker(update):
  """Remember users who sent a join request to a force-join channel so the
  force-join check accepts them (joined members are checked via GetParticipant)."""
  try:
    from telethon.tl.types import UpdateBotChatInviteRequester
    if not isinstance(update, UpdateBotChatInviteRequester):
      return
    from telethon import utils as _tl_utils
    ch_key = str(_tl_utils.get_peer_id(update.peer))
    known = cur.execute("SELECT 1 FROM force_channels WHERE channel_id=?", (ch_key,)).fetchone()
    if not known:
      return
    cur.execute("INSERT OR IGNORE INTO force_join_requests (channel_id, user_id) VALUES (?,?)",
                (ch_key, int(update.user_id)))
    db.commit()
  except Exception as ex:
    logger.error(f"Join request tracker error: {ex}")

COUNTRY_CODES = {
  '1': 'USA/Canada', '7': 'Russia', '20': 'Egypt', '27': 'South Africa',
  '31': 'Netherlands', '32': 'Belgium', '33': 'France', '34': 'Spain',
  '39': 'Italy', '44': 'UK', '46': 'Sweden', '48': 'Poland',
  '49': 'Germany', '51': 'Peru', '52': 'Mexico', '54': 'Argentina',
  '55': 'Brazil', '56': 'Chile', '57': 'Colombia', '58': 'Venezuela',
  '60': 'Malaysia', '61': 'Australia', '62': 'Indonesia', '63': 'Philippines', 
  '66': 'Thailand', '84': 'Vietnam', '86': 'China', '90': 'Turkey',
  '91': 'India', '92': 'Pakistan', '93': 'Afghanistan', '94': 'Sri Lanka',
  '95': 'Myanmar', '98': 'Iran', '212': 'Morocco', '213': 'Algeria',
  '234': 'Nigeria', '254': 'Kenya', '255': 'Tanzania', '380': 'Ukraine',
  '880': 'Bangladesh', '964': 'Iraq', '966': 'Saudi Arabia', '971': 'UAE',
  '998': 'Uzbekistan'
}

def get_country_info(phone):
  phone = str(phone).replace(' ', '').replace('+', '')
  if not phone: return "Unknown"
  
  try:
    customs = cur.execute("SELECT code, name FROM custom_countries").fetchall()
    customs.sort(key=lambda x: len(x[0]), reverse=True)
    for code, name in customs:
      if phone.startswith(code): return name
  except: pass

  for length in (3, 2, 1):
    prefix = phone[:length]
    if prefix in COUNTRY_CODES: return COUNTRY_CODES[prefix]
  return "Unknown"

async def detect_account_year(client):
  year = 2024
  try:
    try: await client.delete_dialog('TGDNAbot')
    except: pass
    await client.send_message('TGDNAbot', '/start')
    me = await client.get_me()
    await asyncio.sleep(1)
    await client.send_message('TGDNAbot', str(me.id)) 
    for _ in range(8):
      await asyncio.sleep(1.5)
      msgs = await client.get_messages('TGDNAbot', limit=3)
      for m in msgs:
        if m.text and ('Created:' in m.text or 'Age:' in m.text or 'Registration' in m.text):
          match = re.search(r'(?:Created|Age|Registration)[^\d]*(\d{4})', m.text, re.IGNORECASE)
          if match: return int(match.group(1))
  except Exception: pass
  return year

def _spoiler(value):
  """Hide sensitive values in Telegram logs using Telegram spoiler formatting."""
  return f"<tg-spoiler>{html.escape(str(value))}</tg-spoiler>"

async def _get_bot_buy_button():
  try:
    bot_info = await bot.get_me()
    username = getattr(bot_info, 'username', None)
    if username:
      return [[Button.url("Buy Now", f"https://t.me/{username}")]]
  except Exception as ex:
    logger.error(f"Failed to build Buy Now button: {ex}")
  return None

async def _send_selling_log(msg):
  try:
    buttons = await _get_bot_buy_button()
    await bot.send_message(
      get_log_channel_id(),
      custom_emoji_text(msg),
      buttons=buttons,
      parse_mode='html'
    )
    return True
  except Exception as ex:
    logger.error(f"Selling log send failed: {ex}")
    return False

async def _user_label(uid):
  """@username (or name) for admin messages."""
  try:
    user = await bot.get_entity(int(uid))
    if getattr(user, 'username', None):
      return '@' + user.username
    return getattr(user, 'first_name', None) or 'NoUsername'
  except Exception:
    return 'NoUsername'


async def notify_admins(msg):
  """DM the owner + every sub-admin (full, un-hidden details)."""
  for admin_id in get_all_admin_ids():
    try:
      await bot.send_message(int(admin_id), custom_emoji_text(msg), parse_mode='html')
    except Exception as ex:
      logger.error(f"Admin notify failed for {admin_id}: {ex}")


async def log_primary_deposit(uid, amt, method):
  """Successful deposit log only. User id, username and any link/number stay hidden."""
  try:
    username = await _user_label(uid)
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = (
      f"{P_YES} {P_FIRE} <b>NEW DEPOSIT SUCCESSFUL</b> {P_PARTY}\n\n"
      f"{P_ACC} User ID: {_spoiler(uid)}\n"
      f"{P_ACC} Username: {_spoiler(username)}\n"
      f"{P_MONEY} Amount: {P_INR}{amt}\n"
      f"{P_CARD} Method: <b>{html.escape(str(method))}</b>\n"
      f"{P_TIME} Time: {t}\n\n"
      f"<i>{P_STAR} Deposit confirmed successfully. {P_STAR}</i>"
    )
    await _send_selling_log(msg)
  except Exception as ex:
    logger.error(f"Global Dep Log Err: {ex}", exc_info=True)

async def log_primary_deposit_success(uid, amt, method, utr=None):
  # Channel: no UTR. Admins: full details (UTR included) for every auto-verified deposit.
  await log_primary_deposit(uid, amt, method)
  try:
    row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    bal = row[0] if row else 0
    await notify_admins(
      f"{P_YES} {P_MONEY} <b>AUTO DEPOSIT VERIFIED</b> {P_PARTY}\n\n"
      f"{P_ACC} User: <code>{uid}</code> ({html.escape(await _user_label(uid))})\n"
      f"{P_MONEY} Amount: {P_INR}{amt:g}\n"
      f"{P_CARD} Method: <b>{html.escape(str(method))}</b>\n"
      f"{P_ID} UTR: <code>{html.escape(str(utr or '-'))}</code>\n"
      f"{P_CARD} New Balance: {P_INR}{float(bal or 0):g}\n"
      f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  except Exception as ex:
    logger.error(f"Deposit admin notify err: {ex}")

async def log_primary_purchase(uid, country, price, amount, year, qty, phone=None):
  try:
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = (
      f"{P_CART} {P_ROCKET} <b>NEW TELEGRAM ACCOUNT SALE</b> {P_PARTY}\n\n"
      f"{P_ID} User ID: {_spoiler(uid)}\n"
      f"{country_flag_html(None, country)} Country: {html.escape(str(country))}\n"
      f"{P_MONEY} Price: {P_INR}{price}\n"
      f"{P_CARD} Total Paid: {P_INR}{amount}\n"
      f"{P_CAL} Year: {year}\n"
      f"{P_PKG} Quantity: {qty}\n"
      f"{P_PHONE} Account Details: {_spoiler('Hidden / Delivered Privately')}\n"
      f"{P_TIME} Time: {t}"
    )
    await _send_selling_log(msg)
  except Exception as ex:
    logger.error(f"Purchase Log Err: {ex}", exc_info=True)
  try:
    await notify_admins(
      f"{P_CART} {P_ROCKET} <b>TELEGRAM ACCOUNT PURCHASED</b> {P_PARTY}\n\n"
      f"{P_ACC} User: <code>{uid}</code> ({html.escape(await _user_label(uid))})\n"
      f"{country_flag_html(None, country)} Country: {html.escape(str(country))} ({year})\n"
      f"{P_PHONE} Number: <code>{html.escape(str(phone or '-'))}</code>\n"
      f"{P_PKG} Qty: {qty}\n"
      f"{P_MONEY} Paid: {P_INR}{amount}\n"
      f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  except Exception as ex:
    logger.error(f"Purchase admin notify err: {ex}")

async def log_smm_sale(uid, service_name, bot_order_id, panel_order_id, link, quantity, total_price):
  link = clean_html_url(link)
  try:
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Channel log: the order LINK is never posted.
    msg = (
      f"{P_CART} {P_ROCKET} <b>NEW SMM ORDER SALE</b> {P_PARTY}\n\n"
      f"{P_ID} User ID: {_spoiler(uid)}\n"
      f"{P_GEAR} Service: {html.escape(str(service_name))}\n"
      f"{P_PKG} Quantity: {quantity}\n"
      f"{P_MONEY} Total Paid: ₹{float(total_price):.4f}\n"
      f"{P_TIME} Time: {t}"
    )
    await _send_selling_log(msg)
  except Exception as ex:
    logger.error(f"SMM Sale Log Err: {ex}", exc_info=True)
  try:
    await notify_admins(
      f"{P_CART} {P_ROCKET} <b>SMM ORDER PLACED</b> {P_PARTY}\n\n"
      f"{P_ACC} User: <code>{uid}</code> ({html.escape(await _user_label(uid))})\n"
      f"{P_GEAR} Service: {html.escape(str(service_name))}\n"
      f"{P_ID} Bot Order ID: <code>{bot_order_id}</code>\n"
      f"{P_GEAR} Panel Order ID: <code>{html.escape(str(panel_order_id))}</code>\n"
      f"{P_LINK} Link: {html.escape(link)}\n"
      f"{P_PKG} Quantity: {quantity}\n"
      f"{P_MONEY} Paid: ₹{float(total_price):.4f}\n"
      f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  except Exception as ex:
    logger.error(f"SMM admin notify err: {ex}")

async def log_digital_sale(uid, product_name, price):
  try:
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = (
      f"{P_STORE} {P_ROCKET} <b>NEW DIGITAL PRODUCT SALE</b> {P_PARTY}\n\n"
      f"{P_ID} User ID: {_spoiler(uid)}\n"
      f"{P_DOC} Product: {html.escape(str(product_name))}\n"
      f"{P_MONEY} Total Paid: ₹{price}\n"
      f"{P_TIME} Time: {t}"
    )
    await _send_selling_log(msg)
  except Exception as ex:
    logger.error(f"Digital Sale Log Err: {ex}", exc_info=True)
  try:
    await notify_admins(
      f"{P_STORE} {P_ROCKET} <b>DIGITAL PRODUCT PURCHASED</b> {P_PARTY}\n\n"
      f"{P_ACC} User: <code>{uid}</code> ({html.escape(await _user_label(uid))})\n"
      f"{P_DOC} Product: {html.escape(str(product_name))}\n"
      f"{P_MONEY} Paid: ₹{price}\n"
      f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  except Exception as ex:
    logger.error(f"Digital admin notify err: {ex}")

async def log_wa_sale(uid, country, price, phone, act_id, order_id):
  try:
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cflag = country_flag_html(None, country.get("name"))
    msg = (
      f"{P_CART} {P_ROCKET} <b>NEW WHATSAPP ACCOUNT SALE</b> {P_PARTY}\n\n"
      f"{P_ID} User ID: {_spoiler(uid)}\n"
      f"{cflag} Country: {html.escape(str(country.get('name')))}\n"
      f"{P_PHONE} Number: {_spoiler(phone)}\n"
      f"{P_MONEY} Price: {P_INR}{price:.2f}\n"
      f"{P_TIME} Time: {t}"
    )
    await _send_selling_log(msg)
  except Exception as ex:
    logger.error(f"WA Sale Log Err: {ex}", exc_info=True)
  try:
    await notify_admins(
      f"{P_CART} {P_ROCKET} <b>WHATSAPP ACCOUNT PURCHASED</b> {P_PARTY}\n\n"
      f"{P_ACC} User: <code>{uid}</code> ({html.escape(await _user_label(uid))})\n"
      f"{country_flag_html(None, country.get('name'))} Country: {html.escape(str(country.get('name')))}\n"
      f"{P_PHONE} Number: <code>{html.escape(str(phone))}</code>\n"
      f"{P_MONEY} Paid: {P_INR}{price:.2f}\n"
      f"{P_ID} Activation: <code>{html.escape(str(act_id))}</code> | Order #{order_id}\n"
      f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  except Exception as ex:
    logger.error(f"WA admin notify err: {ex}")

# ================= PERSISTENT MENU =================
def get_persistent_menu(uid):
  # Support/Updates are direct URL buttons so they never depend on a callback
  # handler. Their destinations are controlled from the Admin Panel settings.
  support_url = get_support_url()
  updates_url = "https://t.me/+yhaYNpSyF5U3Y2Q9"
  # Support/Updates remain direct redirects when Admin has configured a valid
  # Telegram URL. If a URL has not been configured yet, use the callback
  # fallback instead of constructing an invalid Button.url (which crashes
  # the entire /start media send with ButtonUrlInvalidError).
  support_btn = (
    Button.url("Support", support_url)
    if _has_valid_button_url(support_url)
    else Button.inline("Support", data="cb_support")
  )
  updates_btn = (
    Button.url("Updates", updates_url)
    if _has_valid_button_url(updates_url)
    else Button.inline("Updates", data="cb_updates")
  )
  rows = [
    [
      Button.inline("Store", data="cb_store"),
      Button.inline("Add Funds", data="cb_addfunds")
    ],
    [
      Button.inline("Profile", data="cb_profile"),
      Button.inline("My Orders", data="cb_orders")
    ],
    [Button.inline("Redeem Code", data="redeem_start")],
    [Button.url("Selling Logs", get_selling_logs_link())],
    [support_btn],
    [updates_btn]
  ]
  return rows

async def send_main_menu(event, uid):
  ensure_user(uid)
  row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
  bal = row[0] if row else 0

  try:
    sender = await event.get_sender()
    user_name = html.escape(sender.first_name) if sender and sender.first_name else "User"
  except Exception:
    user_name = "User"

  # Keep the account summary together inside a Telegram quote block, matching
  # the requested UI. Custom-emoji constants remain inside the quoted lines.
  # Premium/custom-emoji styled welcome text. Every visual marker is a
  # Telegram custom emoji ID, including the quoted account summary.
  msg = (
    f"{P_DIAMOND} <b>Aaditya Tg Store</b> {P_STAR}\n"
    f"{P_TG} <b>Welcome back,</b> {P_ACC} <b>{user_name}</b> {P_LIGHTNING} {P_STAR}\n\n"
    f"<blockquote>"
    f"{P_MONEY} <b>Wallet Balance:</b> {P_INR}{bal:.2f} {P_USDT} (${to_usd(bal):.2f})\n"
    f"{P_ID} <b>Account UID:</b> <code>{uid}</code> {P_YES}\n"
    f"{P_CROWN} <b>Membership:</b> <b>Verified VIP</b> {P_YES}"
    f"</blockquote>\n"
    f"{P_STAR} <i>Your premium destination for fast, reliable, and automated account purchases.</i> {P_FIRE} {P_DIAMOND}"
  )

  img_path = "23593.jpg"
  buttons = get_persistent_menu(uid)
  rendered = custom_emoji_text(msg)

  if isinstance(event, events.CallbackQuery.Event):
    # "Back to Main" must always work, even when the current message is a
    # photo, the local banner file is missing, or Telegram refuses an edit.
    # Try in order: edit in place -> fresh photo -> fresh text -> alert.
    try:
      return await event.edit(rendered, buttons=buttons, parse_mode='html')
    except MessageNotModifiedError:
      return
    except Exception as ex:
      logger.warning(f"Main menu edit failed, sending fresh message: {ex}")

    sent = False
    if os.path.exists(img_path):
      try:
        await bot.send_file(uid, img_path, caption=rendered, buttons=buttons,
                            parse_mode='html')
        sent = True
      except Exception as ex:
        logger.warning(f"Main menu photo send failed, using text: {ex}")
    if not sent:
      try:
        await bot.send_message(uid, rendered, buttons=buttons, parse_mode='html')
        sent = True
      except Exception as ex:
        logger.error(f"Main menu text send failed: {ex}", exc_info=True)

    if sent:
      try:
        await event.delete()
      except Exception:
        pass
    else:
      await safe_callback_answer(
        event, "Could not open the main menu. Please send /start.", alert=True)
  else:
    if os.path.exists(img_path):
      try:
        return await event.respond(file=img_path, message=rendered,
                                   buttons=buttons, parse_mode='html')
      except Exception as ex:
        logger.warning(f"Main menu photo respond failed, using text: {ex}")
    return await event.respond(rendered, buttons=buttons, parse_mode='html')

async def store_servers_menu(event):
  """Open the Store menu reliably from both text and callback messages.

  The main menu is usually a photo message. Telegram cannot turn that media
  message into a normal text message with buttons reliably on every client,
  so callback navigation explicitly replaces the media message and falls
  back to a fresh message if the first send path fails.
  """
  msg = (
    f"{P_STORE} {P_ROCKET} <b>Aaditya Tg Store</b> {P_STAR}\n"
    f"────────────────\n\n"
    f"<b>Welcome to our digital marketplace!</b> {P_PARTY}\n\n"
    f"{P_YES} <b>Instant Delivery</b> {P_LIGHTNING}\n"
    f"{P_2FA} <b>Secure & Verified Stock</b> {P_DIAMOND}\n"
    f"{P_WAIT} <b>24×7 Automated Service</b> {P_TIME}\n\n"
    f"{P_ASST} Please select below to browse our available stock:"
  )
  btns = []
  if _fnm_on("server1"):
    btns.append([Button.inline("Server 1 [cheap account]", "srv1_accounts")])
  if _fnm_on("server2wa"):
    btns.append([Button.inline("Server 2 [ WhatsApp Accounts ]", "s2wa_countries")])
  if _fnm_on("srv3manual"):
    btns.append([Button.inline("Server 3 [ manually added accounts ]", "srv|manual")])
  if _fnm_on("shop"):
    btns.append([Button.inline("Shop", "digital_shop")])
  if _fnm_on("smm"):
    btns.append([Button.inline("Social Media Services", "cb_smm_services")])
  btns.append([Button.inline("Back to Main", "back_main")])
  rendered = custom_emoji_text(msg)

  if not isinstance(event, events.CallbackQuery.Event):
    return await event.respond(rendered, buttons=btns, parse_mode='html')

  try:
    if getattr(getattr(event, '_message', None), 'media', None):
      try:
        await event.delete()
      except Exception as ex:
        logger.warning(f"Store media delete failed: {ex}")
      try:
        return await event.respond(rendered, buttons=btns, parse_mode='html')
      except Exception as ex:
        logger.warning(f"Store event.respond failed: {ex}")
        return await bot.send_message(event.chat_id, rendered, buttons=btns, parse_mode='html')

    try:
      return await event.edit(rendered, buttons=btns, parse_mode='html')
    except MessageNotModifiedError:
      return
    except Exception as ex:
      logger.warning(f"Store event.edit failed: {ex}")
      return await event.respond(rendered, buttons=btns, parse_mode='html')
  except Exception as ex:
    logger.error(f"Store menu error: {ex}", exc_info=True)
    try:
      return await bot.send_message(event.chat_id, rendered, buttons=btns, parse_mode='html')
    except Exception as send_ex:
      logger.error(f"Store fallback send failed: {send_ex}", exc_info=True)
      await safe_callback_answer(event, "Store could not be opened. Please try /start again.", alert=True)


# ================= SERVER 1 STORE (NOBELOTS RESELLER API) =================
# UI + flow mirrors the "Aaditya Tg Store" mini-app shown in the reference video:
# Terms gate -> WALLET card -> country list (page/sort/search/filters) ->
# country detail (stock/from/page/Bulk Buy) -> ACCOUNT DETAILS -> Filters panel.
S1_PAGE_SIZE = 8
S1_FILTERS = {}
S1_SEARCH_STATE = {}
S1_FILTER_DEFAULTS = {
  "spam": "any", "premium": "any", "origin": "any",
  "email": "any", "search": "", "sort": "low", "cat": "",
}

# ---- Server 1 categories (Pushing / Premium / Autoreg) ----------------------
# push    = normal accounts (non-premium, non-autoreg)
# premium = Telegram Premium accounts only
# autoreg = auto-registered accounts (matched on the API "origin" text)
# If your API uses a different word for autoreg, add it to S1_AUTOREG_KEYWORDS.
S1_CATEGORIES = {
  "push":    {"label": "Pushing Account"},
  "premium": {"label": "Premium Account"},
  "autoreg": {"label": "Autoreg Account"},
}
S1_AUTOREG_KEYWORDS = ("autoreg", "auto reg", "auto-reg", "auto_reg")


def _s1_is_autoreg(it):
  blob = f"{it.get('origin','')} {it.get('resale_origin','')}".lower()
  return any(k in blob for k in S1_AUTOREG_KEYWORDS)


def _s1_cat_label(cat):
  return (S1_CATEGORIES.get(cat) or {}).get("label", "")


def _s1_set_category(f, cat):
  """Apply a category to a filter dict (premium category -> API premium filter)."""
  f["cat"] = cat if cat in S1_CATEGORIES else ""
  f["premium"] = "only" if cat == "premium" else "any"
  return f


def _s1_country_label(item, server_no=1):
  price = server_sell_price(item.get("price"), server_no)
  name = clean_country_name(item.get("name") or item.get("code"))
  label = f"{name} — ₹{price}"
  if len(label) > 48:
    label = label[:45] + "..."
  return label


def _s1_status_text(status):
  return {
    "queued": "Queued",
    "running": "Buying",
    "processing": "Processing",
    "completed": "Completed",
    "partial": "Partially Completed",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "interrupted": "Interrupted",
    "waiting": "Waiting for Code",
  }.get(str(status or "").lower(), str(status or "Waiting").title())


# ---- Terms gate --------------------------------------------------------------
def _s1_terms_accepted(uid):
  try:
    return cur.execute("SELECT 1 FROM s1_terms WHERE user_id=?", (uid,)).fetchone() is not None
  except Exception:
    return False


async def server1_terms(event):
  msg = (
    f"{P_STORE} <b>Aaditya Tg Store</b>\n"
    f"{P_ACC} <i>5000 monthly users</i>\n"
        f"────────────────\n\n"
    f"<b>before you buy:</b>\n"
    f"1. The account can get logged out at any time.\n"
    f"2. The OTP / login code may not arrive on some accounts.\n"
    f"3. The account can get frozen, limited or banned.\n\n"
    f"<b>NO REFUND</b>\n"
    f"No refund will be issued on Server 1 accounts under any circumstances. "
    f"This applies whether the OTP arrives or not, and whether the account logs out, "
    f"freezes, gets limited or banned, or anything else happens after purchase.\n\n"
    f"By tapping <b>Agree</b> you confirm that you have read and accepted all of the above."
  )
  btns = [
    [Button.inline("Agree and Continue", "srv1_agree")],
    [Button.inline("Decline", "srv1_decline")],
  ]
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_agree(event):
  uid = event.sender_id
  cur.execute("INSERT OR IGNORE INTO s1_terms (user_id) VALUES (?)", (uid,))
  db.commit()
  await safe_callback_answer(event, "Terms accepted. Welcome to Aaditya Tg Store!")
  return await server1_category_menu(event)


async def server1_category_menu(event):
  """Store -> Server 1 -> choose Pushing / Premium / Autoreg section."""
  uid = event.sender_id
  if not _s1_terms_accepted(uid):
    return await server1_terms(event)
  msg = (
    f"{P_STORE} <b>Server 1 [cheap account]</b>\n"
    f"────────────────\n\n"
    f"{_s1_wallet_card(uid)}\n"
    f"────────────────\n\n"
    f"{P_ASST} Please choose an account section:"
  )
  btns = [
    [Button.inline("Pushing Account", "srv1_cat|push")],
    [Button.inline("Premium Account", "srv1_cat|premium")],
    [Button.inline("Autoreg Account", "srv1_cat|autoreg")],
    [Button.inline("My Orders", "cb_orders")],
    [Button.inline("Back to Store", "store_servers")],
  ]
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_pick_category(event, cat):
  uid = event.sender_id
  if not _s1_terms_accepted(uid):
    return await server1_terms(event)
  cat = str(cat or "").strip().lower()
  if cat not in S1_CATEGORIES:
    return await safe_callback_answer(event, "Unknown section.", alert=True)
  f = _s1_filters(uid)
  _s1_set_category(f, cat)
  f["search"] = ""
  return await server1_countries_menu(event, 1)


async def server1_decline(event):
  await safe_callback_answer(event, "You must accept the terms to use Server 1.", alert=True)
  return await store_servers_menu(event)


# ---- Wallet / filter state ---------------------------------------------------
def _s1_wallet(uid):
  row = cur.execute("SELECT balance, total_deposited FROM users WHERE user_id=?", (uid,)).fetchone()
  balance = int(row[0] or 0) if row else 0
  deposited = int(row[1] or 0) if row else 0
  spent_row = cur.execute(
    "SELECT COALESCE(SUM(price),0) FROM s2_orders WHERE user_id=? AND charged=1", (uid,)).fetchone()
  spent = int(spent_row[0] or 0) if spent_row else 0
  return balance, deposited, spent


def _s1_wallet_card(uid):
  balance, deposited, spent = _s1_wallet(uid)
  return (
    f"{P_CARD} <b>WALLET</b>\n"
    f"{P_MONEY} Balance : ₹{balance}\n"
    f"{P_PKG} Deposited : ₹{deposited}\n"
    f"{P_STATS} Spent : ₹{spent}"
  )


_S1_FILTER_KEYS = ("spam", "premium", "origin", "email")


def _s1_norm_value(key, value):
  """Normalise a filter value to the canonical UI token.

  Accepts both UI tokens ("only", "free", "blocked", "required") and raw
  API-style values ("yes"/"no"/"true"/"false"/"1"/"0") so a value that
  leaks in from the API can never make the UI show the wrong label.
  """
  v = str(value if value is not None else "any").strip().lower()
  if key == "premium":
    return {"yes": "only", "true": "only", "1": "only", "premium": "only",
            "only": "only", "no": "any", "false": "any", "0": "any",
            "none": "any", "": "any", "any": "any"}.get(v, v or "any")
  if key == "email":
    return {"yes": "required", "true": "required", "1": "required",
            "required": "required", "no": "any", "false": "any", "0": "any",
            "none": "any", "": "any", "any": "any"}.get(v, v or "any")
  if key == "spam":
    return {"yes": "blocked", "true": "blocked", "blocked": "blocked",
            "spam blocked": "blocked", "no": "free", "false": "free",
            "free": "free", "spam free": "free", "temp": "temp",
            "temporary": "temp", "temporary spam": "temp", "none": "any",
            "": "any", "any": "any"}.get(v, v or "any")
  if key == "origin":
    return "any" if v in ("", "none", "any") else v
  return v


def _s1_filters(uid):
  f = S1_FILTERS.get(uid)
  if not isinstance(f, dict):
    f = dict(S1_FILTER_DEFAULTS)
    S1_FILTERS[uid] = f
  for k, v in S1_FILTER_DEFAULTS.items():
    f.setdefault(k, v)
  # Self-heal any legacy/API-style value that may already be stored.
  for k in _S1_FILTER_KEYS:
    f[k] = _s1_norm_value(k, f.get(k))
  return f


def _s1_api_params(f):
  """Map UI filter state -> (spam, premium, email) API query values."""
  spam = {"free": "no", "blocked": "yes"}.get(_s1_norm_value("spam", f.get("spam")))
  premium = "yes" if _s1_norm_value("premium", f.get("premium")) == "only" else None
  email = "yes" if _s1_norm_value("email", f.get("email")) == "required" else None
  return spam, premium, email


def _s1_filters_active(f):
  return (
    _s1_norm_value("spam", f.get("spam")) != "any"
    or _s1_norm_value("premium", f.get("premium")) != "any"
    or _s1_norm_value("origin", f.get("origin")) != "any"
    or _s1_norm_value("email", f.get("email")) != "any"
    or bool(str(f.get("search") or "").strip())
  )


def _s1_filter_value_label(key, value):
  value = _s1_norm_value(key, value)
  if key == "spam":
    return {"any": "Any", "free": "Spam Free", "blocked": "Spam Blocked",
            "temp": "Temporary Spam"}.get(value, "Any")
  if key == "premium":
    return {"any": "Any", "only": "Premium Only"}.get(value, "Any")
  if key == "origin":
    return "Any" if value == "any" else value.title()
  if key == "email":
    return {"any": "Any", "required": "Required"}.get(value, "Any")
  return value


def _s1_filter_summary(f):
  search = str(f.get("search") or "").strip()
  return (
    f"Spam : {_s1_filter_value_label('spam', f.get('spam'))}\n"
    f"Premium : {_s1_filter_value_label('premium', f.get('premium'))}\n"
    f"Origin : {_s1_filter_value_label('origin', f.get('origin'))}\n"
    f"Email : {_s1_filter_value_label('email', f.get('email'))}\n"
    f"Search : {search if search else '—'}"
  )


def _s1_truthy(v):
  """Best-effort boolean for API fields that arrive as Yes/No strings."""
  if v is None or v == "":
    return None
  if isinstance(v, bool):
    return v
  if isinstance(v, (int, float)):
    return v != 0
  s = str(v).strip().lower()
  if s in ("yes", "true", "1", "y", "on", "enabled", "premium", "premium only",
           "spam blocked", "blocked", "required", "active"):
    return True
  if s in ("no", "false", "0", "n", "off", "disabled", "none", "null", "n/a",
           "free", "spam free", "not checked"):
    return False
  return None


def _s1_apply_client_filters(items, f):
  origin = _s1_norm_value("origin", f.get("origin"))
  search = str(f.get("search") or "").strip().lower()
  premium_want = _s1_norm_value("premium", f.get("premium"))
  spam_want = _s1_norm_value("spam", f.get("spam"))
  email_want = _s1_norm_value("email", f.get("email"))
  cat = str(f.get("cat") or "")
  out = []
  for it in items:
    if cat == "autoreg" and not _s1_is_autoreg(it):
      continue
    if cat == "push" and (_s1_is_autoreg(it) or _s1_truthy(it.get("premium")) is True):
      continue
    if cat == "premium" and _s1_truthy(it.get("premium")) is False:
      continue
    if origin != "any":
      blob = f"{it.get('origin','')} {it.get('resale_origin','')}".lower()
      if origin not in blob:
        continue
    # Defensive client-side filtering: some countries do not support every
    # server-side filter, so enforce the selection locally as well. This is
    # what keeps "Premium Only" from ever showing a non-premium account.
    if premium_want == "only" and _s1_truthy(it.get("premium")) is False:
      continue
    if spam_want == "free" and _s1_truthy(it.get("spam")) is True:
      continue
    if spam_want == "blocked" and _s1_truthy(it.get("spam")) is False:
      continue
    if email_want == "required" and _s1_truthy(it.get("email")) is False:
      continue
    if search:
      blob = " ".join(str(it.get(k) or "") for k in (
        "id", "origin", "resale_origin", "uploaded", "last_seen", "dial",
        "name", "country")).lower()
      if search not in blob:
        continue
    out.append(it)
  return out


def _s1_detail(country_code, f, force_refresh=False):
  spam, premium, email = _s1_api_params(f)
  return fetch_s1_country_detail(country_code, spam, force_refresh, premium, email)


def _yn(v, unknown="N/A"):
  b = _s1_truthy(v)
  if b is None:
    return unknown
  return "Yes" if b else "No"


def _premium_text(it, f=None):
  """'Yes (ends 20 Sep 2026)' / 'Yes' / 'No' / 'N/A'. No date is shown for 'No'."""
  default = "N/A"
  if f is not None and _s1_norm_value("premium", f.get("premium")) == "only":
    default = "Yes"
  val = _yn(it.get("premium"), default)
  end = (it.get("premium_end") or "").strip()
  if val == "Yes" and end:
    return f"Yes (ends {html.escape(end)})"
  return val


# ---- Order persistence -------------------------------------------------------
def _s1_finalize_purchase(uid, batch_id, order, country_code, country_name, price):
  """Store a bought account and charge the user's wallet exactly once."""
  accounts = order.get("accounts") or []
  acc = accounts[0] if accounts else {}
  order_no = str(acc.get("order_no") or "")
  phone = str(acc.get("phone") or "")
  row = cur.execute("SELECT charged FROM s2_orders WHERE order_id=?", (batch_id,)).fetchone()
  if row is None:
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, uid))
    cur.execute(
      "INSERT INTO s2_orders (order_id, user_id, country_code, country_name, number, price, "
      "status, code, password, account_no, charged) VALUES (?,?,?,?,?,?,?,?,?,?,1)",
      (batch_id, uid, country_code, country_name, phone, price, "waiting", "", "", order_no))
  else:
    if not int(row[0] or 0):
      cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, uid))
    cur.execute(
      "UPDATE s2_orders SET number=?, price=?, status='waiting', account_no=?, charged=1 "
      "WHERE order_id=?",
      (phone, price, order_no, batch_id))
  db.commit()
  return order_no, phone


def _s1_finalize_bulk(uid, batch_id, order, country_code, country_name):
  """Store every delivered account of a bulk order, charging each exactly once."""
  created = []
  for acc in (order.get("accounts") or []):
    order_no = str(acc.get("order_no") or "")
    phone = str(acc.get("phone") or "")
    try:
      api_price = float(acc.get("price") or 0)
    except Exception:
      api_price = 0.0
    price = server_sell_price(api_price)
    row_id = f"{batch_id}#{order_no or phone}"
    if cur.execute("SELECT 1 FROM s2_orders WHERE order_id=?", (row_id,)).fetchone():
      continue
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, uid))
    cur.execute(
      "INSERT INTO s2_orders (order_id, user_id, country_code, country_name, number, price, "
      "status, code, password, account_no, charged) VALUES (?,?,?,?,?,?,?,?,?,?,1)",
      (row_id, uid, country_code, country_name, phone, price, "waiting", "", "", order_no))
    created.append({"row_id": row_id, "number": phone, "price": price, "order_no": order_no})
  db.commit()
  return created


def _s1_store_pending(uid, batch_id, country_code, country_name, price, status):
  # Never reset an existing row (and never reset its `charged` flag): a
  # pending update must not be able to re-enable a second charge later.
  cur.execute("UPDATE s2_orders SET status=? WHERE order_id=?",
              (status or "processing", batch_id))
  if cur.rowcount == 0:
    cur.execute(
      "INSERT INTO s2_orders (order_id, user_id, country_code, country_name, number, "
      "price, status, code, password, account_no, charged) VALUES (?,?,?,?,?,?,?,?,?,?,0)",
      (batch_id, uid, country_code, country_name, "", price, status or "processing", "", "", ""))
  db.commit()


# ---- Country list ------------------------------------------------------------
async def server1_countries_menu(event, page=1, force_refresh=False):
  """Store -> Server 1 -> WALLET card + live country list."""
  uid = event.sender_id
  if not _s1_terms_accepted(uid):
    return await server1_terms(event)

  data = await asyncio.to_thread(fetch_s2_countries, force_refresh)
  if isinstance(data, dict):
    msg = (
      f"{P_NO} <b>Server 1 [cheap account]</b>\n"
      f"────────────────\n\n"
      f"{P_WARN} Could not load the server right now.\n"
      f"<i>{html.escape(str(data.get('error') or 'Unknown error'))}</i>"
    )
    btns = [
      [Button.inline("Try Again", "srv1_ref")],
      [Button.inline("Back to Store", "store_servers")],
    ]
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)

  available = [c for c in data if c.get("code")]
  if not available:
    msg = (
      f"{P_STORE} <b>Aaditya Tg Store </b>\n"
      f"────────────────\n\n"
      f"{P_WARN} No countries are available right now. Please check back later."
    )
    btns = [
      [Button.inline("Refresh", "srv1_ref")],
      [Button.inline("Back to Store", "store_servers")],
    ]
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)

  f = _s1_filters(uid)
  if str(f.get("sort") or "low").lower() == "high":
    available.sort(key=lambda c: (float(c.get("price") or 0), c.get("name") or ""), reverse=True)
  else:
    available.sort(key=lambda c: (float(c.get("price") or 0), c.get("name") or ""))

  total = len(available)
  total_pages = max(1, (total + S2_COUNTRIES_PER_PAGE - 1) // S2_COUNTRIES_PER_PAGE)
  try:
    page = int(page or 1)
  except Exception:
    page = 1
  page = max(1, min(page, total_pages))
  start = (page - 1) * S2_COUNTRIES_PER_PAGE
  page_items = available[start:start + S2_COUNTRIES_PER_PAGE]

  stock_vals = [int(c.get("stock")) for c in available if c.get("stock") is not None]
  accounts_txt = f"{sum(stock_vals):,}" if stock_vals else "live"

  lines = []
  for item in page_items:
    ccode = str(item.get("code") or "").strip().upper()
    cname = clean_country_name(item.get("name") or ccode)
    cprice = server_sell_price(item.get("price"))
    lines.append(f"{country_flag_html(ccode, cname)} <b>{html.escape(cname)}</b> — from ₹{cprice}")
  country_block = "\n".join(lines)

  filter_line = f"\n{P_WARN} <b>Filters Active</b>" if _s1_filters_active(f) else ""
  if _s1_cat_label(f.get("cat")):
    filter_line = f"\n{P_DIAMOND} <b>Section:</b> {_s1_cat_label(f.get('cat'))}" + filter_line
  sort_label = ("Sort - Price - High to Low"
                if str(f.get("sort") or "low").lower() == "high"
                else "Sort - Price - Low to High")

  msg = (
    f"{P_STORE} <b>Aaditya Tg Store</b>\n"
    f"{P_ACC} <i>4,945 monthly users</i>\n"
        f"────────────────\n\n"
    f"{_s1_wallet_card(uid)}\n"
    f"────────────────\n\n"
    f"{P_PKG} <b>Accounts:</b> {accounts_txt} | <b>Countries:</b> {total}\n"
    f"{P_ASST} <b>Page:</b> {page} of {total_pages}{filter_line}\n\n"
    f"{country_block}"
  )

  btns = []
  for item in page_items:
    btns.append([Button.inline(
      _s1_country_label(item), f"srv1_c|{item.get('code')}",
      icon_custom_emoji_id=country_flag_icon_id(item.get("code"), item.get("name")))])

  nav = []
  if page > 1:
    nav.append(Button.inline("Prev", f"srv1_pg|{page-1}"))
  nav.append(Button.inline(f"{page}/{total_pages}", f"srv1_pg|{page}"))
  if page < total_pages:
    nav.append(Button.inline("Next", f"srv1_pg|{page+1}"))
  btns.append(nav)

  btns.append([Button.inline("Back", "srv1_accounts"),
               Button.inline("Search", "srv1_csearch"),
               Button.inline("Filters", "srv1_filters")])
  btns.append([Button.inline(sort_label, f"srv1_sort|{'low' if str(f.get('sort') or 'low').lower() == 'high' else 'high'}")])
  btns.append([Button.inline("My Orders", "cb_orders"),
               Button.inline("Add Funds", "cb_addfunds")])
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_set_sort(event, direction):
  uid = event.sender_id
  f = _s1_filters(uid)
  f["sort"] = "high" if str(direction).lower() == "high" else "low"
  await safe_callback_answer(event, f"Sorting: Price {'High to Low' if f['sort'] == 'high' else 'Low to High'}")
  return await server1_countries_menu(event, 1)


# ---- Country detail (stock + account list) ----------------------------------
async def server1_country_detail(event, country_code, page=1, force_refresh=False):
  uid = event.sender_id
  if not _s1_terms_accepted(uid):
    return await server1_terms(event)

  code = str(country_code or "").strip().upper()
  f = _s1_filters(uid)
  spam, premium, email = _s1_api_params(f)

  detail = await asyncio.to_thread(_s1_detail, code, f, force_refresh)
  if not isinstance(detail, dict) or detail.get("error"):
    return await safe_callback_answer(
      event, (detail or {}).get("error") or "This country is not available.", alert=True)

  items = await asyncio.to_thread(fetch_s1_items, code, force_refresh, spam, 20, premium, email)
  if isinstance(items, dict):
    return await e_edit_or_send(
      event,
      custom_emoji_text(f"{P_NO} <b>Could not load accounts</b>\n\n"
                        f"{P_WARN} {html.escape(str(items.get('error') or 'Unknown error'))}"),
      [[Button.inline("Try Again", f"srv1_ipr|{code}|1")],
       [Button.inline("Back", "srv1_countries")]])

  items = _s1_apply_client_filters(items or [], f)
  cname = clean_country_name(detail.get("name") or code)
  stock = int(detail.get("stock") or 0)

  if not items:
    msg = (
      f"{country_flag_html(code, cname)} <b>{html.escape(cname.upper())}</b>\n"
      f"{P_PKG} Stock : {stock}\n"
      f"{P_MONEY} From : ₹{server_sell_price(detail.get('price'))}\n\n"
      f"{P_WARN} No accounts match your current filters."
    )
    btns = [
      [Button.inline("Reset Filters", "srv1_freset")],
      [Button.inline("Back", "srv1_countries"),
       Button.inline("Filters", "srv1_filters")],
    ]
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)

  total = len(items)
  pages = max(1, (total + S1_PAGE_SIZE - 1) // S1_PAGE_SIZE)
  try:
    page = int(page or 1)
  except Exception:
    page = 1
  page = max(1, min(page, pages))
  chunk = items[(page - 1) * S1_PAGE_SIZE: page * S1_PAGE_SIZE]
  low = min(server_sell_price(i["price"]) for i in items)

  filter_line = f"\n{P_WARN} <b>Filters Active</b>" if _s1_filters_active(f) else ""
  msg = (
    f"{country_flag_html(code, cname)} <b>{html.escape(cname.upper())}</b>\n"
    f"{P_PKG} Stock : {stock}\n"
    f"{P_MONEY} From : ₹{low}\n"
    + (f"{P_DIAMOND} Section : {_s1_cat_label(f.get('cat'))}\n" if _s1_cat_label(f.get('cat')) else "") +
    f"{P_ASST} Page : {page} of {pages}{filter_line}\n"
    f"────────────────"
  )

  btns, pair = [], []
  for it in chunk:
    star = ""  # no star next to premium accounts (shown in account details instead)
    pair.append(Button.inline(
      f"₹{server_sell_price(it['price'])}{star}",
      f"srv1_i|{code}|{it['id']}|{page}",
      icon_custom_emoji_id=country_flag_icon_id(code, cname)))
    if len(pair) == 2:
      btns.append(pair)
      pair = []
  if pair:
    btns.append(pair)

  if pages > 1:
    start_pg = max(1, min(page - 3, pages - 6))
    btns.append([Button.inline(f"[{n}]" if n == page else str(n), f"srv1_ip|{code}|{n}")
                 for n in range(start_pg, min(pages, start_pg + 6) + 1)])

  if stock > 1:
    btns.append([Button.inline("Bulk Buy", f"srv1_bulk|{code}")])
  btns.append([Button.inline("Back", "srv1_countries"),
               Button.inline("Filters", "srv1_filters"),
               Button.inline("Refresh", f"srv1_ipr|{code}|{page}")])
  try:
    await e_edit_or_send(event, custom_emoji_text(msg), btns)
  except MessageNotModifiedError:
    pass


# ---- Server 1 session security ----------------------------------------------
# After a Telegram account is delivered, the account usually still has the
# seller's / provider's sessions logged in. This block logs in with the
# delivered StringSession, kills every *other* session ("Terminate All Other
# Sessions") and finally logs the bot's own session out ("Terminate Bot
# Session") so the buyer receives a completely clean account.
#
# Mode is controlled by the admin setting  s1_secure_mode :
#   others  -> terminate other sessions right after the purchase, and the bot
#              session after the login code has been delivered (default)
#   all     -> terminate everything right after the purchase
#   off     -> do nothing (old behaviour, session string stays valid)
try:
  cur.execute("ALTER TABLE s2_orders ADD COLUMN secured INTEGER DEFAULT 0")
  db.commit()
except Exception:
  pass


def _s1_secure_mode():
  try:
    mode = str(get_setting("s1_secure_mode", "others") or "others").strip().lower()
  except Exception:
    mode = "others"
  return mode if mode in ("others", "all", "off") else "others"


async def _s1_terminate_sessions(session_string, include_self=False):
  """Terminate sessions of a Telegram account.

  Returns (ok, terminated_count, note).  ``include_self`` also logs the bot's
  own session out, which invalidates the StringSession for good.
  """
  if not session_string:
    return False, 0, "no_session"
  if _TGStringSession is None or _TGGetAuthorizations is None:
    return False, 0, "telethon_sessions_unavailable"

  client = None
  try:
    client = TelegramClient(_TGStringSession(session_string), API_ID, API_HASH)
    await asyncio.wait_for(client.connect(), timeout=45)
    try:
      authorized = await asyncio.wait_for(client.is_user_authorized(), timeout=20)
    except Exception:
      authorized = False
    if not authorized:
      return False, 0, "session_not_authorized"

    killed = 0
    try:
      res = await asyncio.wait_for(client(_TGGetAuthorizations()), timeout=30)
      for auth in (getattr(res, "authorizations", None) or []):
        if getattr(auth, "current", False):
          continue
        try:
          await asyncio.wait_for(
            client(_TGResetAuthorization(hash=auth.hash)), timeout=20)
          killed += 1
        except Exception as ex:
          logger.warning("s1 reset authorization failed: %s", ex)
    except Exception as ex:
      logger.warning("s1 get authorizations failed: %s", ex)

    if include_self:
      try:
        await asyncio.wait_for(client.log_out(), timeout=30)
      except Exception as ex:
        logger.warning("s1 log_out failed: %s", ex)

    return True, killed, "ok"
  except Exception as ex:
    logger.warning("s1 terminate sessions failed: %s", ex)
    return False, 0, str(ex)[:90]
  finally:
    try:
      if client is not None:
        await client.disconnect()
    except Exception:
      pass


async def _s1_secure_order(order_id, include_self=False):
  """Fetch the delivered account session and terminate its sessions."""
  try:
    row = cur.execute(
      "SELECT account_no FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
  except Exception:
    row = None
  if not row or not row[0]:
    return False, 0, "no_account"
  account_no = str(row[0])

  try:
    res = await asyncio.to_thread(fetch_account_session, account_no)
  except Exception as ex:
    return False, 0, str(ex)[:90]
  if not isinstance(res, dict) or not res.get("ok"):
    return False, 0, _api_error_text(res) if isinstance(res, dict) else "session_fetch_failed"

  sess = str(res.get("string_session") or res.get("session") or res.get("string") or "").strip()
  if not sess:
    return False, 0, "session_empty"

  ok, killed, note = await _s1_terminate_sessions(sess, include_self=include_self)
  # One quick retry: a flaky network should never leave the seller's sessions
  # alive on a delivered account.
  if not ok and note not in ("telethon_sessions_unavailable", "no_session"):
    try:
      await asyncio.sleep(2)
      ok2, killed2, note2 = await _s1_terminate_sessions(
        sess, include_self=include_self)
      if ok2:
        ok, killed, note = ok2, killed2, note2
      else:
        note = note2
    except Exception as ex:
      logger.warning("s1 secure retry failed: %s", ex)
  try:
    flag = 2 if (ok and include_self) else (1 if ok else 0)
    cur.execute("UPDATE s2_orders SET secured=? WHERE order_id=?", (flag, order_id))
    db.commit()
  except Exception:
    pass
  return ok, killed, note


async def server1_secure_account(event, order_id):
  """Manual button: terminate every session (including the bot's own)."""
  uid = event.sender_id
  row = cur.execute(
    "SELECT user_id, number FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
  if not row:
    return await safe_callback_answer(event, "Order not found.", alert=True)
  if int(row[0]) != int(uid) and not is_admin(uid):
    return await safe_callback_answer(event, "This order belongs to another user.", alert=True)

  await safe_callback_answer(event, "Terminating sessions...", alert=False)
  ok, killed, note = await _s1_secure_order(order_id, include_self=True)

  if ok:
    msg = (
      f"{P_YES} <b>Account Secured</b>\n"
      f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
      f"{P_PHONE} <b>Number:</b> <code>{html.escape(str(row[1] or '-'))}</code>\n"
      f"{P_2FA} <b>Other sessions terminated:</b> {killed}\n"
      f"{P_2FA} <b>Bot session:</b> Terminated \u2705\n\n"
      f"{P_ASST} The account is now clean. Log in with the number and the "
      f"login code \u2014 nobody else can access it."
    )
  else:
    msg = (
      f"{P_WARN} <b>Could Not Secure The Account</b>\n"
      f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
      f"{P_PHONE} <b>Number:</b> <code>{html.escape(str(row[1] or '-'))}</code>\n"
      f"{P_NO} <b>Reason:</b> <code>{html.escape(str(note))}</code>\n\n"
      f"{P_ASST} Try again in a few seconds, or contact support."
    )

  btns = [
    [Button.inline("Try Again", f"srv1_sec|{order_id}")],
    [Button.inline("Check Code", f"srv1_code|{order_id}")],
    [Button.inline("My Orders", "cb_orders")],
    [Button.inline("Back to Store", "store_servers")],
  ]
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


# ---- Account details ---------------------------------------------------------
async def server1_item_detail(event, country_code, item_id, page=1):
  uid = event.sender_id
  if not _s1_terms_accepted(uid):
    return await server1_terms(event)

  code = str(country_code or "").strip().upper()
  f = _s1_filters(uid)
  spam, premium, email = _s1_api_params(f)
  items = await asyncio.to_thread(fetch_s1_items, code, True, spam, 20, premium, email)
  if isinstance(items, dict):
    items = []
  # Keep the detail page consistent with the list page: the same client-side
  # filter guard is applied, so a non-premium account can never appear while
  # the "Premium Only" filter is active.
  items = _s1_apply_client_filters(items or [], f)
  it = next((i for i in (items or []) if i["id"] == str(item_id)), None)
  back = [Button.inline("Back", f"srv1_ip|{code}|{page}")]
  if not it:
    return await e_edit_or_send(
      event, custom_emoji_text(f"{P_NO} <b>This account is no longer available.</b>"), [back])

  detail = await asyncio.to_thread(_s1_detail, code, f)
  cname = clean_country_name((detail or {}).get("name") or code)
  dial = it.get("dial") or (detail or {}).get("dial") or ""
  dial_txt = f"{code}{dial}" if dial else code
  price = server_sell_price(it["price"])
  origin = it.get("origin") or "Mixed"
  resale_origin = it.get("resale_origin") or "—"

  msg = (
    f"{P_CROWN} <b>ACCOUNT DETAILS</b>\n"
    f"────────────────\n\n"
    f"{P_GLOBE} <b>Country :</b> {country_flag_html(code, cname)} {html.escape(cname)} ({dial_txt})\n"
    f"{P_MONEY} <b>Price :</b> ₹{price}\n"
    f"{P_CARD} <b>Origin :</b> {html.escape(str(origin))}\n"
    f"{P_CARD} <b>Resale Origin :</b> {html.escape(str(resale_origin))}\n"
    f"{P_TIME} <b>Uploaded :</b> {html.escape(it.get('uploaded') or 'N/A')}\n"
    f"{P_TIME} <b>Last Seen :</b> {html.escape(it.get('last_seen') or 'N/A')}\n"
    f"{P_CROWN} <b>Premium :</b> {_premium_text(it, f)}\n"
    f"{P_ACC} <b>Groups/Ch :</b> {it.get('channels', 0)}Ch|{it.get('groups', 0)}Grp|{it.get('admins', 0)} Adm\n"
    f"{P_WARN} <b>Spam :</b> {_yn(it.get('spam'))}\n"
    f"{P_2FA} <b>2FA :</b> {_yn(it.get('twofa'))}\n"
    f"{P_ASST} <b>Email :</b> {_yn(it.get('email'))}"
  )
  btns = [
    [Button.inline(f"Buy Now — ₹{price}", f"srv1_buy|{code}|{it['id']}")],
    back + [Button.inline("Refresh", f"srv1_i|{code}|{it['id']}|{page}")],
  ]
  try:
    await e_edit_or_send(event, custom_emoji_text(msg), btns)
  except MessageNotModifiedError:
    pass


# ---- Single buy --------------------------------------------------------------
async def server1_buy_number(event, country_code, item_id=None):
  uid = event.sender_id
  code = str(country_code or "").strip().upper()
  f = _s1_filters(uid)
  spam, premium, email = _s1_api_params(f)
  lock = get_user_lock(uid)

  if lock.locked():
    return await safe_callback_answer(
      event, "Please wait, your previous request is still processing.", alert=True)

  async with lock:
    await safe_callback_answer(event, "Buying account...", alert=False)

    api_price = None
    if item_id:
      listed = await asyncio.to_thread(fetch_s1_items, code, True, spam, 20, premium, email)
      if isinstance(listed, dict):
        return await e_edit_or_send(
          event,
          custom_emoji_text(f"{P_NO} <b>Could not load this account.</b>\n\n"
                            f"{P_WARN} {html.escape(str(listed.get('error') or 'Unknown error'))}"),
          [[Button.inline("Back", f"srv1_ip|{code}|1")]])
      pick = next((i for i in (listed or []) if i["id"] == str(item_id)), None)
      if not pick:
        return await e_edit_or_send(
          event,
          custom_emoji_text(f"{P_NO} <b>This account was just sold.</b> Please pick another."),
          [[Button.inline("Back", f"srv1_ip|{code}|1")]])
      api_price = float(pick["price"])
      spam = premium = email = None  # exact account id decides the filters
    else:
      detail = await asyncio.to_thread(_s1_detail, code, f)
      if not isinstance(detail, dict) or detail.get("error"):
        return await e_edit_or_send(
          event,
          custom_emoji_text(f"{P_NO} <b>This country is not available right now.</b>\n\n"
                            f"{P_WARN} {html.escape(str((detail or {}).get('error') or 'Unknown error'))}"),
          [[Button.inline("Back", "srv1_countries")]])
      if int(detail.get("stock") or 0) <= 0:
        return await e_edit_or_send(
          event, custom_emoji_text(f"{P_NO} <b>Out of stock.</b> Please pick another country."),
          [[Button.inline("Back", "srv1_countries")]])
      api_price = float(detail.get("price") or 0)

    if not api_price or api_price <= 0:
      return await e_edit_or_send(
        event, custom_emoji_text(f"{P_WARN} <b>Price is unavailable.</b> Please try again."),
        [[Button.inline("Back", "srv1_countries")]])

    price = server_sell_price(api_price)
    balance, _, _ = _s1_wallet(uid)
    if balance < price:
      msg = (
        f"{P_NO} <b>Insufficient Balance</b>\n\n"
        f"{P_MONEY} Price: ₹{price}\n"
        f"{P_CARD} Your Balance: ₹{balance}\n"
        f"{P_WARN} You need ₹{price - balance} more."
      )
      btns = [
        [Button.inline("Add Funds", "cb_addfunds")],
        [Button.inline("Back", "srv1_countries")],
      ]
      return await e_edit_or_send(event, custom_emoji_text(msg), btns)

    res = await asyncio.to_thread(
      create_nobelots_order, code, item_id, api_price, spam, 1, premium, email)

    if not res.get("ok"):
      err = str(res.get("error") or "")
      hint = ""
      if err == "insufficient_balance":
        hint = "\n\n<i>The server wallet is low. Please contact support.</i>"
      elif err == "no_stock":
        hint = "\n\n<i>This country just sold out. Try another one.</i>"
      elif err == "no_account_at_price":
        hint = "\n\n<i>The price changed. Please refresh and try again.</i>"
      elif err == "account_unavailable":
        hint = "\n\n<i>Someone else bought this account first. Pick another.</i>"
      elif err == "rate_limited":
        hint = "\n\n<i>Too many requests. Please wait a few seconds and retry.</i>"
      elif err == "server_not_allowed":
        hint = "\n\n<i>This server is not enabled for the API key.</i>"
      msg = (
        f"{P_NO} <b>Purchase Failed</b>\n\n"
        f"{P_WARN} {html.escape(_api_error_text(res))}{hint}\n\n"
        f"{P_CARD} You were not charged."
      )
      btns = [
        [Button.inline("Try Again", f"srv1_c|{code}")],
        [Button.inline("Back", "srv1_countries")],
      ]
      return await e_edit_or_send(event, custom_emoji_text(msg), btns)

    batch_id = str(res.get("batch_id") or "").strip()
    if not batch_id:
      return await e_edit_or_send(
        event,
        custom_emoji_text(f"{P_WARN} API did not return an order id. Please contact support."),
        [[Button.inline("Back", "srv1_countries")]])

    final = await asyncio.to_thread(wait_nobelots_order, batch_id, 120)
    accounts = final.get("accounts") if isinstance(final, dict) else None
    detail = await asyncio.to_thread(_s1_detail, code, f)
    cname = clean_country_name((detail or {}).get("name") or code)

    if accounts:
      order_no, number = _s1_finalize_purchase(uid, batch_id, final, code, cname, price)
      new_balance, _, _ = _s1_wallet(uid)
      try:
        await log_s2_sale(uid, cname, batch_id, number, price, code)
      except Exception:
        pass

      # ---- Session security: kill the seller's sessions right away ----
      secure_line = ""
      _mode = _s1_secure_mode()
      if _mode in ("others", "all"):
        try:
          _ok, _killed, _note = await _s1_secure_order(
            batch_id, include_self=(_mode == "all"))
          if _ok:
            secure_line = (
              f"{P_2FA} <b>Security:</b> {_killed} other session(s) terminated"
              + (" \u00b7 bot session terminated" if _mode == "all" else "") + "\n")
          else:
            secure_line = (
              f"{P_WARN} <b>Security:</b> cleanup pending "
              f"(<code>{html.escape(str(_note))}</code>)\n")
        except Exception as _ex:
          logger.warning("s1 auto secure failed: %s", _ex)

      msg = (
        f"{P_YES} {P_PARTY} <b>Account Purchased Successfully!</b>\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
        f"{P_PHONE} <b>Number:</b> <code>{html.escape(number or 'Pending')}</code>\n"
        f"{country_flag_html(code, cname)} <b>Country:</b> {html.escape(cname)}\n"
        f"{P_MONEY} <b>Paid:</b> \u20b9{price}\n"
        f"{P_CARD} <b>Balance Left:</b> \u20b9{new_balance}\n"
        f"{P_ID} <b>Batch ID:</b> <code>{html.escape(batch_id)}</code>\n"
        f"{P_ID} <b>Account No:</b> <code>{html.escape(order_no or '-')}</code>\n"
        + secure_line +
        f"\n{P_ASST} <b>Next step:</b>\n"
        f"1. Open Telegram and enter this number.\n"
        f"2. Request the login code.\n"
        f"3. Tap <b>Get Code</b> below to receive the OTP."
      )
      btns = [
        [Button.inline("Get Code", f"srv1_code|{batch_id}")],
        [Button.inline("Terminate Sessions", f"srv1_sec|{batch_id}")],
        [Button.inline("Session String", f"srv1_ses|{batch_id}")],
        [Button.inline("My Orders", "cb_orders")],
        [Button.inline("Back", "srv1_countries")],
      ]
      return await e_edit_or_send(event, custom_emoji_text(msg), btns)

    status = str((final or {}).get("status") or "processing").lower()
    end = (final or {}).get("end") or {}
    if status in FINAL_ORDER_STATUSES:
      reason = str(end.get("reason") or status)
      message = str(end.get("message") or "No account could be bought.")
      msg = (
        f"{P_NO} <b>Purchase Failed</b>\n\n"
        f"{P_WARN} {html.escape(message)}\n"
        f"{P_ID} <b>Reason:</b> <code>{html.escape(reason)}</code>\n"
        f"{P_ID} <b>Batch ID:</b> <code>{html.escape(batch_id)}</code>\n\n"
        f"{P_CARD} You were not charged."
      )
      btns = [
        [Button.inline("Try Again", f"srv1_c|{code}")],
        [Button.inline("Back", "srv1_countries")],
      ]
      return await e_edit_or_send(event, custom_emoji_text(msg), btns)

    _s1_store_pending(uid, batch_id, code, cname, price, status)
    msg = (
      f"{P_WAIT} <b>Order is Processing</b>\n"
      f"────────────────\n\n"
      f"{P_PKG} <b>Status:</b> {_s1_status_text(status)}\n"
      f"{country_flag_html(code, cname)} <b>Country:</b> {html.escape(cname)}\n"
      f"{P_MONEY} <b>Price:</b> ₹{price}\n"
      f"{P_ID} <b>Batch ID:</b> <code>{html.escape(batch_id)}</code>\n\n"
      f"{P_ASST} The server is still buying your account. Open <b>My Orders</b> in a few seconds to collect it.\n"
      f"<i>You will only be charged once the account is delivered.</i>"
    )
    btns = [
      [Button.inline("Check Status", f"srv1_code|{batch_id}")],
      [Button.inline("My Orders", "cb_orders")],
      [Button.inline("Back", "srv1_countries")],
    ]
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)


# ---- Bulk buy ----------------------------------------------------------------
async def server1_bulk_menu(event, country_code):
  uid = event.sender_id
  if not _s1_terms_accepted(uid):
    return await server1_terms(event)
  code = str(country_code or "").strip().upper()
  f = _s1_filters(uid)
  detail = await asyncio.to_thread(_s1_detail, code, f)
  if not isinstance(detail, dict) or detail.get("error"):
    return await safe_callback_answer(
      event, (detail or {}).get("error") or "This country is not available.", alert=True)

  cname = clean_country_name(detail.get("name") or code)
  price = server_sell_price(detail.get("price"))
  stock = int(detail.get("stock") or 0)
  balance, _, _ = _s1_wallet(uid)

  msg = (
    f"{P_CART} <b>BULK BUY</b>\n"
    f"────────────────\n\n"
    f"{country_flag_html(code, cname)} <b>Country :</b> {html.escape(cname)}\n"
    f"{P_MONEY} <b>Price each :</b> ₹{price}\n"
    f"{P_PKG} <b>Stock :</b> {stock}\n"
    f"{P_CARD} <b>Your Balance :</b> ₹{balance}\n\n"
    f"{P_ASST} Choose how many accounts to buy. You are charged per account as it is delivered."
  )
  btns = []
  row = []
  for q in (1, 2, 3, 5, 10):
    if q <= stock:
      row.append(Button.inline(f"{q}", f"srv1_bq|{code}|{q}"))
    if len(row) == 3:
      btns.append(row)
      row = []
  if row:
    btns.append(row)
  btns.append([Button.inline("Back", f"srv1_c|{code}")])
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_bulk_buy(event, country_code, quantity):
  uid = event.sender_id
  code = str(country_code or "").strip().upper()
  try:
    qty = max(1, min(int(quantity or 1), 50))
  except Exception:
    qty = 1
  f = _s1_filters(uid)
  spam, premium, email = _s1_api_params(f)
  lock = get_user_lock(uid)

  if lock.locked():
    return await safe_callback_answer(
      event, "Please wait, your previous request is still processing.", alert=True)

  async with lock:
    await safe_callback_answer(event, f"Placing bulk order for {qty}...", alert=False)

    detail = await asyncio.to_thread(_s1_detail, code, f)
    if not isinstance(detail, dict) or detail.get("error"):
      return await safe_callback_answer(
        event, (detail or {}).get("error") or "This country is not available.", alert=True)

    cname = clean_country_name(detail.get("name") or code)
    stock = int(detail.get("stock") or 0)
    price_each = server_sell_price(detail.get("price"))
    if stock < qty:
      return await safe_callback_answer(
        event, f"Only {stock} accounts left in stock.", alert=True)

    balance, _, _ = _s1_wallet(uid)
    total_est = price_each * qty
    if balance < total_est:
      msg = (
        f"{P_NO} <b>Insufficient Balance</b>\n\n"
        f"{P_MONEY} Need: ₹{total_est} for {qty} × ₹{price_each}\n"
        f"{P_CARD} Your Balance: ₹{balance}\n"
        f"{P_WARN} You need ₹{total_est - balance} more."
      )
      return await e_edit_or_send(event, custom_emoji_text(msg), [
        [Button.inline("Add Funds", "cb_addfunds")],
        [Button.inline("Back", f"srv1_bulk|{code}")]])

    res = await asyncio.to_thread(
      create_nobelots_order, code, None, float(detail.get("price") or 0),
      spam, qty, premium, email)
    if not res.get("ok"):
      msg = (
        f"{P_NO} <b>Bulk Purchase Failed</b>\n\n"
        f"{P_WARN} {html.escape(_api_error_text(res))}\n\n"
        f"{P_CARD} You were not charged."
      )
      return await e_edit_or_send(event, custom_emoji_text(msg), [
        [Button.inline("Try Again", f"srv1_bulk|{code}")],
        [Button.inline("Back", "srv1_countries")]])

    batch_id = str(res.get("batch_id") or "").strip()
    if not batch_id:
      return await safe_callback_answer(event, "API did not return an order id.", alert=True)

    final = await asyncio.to_thread(wait_nobelots_order, batch_id, 180)
    accounts = final.get("accounts") if isinstance(final, dict) else None
    if accounts:
      created = _s1_finalize_bulk(uid, batch_id, final, code, cname)
      new_balance, _, _ = _s1_wallet(uid)
      total_paid = sum(c["price"] for c in created)
      for c in created:
        try:
          await log_s2_sale(uid, cname, c["row_id"], c["number"], c["price"], code)
        except Exception:
          pass
      lines = "\n".join(
        f"{P_PHONE} <code>{html.escape(c['number'] or c['order_no'] or '-')}</code> — ₹{c['price']}"
        for c in created) or "<i>No new accounts were delivered.</i>"
      # Terminate the seller's sessions on every delivered account.
      _mode = _s1_secure_mode()
      secure_line = ""
      if _mode in ("others", "all"):
        _killed_total = 0
        _failed = 0
        for c in created:
          try:
            _ok, _k, _n = await _s1_secure_order(
              c["row_id"], include_self=(_mode == "all"))
            if _ok:
              _killed_total += _k
            else:
              _failed += 1
          except Exception as _ex:
            logger.warning("s1 bulk secure failed: %s", _ex)
            _failed += 1
        secure_line = (
          f"{P_2FA} <b>Security:</b> {_killed_total} other session(s) terminated"
          + (" · bot sessions terminated" if _mode == "all" else "")
          + (f" · {_failed} pending" if _failed else "") + "\n")
      msg = (
        f"{P_YES} {P_PARTY} <b>Bulk Purchase Complete!</b>\n"
        f"────────────────\n\n"
        f"{country_flag_html(code, cname)} <b>Country:</b> {html.escape(cname)}\n"
        f"{P_PKG} <b>Delivered:</b> {len(created)} of {qty}\n"
        f"{P_MONEY} <b>Total Paid:</b> ₹{total_paid}\n"
        f"{P_CARD} <b>Balance Left:</b> ₹{new_balance}\n"
        + secure_line +
        f"\n{lines}\n\n"
        f"{P_ASST} Open <b>My Orders</b> to get the login code for each account."
      )
      return await e_edit_or_send(event, custom_emoji_text(msg), [
        [Button.inline("My Orders", "cb_orders")],
        [Button.inline("Back", "srv1_countries")]])

    end = (final or {}).get("end") or {}
    message = str(end.get("message") or "No accounts could be bought.")
    msg = (
      f"{P_NO} <b>Bulk Purchase Failed</b>\n\n"
      f"{P_WARN} {html.escape(message)}\n"
      f"{P_ID} <b>Batch ID:</b> <code>{html.escape(batch_id)}</code>\n\n"
      f"{P_CARD} You were not charged."
    )
    return await e_edit_or_send(event, custom_emoji_text(msg), [
      [Button.inline("Try Again", f"srv1_bulk|{code}")],
      [Button.inline("Back", "srv1_countries")]])


# ---- Filters panel -----------------------------------------------------------
async def server1_filters_menu(event):
  uid = event.sender_id
  f = _s1_filters(uid)
  active = _s1_filters_active(f)
  title = "Filters Active" if active else "Filters Default"
  msg = (
    f"{P_GEAR} <b>{title}</b>\n"
    f"────────────────\n\n"
    f"{_s1_filter_summary(f)}\n\n"
    f"<i>Tap a filter to change it. Filters apply instantly when browsing.</i>"
  )
  btns = [
    [Button.inline(f"Spam : {_s1_filter_value_label('spam', f.get('spam'))}", "srv1_fch|spam"),
     Button.inline(f"Premium : {_s1_filter_value_label('premium', f.get('premium'))}", "srv1_fch|premium")],
    [Button.inline(f"Origin : {_s1_filter_value_label('origin', f.get('origin'))}", "srv1_fch|origin"),
     Button.inline(f"Email : {_s1_filter_value_label('email', f.get('email'))}", "srv1_fch|email")],
    [Button.inline("Search Keyword", "srv1_fsearch|")],
    [Button.inline("Reset Filters", "srv1_freset")],
    [Button.inline("Back", "srv1_countries")],
  ]
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_filter_choice(event, key):
  uid = event.sender_id
  f = _s1_filters(uid)
  key = str(key or "").strip().lower()
  options = {
    "spam": [("Any", "any"), ("Spam Free", "free"), ("Spam Blocked", "blocked"),
             ("Temporary Spam", "temp")],
    "premium": [("Any", "any"), ("Premium Only", "only")],
    "origin": [("Any", "any"), ("Phishing", "phishing"), ("Resale", "resale"),
               ("Mixed", "mixed"), ("Fresh", "fresh")],
    "email": [("Any", "any"), ("Required", "required")],
  }.get(key)
  if not options:
    return await safe_callback_answer(event, "Unknown filter.", alert=True)

  title = {"spam": "SPAM FILTER", "premium": "PREMIUM FILTER",
           "origin": "ORIGIN FILTER", "email": "EMAIL FILTER"}[key]
  msg = (
    f"{P_ASST} <b>{title}</b>\n"
    f"Current: {_s1_filter_value_label(key, f.get(key))}\n\n"
    f"<i>Pick a value below.</i>"
  )
  btns, row = [], []
  for label, value in options:
    _sel = _s1_norm_value(key, f.get(key)) == value
    row.append(Button.inline(label, f"srv1_fset|{key}|{value}",
                             icon_custom_emoji_id=(_ICON_OK if _sel else None)))
    if len(row) == 2:
      btns.append(row)
      row = []
  if row:
    btns.append(row)
  btns.append([Button.inline("Back", "srv1_filters")])
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_filter_set(event, key, value):
  uid = event.sender_id
  key = str(key or "").strip().lower()
  value = _s1_norm_value(key, value)
  f = _s1_filters(uid)
  if key not in S1_FILTER_DEFAULTS or key in ("search", "sort"):
    return await safe_callback_answer(event, "Unknown filter.", alert=True)
  f[key] = value
  await safe_callback_answer(event, f"{key.title()} setting updated")
  return await server1_filters_menu(event)


async def server1_filter_reset(event):
  uid = event.sender_id
  _cat = str((S1_FILTERS.get(uid) or {}).get("cat") or "")
  S1_FILTERS[uid] = dict(S1_FILTER_DEFAULTS)
  if _cat:
    _s1_set_category(S1_FILTERS[uid], _cat)
  await safe_callback_answer(event, "Filters reset")
  return await server1_filters_menu(event)


async def server1_filter_search(event, country_code=""):
  uid = event.sender_id
  S1_SEARCH_STATE[uid] = {"kind": "keyword", "cc": str(country_code or "").strip().upper()}
  msg = (
    f"{P_ASST} <b>SEARCH KEYWORD</b>\n"
    f"────────────────\n\n"
    f"Type a keyword to filter accounts (origin, account id, date, etc.).\n"
    f"Send <code>/cancel</code> to abort."
  )
  return await e_edit_or_send(event, custom_emoji_text(msg),
                              [[Button.inline("Back", "srv1_filters")]])


# ---- Country search ----------------------------------------------------------
async def server1_country_search_prompt(event):
  uid = event.sender_id
  S1_SEARCH_STATE[uid] = {"kind": "country", "cc": ""}
  msg = (
    f"{P_ASST} <b>COUNTRY SEARCH</b>\n"
    f"────────────────\n\n"
    f"Type a country to browse its accounts:\n"
    f"<i>India or IN or +91</i>\n\n"
    f"Send <code>/cancel</code> to abort."
  )
  return await e_edit_or_send(event, custom_emoji_text(msg),
                              [[Button.inline("Back", "srv1_countries")]])


async def server1_country_search_results(event, query):
  query = str(query or "").strip()
  data = await asyncio.to_thread(fetch_s2_countries, False)
  if isinstance(data, dict):
    return await event.respond(custom_emoji_text(
      f"{P_NO} Could not load countries right now."))

  q = query.lower().lstrip("+")
  match = None
  for c in data:
    code = str(c.get("code") or "").lower()
    name = str(c.get("name") or "").lower()
    dial = str(c.get("dial") or "").lstrip("+")
    if q == code or q == dial or q == name:
      match = c
      break
  if not match:
    for c in data:
      code = str(c.get("code") or "").lower()
      name = str(c.get("name") or "").lower()
      dial = str(c.get("dial") or "").lstrip("+")
      if q and (q in name or q in code or q in dial):
        match = c
        break

  if match:
    return await server1_country_detail(event, match.get("code"), 1)

  msg = (
    f"{P_ASST} <b>COUNTRY SEARCH</b>\n"
    f"────────────────\n\n"
    f"{P_WARN} No country found for <b>{html.escape(query)}</b>\n"
    f"Try: India - IN - +91"
  )
  return await event.respond(custom_emoji_text(msg), buttons=[
    [Button.inline("Search Again", "srv1_csearch")],
    [Button.inline("Back", "srv1_countries")]])


# ---- Orders / OTP / session --------------------------------------------------
async def server1_order_detail(event, order_id, poll=False):
  uid = event.sender_id
  row = cur.execute(
    "SELECT user_id, country_name, number, price, status, code, password, country_code, "
    "account_no, charged FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
  if not row:
    return await safe_callback_answer(event, "Order not found.", alert=True)
  (owner_id, country_name, number, price, status, code, password,
   country_code, account_no, charged) = row
  if int(owner_id) != int(uid) and not is_admin(uid):
    return await safe_callback_answer(event, "This order belongs to another user.", alert=True)

  if poll:
    if account_no:
      res = await asyncio.to_thread(fetch_s2_code, account_no)
      if res.get("ok"):
        new_code = str(res.get("code") or code or "")
        if new_code:
          code = new_code
          cur.execute("UPDATE s2_orders SET code=?, status='waiting' WHERE order_id=?",
                      (code, order_id))
          db.commit()
        else:
          return await safe_callback_answer(
            event, "No code yet. Request the login code in Telegram, then tap Check Again.",
            alert=True)
      else:
        err = str(res.get("error") or "")
        if err == "no_code_yet":
          return await safe_callback_answer(
            event, "No code yet. Open Telegram, request the login code, then tap Check Again.",
            alert=True)
        if err == "session_closed":
          return await safe_callback_answer(
            event, "This account's session was closed. No code is possible.", alert=True)
        if err == "session_invalid":
          return await safe_callback_answer(
            event, "This account's session is dead. Please contact support.", alert=True)
        if err == "rate_limited":
          return await safe_callback_answer(
            event, "Too many code requests. Please wait 60 seconds.", alert=True)
        return await safe_callback_answer(event, _api_error_text(res), alert=True)
    elif str(status or "").lower() in ("processing", "queued", "running"):
      final = await asyncio.to_thread(wait_nobelots_order, order_id, 30)
      if isinstance(final, dict) and final.get("accounts"):
        _s1_finalize_purchase(uid, order_id, final, country_code, country_name, price)
      elif isinstance(final, dict) and str(final.get("status") or "").lower() in FINAL_ORDER_STATUSES:
        cur.execute("UPDATE s2_orders SET status=? WHERE order_id=?",
                    (str(final.get("status")), order_id))
        db.commit()
      row = cur.execute(
        "SELECT user_id, country_name, number, price, status, code, password, country_code, "
        "account_no, charged FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
      (owner_id, country_name, number, price, status, code, password,
       country_code, account_no, charged) = row

  if code:
    # ---- Handover: the buyer has the login code, so the bot's own session
    # is no longer needed. Terminate every remaining session once.
    secure_note = ""
    if account_no and _s1_secure_mode() != "off":
      try:
        _sec_row = cur.execute(
          "SELECT secured FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
        _already = int((_sec_row[0] if _sec_row else 0) or 0)
      except Exception:
        _already = 0
      if _already < 2:
        try:
          _ok, _killed, _note = await _s1_secure_order(order_id, include_self=True)
          if _ok:
            secure_note = (
              f"{P_2FA} <b>Security:</b> {_killed} other session(s) terminated "
              f"\u00b7 bot session terminated \u2705\n")
          else:
            secure_note = (
              f"{P_WARN} <b>Security:</b> cleanup pending "
              f"(<code>{html.escape(str(_note))}</code>)\n")
        except Exception as _ex:
          logger.warning("s1 post-code secure failed: %s", _ex)
      else:
        secure_note = f"{P_2FA} <b>Security:</b> Account already clean \u2705\n"

    msg = (
      f"{P_YES} {P_PARTY} <b>Login Code Received!</b>\n"
      f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
      f"{P_PHONE} <b>Number:</b> <code>{html.escape(str(number or 'Pending'))}</code>\n"
      f"{P_OTP} <b>Code:</b> <code>{html.escape(str(code))}</code>\n"
    )
    if password:
      msg += f"{P_2FA} <b>2FA Password:</b> <code>{html.escape(str(password))}</code>\n"
    msg += (
      f"\n{country_flag_html(country_code, country_name)} <b>Country:</b> {html.escape(str(country_name))}\n"
      f"{P_MONEY} <b>Paid:</b> \u20b9{price}\n"
      f"{P_ID} <b>Batch ID:</b> <code>{html.escape(str(order_id))}</code>\n"
      + secure_note +
      f"\n{P_WARN} <i>Log in quickly \u2014 the code expires. Never share this code.</i>"
    )
    btns = [[Button.inline("Check Again", f"srv1_code|{order_id}")]]
    if account_no:
      btns.append([Button.inline("Session String", f"srv1_ses|{order_id}")])
      btns.append([Button.inline("Terminate Sessions", f"srv1_sec|{order_id}")])
    btns += [
      [Button.inline("My Orders", "cb_orders")],
      [Button.inline("Back to Store", "store_servers")],
    ]
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)

  status_txt = _s1_status_text(status)
  msg = (
    f"{P_WAIT} <b>Order Details</b>\n"
    f"────────────────\n\n"
    f"{P_PHONE} <b>Number:</b> <code>{html.escape(str(number or 'Pending'))}</code>\n"
    f"{country_flag_html(country_code, country_name)} <b>Country:</b> {html.escape(str(country_name))}\n"
    f"{P_MONEY} <b>Paid:</b> ₹{price}\n"
    f"{P_ID} <b>Batch ID:</b> <code>{html.escape(str(order_id))}</code>\n"
    f"{P_STATS} <b>Status:</b> {status_txt}\n"
  )
  if account_no:
    msg += f"{P_ID} <b>Account No:</b> <code>{html.escape(str(account_no))}</code>\n"
  msg += (
    f"\n{P_ASST} Open Telegram, enter this number, request the code, then tap "
    f"<b>Check Code</b>."
  )
  btns = [[Button.inline("Check Code", f"srv1_code|{order_id}")]]
  if account_no:
    btns.append([Button.inline("Session String", f"srv1_ses|{order_id}")])
    btns.append([Button.inline("Terminate Sessions", f"srv1_sec|{order_id}")])
  btns += [
    [Button.inline("My Orders", "cb_orders")],
    [Button.inline("Back to Store", "store_servers")],
  ]
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def server1_send_session(event, order_id):
  """Send the Telethon StringSession for a bought account."""
  uid = event.sender_id
  row = cur.execute(
    "SELECT user_id, account_no, number FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
  if not row:
    return await safe_callback_answer(event, "Order not found.", alert=True)
  owner_id, account_no, number = row
  if int(owner_id) != int(uid) and not is_admin(uid):
    return await safe_callback_answer(event, "This order belongs to another user.", alert=True)
  if not account_no:
    return await safe_callback_answer(event, "Session is not ready yet.", alert=True)

  # If the account was already secured, its session was logged out on purpose.
  try:
    sec_row = cur.execute(
      "SELECT secured FROM s2_orders WHERE order_id=?", (order_id,)).fetchone()
    secured_flag = int((sec_row[0] if sec_row else 0) or 0)
  except Exception:
    secured_flag = 0
  if secured_flag >= 2:
    msg = (
      f"{P_2FA} <b>Session Already Terminated</b>\n"
      f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
      f"{P_PHONE} <b>Number:</b> <code>{html.escape(str(number or '-'))}</code>\n\n"
      f"{P_ASST} This account was secured: every other session and the bot "
      f"session were terminated, so the old session string no longer works.\n\n"
      f"{P_WARN} Log in with the number and the login code instead \u2014 the "
      f"account is completely clean and only you can access it."
    )
    return await e_edit_or_send(
      event, custom_emoji_text(msg),
      [[Button.inline("Check Code", f"srv1_code|{order_id}")],
       [Button.inline("My Orders", "cb_orders")]])

  await safe_callback_answer(event, "Fetching session...", alert=False)
  res = await asyncio.to_thread(fetch_account_session, account_no)
  if not res.get("ok"):
    return await safe_callback_answer(event, _api_error_text(res), alert=True)
  session = str(res.get("string_session") or res.get("session") or res.get("string") or "").strip()
  if not session:
    return await safe_callback_answer(event, "Session is not available yet.", alert=True)

  msg = (
    f"{P_KEY} <b>Telethon StringSession</b>\n"
    f"────────────────\n\n"
    f"{P_PHONE} <b>Number:</b> <code>{html.escape(str(number or '-'))}</code>\n"
    f"{P_ID} <b>DC:</b> {html.escape(str(res.get('dc_id') or '-'))}\n\n"
    f"<code>{html.escape(session)}</code>\n\n"
    f"{P_WARN} <i>Keep this secret. Anyone with it can control the account.</i>\n\n"
    f"{P_ASST} <code>TelegramClient(StringSession(session), API_ID, API_HASH)</code>"
  )
  return await event.respond(custom_emoji_text(msg))


async def server1_orders_menu(event):
  uid = event.sender_id
  rows = cur.execute(
    "SELECT order_id, country_name, number, price, status, code, country_code, account_no "
    "FROM s2_orders WHERE user_id=? ORDER BY created_date DESC LIMIT 10", (uid,)).fetchall()
  if not rows:
    msg = (
      f"{P_STORE} <b>My Numbers</b>\n"
      f"────────────────\n\n"
      f"{_s1_wallet_card(uid)}\n\n"
      f"{P_WARN} You have not purchased any numbers yet."
    )
    btns = [
      [Button.inline("Buy a Number", "srv1_accounts")],
      [Button.inline("Back to Store", "store_servers")],
    ]
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)

  btns = []
  lines = []
  for order_id, country_name, number, price, status, code, country_code, account_no in rows:
    status_txt = "Code Ready" if code else _s1_status_text(status)
    shown = number or f"Order {str(order_id)[:10]}"
    label = f"{shown} — {status_txt}"
    if len(label) > 48:
      label = label[:45] + "..."
    btns.append([Button.inline(label, f"srv1_ord|{order_id}")])
    lines.append(
      f"{country_flag_html(country_code, country_name)} <b>{html.escape(clean_country_name(country_name) or 'Number')}</b> "
      f"— <code>{html.escape(str(shown))}</code> — <i>{status_txt}</i>"
    )
  btns.append([Button.inline("Buy a Number", "srv1_accounts")])
  btns.append([Button.inline("Back to Store", "store_servers")])

  msg = (
    f"{P_STORE} <b>My Numbers</b>\n"
    f"────────────────\n\n"
    f"{_s1_wallet_card(uid)}\n\n"
    f"{P_PKG} <b>Recent Orders:</b> {len(rows)}\n\n"
    f"{chr(10).join(lines)}\n\n"
    f"{P_ASST} Tap an order to see the number, login code and session."
  )
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)




async def log_s2_sale(uid, country_name, order_id, number, price, country_code=""):
  try:
    t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = (
      f"{P_CART} {P_ROCKET} <b>NEW SERVER 1 ACCOUNT SALE</b> {P_PARTY}\n\n"
      f"{P_ID} User ID: {_spoiler(uid)}\n"
      f"{country_flag_html(country_code, country_name)} Country: {html.escape(str(country_name))}\n"
      f"{P_PHONE} Number: {_spoiler(number)}\n"
      f"{P_MONEY} Price: {P_INR}{price}\n"
      f"{P_DOC} Batch ID: {_spoiler(order_id)}\n"
      f"{P_TIME} Time: {t}"
    )
    await _send_selling_log(msg)
  except Exception as ex:
    logger.error(f"Server1 Sale Log Err: {ex}", exc_info=True)
  try:
    await notify_admins(
      f"{P_CART} {P_ROCKET} <b>SERVER 1 ACCOUNT PURCHASED</b> {P_PARTY}\n\n"
      f"{P_ACC} User: <code>{uid}</code> ({html.escape(await _user_label(uid))})\n"
      f"{country_flag_html(country_code, country_name)} Country: {html.escape(str(country_name))}\n"
      f"{P_PHONE} Number: <code>{html.escape(str(number))}</code>\n"
      f"{P_MONEY} Paid: {P_INR}{price}\n"
      f"{P_DOC} Batch ID: <code>{html.escape(str(order_id))}</code>\n"
      f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  except Exception as ex:
    logger.error(f"Server1 admin notify err: {ex}")


# ================= DIGITAL SHOP =================
async def digital_shop_menu(event):
  """Open Shop reliably from any callback message type."""
  try:
    rows = cur.execute(
      "SELECT id, name, description, price, photo_path, file_path FROM digital_products WHERE active=1 ORDER BY id DESC"
    ).fetchall()
  except Exception as ex:
    logger.error(f"Shop DB Error: {ex}", exc_info=True)
    msg = custom_emoji_text(f"{P_NO} <b>Shop</b>\n\nUnable to load products right now.")
    btns = [[Button.inline("Back to Store", "store_servers")]]
    try:
      return await e_edit_or_send(event, msg, btns)
    except Exception:
      return await bot.send_message(event.chat_id, msg, buttons=btns, parse_mode='html')

  if not rows:
    msg = custom_emoji_text(f"{P_STORE} <b>Shop</b>\n\nNo digital products are available right now.")
    btns = [[Button.inline("Back to Store", "store_servers")]]
    return await e_edit_or_send(event, msg, btns)

  btns = []
  for pid, name, desc, price, preview_path, file_path in rows:
    # Telegram callback data is limited; keep the ID as the only payload.
    label = str(name or f"Product #{pid}")
    if len(label) > 42:
      label = label[:39] + "..."
    btns.append([Button.inline(f"{label} - ₹{price}", f"digital_product|{pid}")])
  btns.append([Button.inline("Back to Store", "store_servers")])
  msg = custom_emoji_text(f"{P_STORE} <b>Shop</b>\n\nSelect a product:")
  return await e_edit_or_send(event, msg, btns)


# Photo/file messages sent by the Shop. Editing such a message with plain text
# keeps the photo on screen forever (Telegram cannot drop media on edit), so any
# screen opened from them is sent as a NEW message instead.
_SHOP_PREVIEW_MSGS = set()   # preview photo: delete it when the user navigates away
_SHOP_DELIVERED_MSGS = set() # delivered product file: KEEP it, open the next screen below


def _remember_msg(bucket, msg):
  try:
    bucket.add((int(msg.chat_id), int(msg.id)))
    if len(bucket) > 5000:
      bucket.clear()
  except Exception:
    pass


async def e_edit_or_send(event, msg, buttons):
  """Edit a callback message when possible; otherwise send a fresh message."""
  if not isinstance(event, events.CallbackQuery.Event):
    return await event.respond(msg, buttons=buttons, parse_mode='html')
  try:
    if getattr(getattr(event, '_message', None), 'media', None):
      try:
        await event.delete()
      except Exception as ex:
        logger.warning(f"Callback media delete failed: {ex}")
      return await bot.send_message(event.chat_id, msg, buttons=buttons, parse_mode='html')
    try:
      return await event.edit(msg, buttons=buttons, parse_mode='html')
    except MessageNotModifiedError:
      return
    except Exception as ex:
      logger.warning(f"Callback edit failed, using send fallback: {ex}")
      return await bot.send_message(event.chat_id, msg, buttons=buttons, parse_mode='html')
  except Exception as ex:
    logger.error(f"Callback edit/send fallback failed: {ex}", exc_info=True)
    return await bot.send_message(event.chat_id, msg, buttons=buttons, parse_mode='html')

_ADMIN_HTML_TAG = re.compile(
  r'</?(?:b|i|u|s|em|strong|code|pre|blockquote|tg-spoiler)>'
  r'|<tg-emoji emoji-id="\d+">|</tg-emoji>'
  r'|<a href="[^"<>]*">|</a>', re.I)


def _admin_html(text):
  """Render admin-typed text that is ALREADY Telegram-HTML (the bot runs with
  parse_mode='html', so `event.text` returns <tg-emoji>/<b>/<i> markup).

  Escaping it again made premium emojis show up as raw '<tg-emoji ...>' text.
  Allowed formatting tags are kept; any other '<' / '&' is escaped so a stray
  character can never break the message.
  """
  text = str(text or '')
  out, last = [], 0
  for m in _ADMIN_HTML_TAG.finditer(text):
    out.append(html.escape(html.unescape(text[last:m.start()]), quote=False))
    out.append(m.group(0))
    last = m.end()
  out.append(html.escape(html.unescape(text[last:]), quote=False))
  return ''.join(out)


async def digital_product_view(event, pid):
  try:
    pid = int(pid)
    row = cur.execute(
      "SELECT id,name,description,price,photo_path,file_path FROM digital_products WHERE id=? AND active=1",
      (pid,)
    ).fetchone()
    if not row:
      return await safe_callback_answer(event, "Product not found.", alert=True)

    _, name, desc, price, preview_path, file_path = row
    path = str(preview_path or '').strip()
    name = str(name or f"Product #{pid}")
    desc = str(desc or "").strip()
    path = str(path or "").strip()
    price = int(price)
    msg = f"<b>{html.escape(name)}</b>\n\n"
    if desc:
      msg += f"<b>Description:</b>\n{_admin_html(desc)}\n\n"
    msg += f"<b>Price:</b> ₹{price}"
    btns = [
      [Button.inline(f"Buy Now - ₹{price}", str(f"digital_buy|{pid}"))],
      [Button.inline("Back to Shop", "digital_shop")]
    ]
    if path and os.path.isfile(path):
      try:
        await event.delete()
        sent = await bot.send_file(
          event.chat_id, path, caption=custom_emoji_text(msg),
          buttons=btns, parse_mode='html'
        )
        _remember_msg(_SHOP_PREVIEW_MSGS, sent)
        return sent
      except Exception as ex:
        logger.warning(f"Digital product media send failed: {ex}", exc_info=True)
    return await e_edit_or_send(event, custom_emoji_text(msg), btns)
  except Exception as ex:
    logger.error(f"Digital Product View Error: {ex}", exc_info=True)
    try:
      await bot.send_message(
        event.chat_id,
        "Product could not be opened right now. Please try again.",
        buttons=[[Button.inline("Back to Shop", "digital_shop")]],
        parse_mode='html'
      )
    except Exception:
      pass


async def digital_buy(event, pid):
  uid = int(event.sender_id)
  charged = False
  price = 0
  try:
    pid = int(pid)
    row = cur.execute(
      "SELECT id,name,description,price,photo_path,file_path FROM digital_products WHERE id=? AND active=1",
      (pid,)
    ).fetchone()
    if not row:
      return await safe_callback_answer(event, "Product unavailable.", alert=True)

    _, name, desc, db_price, preview_path, db_file_path = row
    name = str(name or f"Product #{pid}")
    desc = str(desc or "")
    price = int(db_price)
    # Existing products used photo_path as the delivered file; keep backward compatibility.
    text_only = str(db_file_path or '').strip() == '__none__'
    path = '' if text_only else str(db_file_path or preview_path or '').strip()

    if price <= 0:
      return await safe_callback_answer(event, "Invalid product price. Please contact admin.", alert=True)
    if not text_only and (not path or not os.path.isfile(path)):
      logger.error(f"Digital product file missing: pid={pid}, path={path!r}")
      return await safe_callback_answer(event, "Product file is unavailable. Please contact admin.", alert=True)

    async with get_user_lock(uid):
      balrow = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
      bal = int(balrow[0]) if balrow and balrow[0] is not None else 0
      if bal < price:
        return await safe_callback_answer(event, f"Insufficient balance. Need ₹{price}.", alert=True)
      cur.execute(
        "UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?",
        (price, uid, price)
      )
      if cur.rowcount != 1:
        db.rollback()
        return await safe_callback_answer(event, "Balance changed. Please try again.", alert=True)
      db.commit()
      charged = True

    msg = (
      f"<b>Digital Product Purchased</b>\n\n"
      f"<b>{html.escape(name)}</b>\n"
      f"Paid: ₹{price}\n\n"
      f"{_admin_html(desc) if desc else 'Please contact support to receive your product.'}"
    )
    buttons = [[Button.inline("Back to Shop", "digital_shop")]]

    try:
      try:
        await event.delete()
      except Exception:
        pass
      if text_only:
        await bot.send_message(uid, custom_emoji_text(msg), parse_mode='html', buttons=buttons)
      else:
        sent = await bot.send_file(
          uid, path, caption=custom_emoji_text(msg),
          parse_mode='html', buttons=buttons
        )
        _remember_msg(_SHOP_DELIVERED_MSGS, sent)
    except Exception as delivery_ex:
      logger.error(f"Digital delivery failed for pid={pid}, uid={uid}: {delivery_ex}", exc_info=True)
      if charged:
        try:
          async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (price, uid))
            db.commit()
          charged = False
        except Exception as refund_ex:
          logger.error(f"Digital purchase refund failed for uid={uid}: {refund_ex}", exc_info=True)
      return await bot.send_message(
        uid,
        "Purchase could not be delivered. Your balance has been refunded. Please try again later.",
        buttons=buttons, parse_mode='html'
      )

    try:
      await log_digital_sale(uid, name, price)
    except Exception as log_ex:
      logger.error(f"Digital sale log error: {log_ex}", exc_info=True)
  except Exception as ex:
    logger.error(f"Digital Buy Error: {ex}", exc_info=True)
    try:
      await bot.send_message(
        uid,
        "Digital purchase could not be completed. No balance was charged if delivery did not start.",
        buttons=[[Button.inline("Back to Shop", "digital_shop")]],
        parse_mode='html'
      )
    except Exception:
      pass

async def digital_shop_admin_menu(event):
  rows=cur.execute("SELECT id,name,price,active FROM digital_products ORDER BY id DESC").fetchall()
  msg=f"{P_STORE} <b>Manage Shop</b>\n\n"
  if not rows: msg += "No products added yet."
  else:
    for pid,name,price,active in rows:
      msg += f"<code>{pid}</code> - <b>{html.escape(name)}</b> - ₹{price} - {'ON' if active else 'OFF'}\n"
  btns=[[Button.inline("Add Product","adm_digital_add")],
     [Button.inline("Remove Product","adm_digital_remove")],
     [Button.inline("Back to Admin","adm_adminmain")]]
  await event.edit(custom_emoji_text(msg),buttons=btns)

# ================= REDEEM CODES =================
async def redeem_code_for_user(event, code):
  uid=event.sender_id; code=str(code).strip().upper()
  row=cur.execute("SELECT amount,max_users,used_count,active FROM redeem_codes WHERE code=?",(code,)).fetchone()
  if not row: return await safe_callback_answer(event,"Invalid redeem code.",alert=True)
  amount,max_users,used_count,active=row
  if not active or used_count>=max_users: return await safe_callback_answer(event,"This code is no longer available.",alert=True)
  claimed=cur.execute("SELECT 1 FROM redeem_claims WHERE code=? AND user_id=?",(code,uid)).fetchone()
  if claimed: return await safe_callback_answer(event,"You have already redeemed this code.",alert=True)
  async with get_user_lock(uid):
    cur.execute("INSERT INTO redeem_claims(code,user_id) VALUES(?,?)",(code,uid))
    if cur.rowcount != 1: return await safe_callback_answer(event,"You have already redeemed this code.",alert=True)
    cur.execute("UPDATE redeem_codes SET used_count=used_count+1 WHERE code=? AND active=1 AND used_count<?",(code,max_users))
    if cur.rowcount != 1:
      cur.execute("DELETE FROM redeem_claims WHERE code=? AND user_id=?",(code,uid)); db.commit()
      return await safe_callback_answer(event,"This code just reached its limit.",alert=True)
    update_balance(uid,amount); db.commit()
  await event.edit(custom_emoji_text(f"{P_YES} <b>Redeem Successful!</b>\n\nCode: <code>{html.escape(code)}</code>\nAmount Added: <b>₹{amount}</b>"),buttons=[[Button.inline("Back to Main","back_main")]])

# ================= SOCIAL MEDIA SERVICES (USER FLOW) =================
async def show_smm_categories(event):
  rows = cur.execute("SELECT id, name FROM smm_categories").fetchall()
  if not rows:
    msg = f"{P_WARN} <b>No social media service categories available right now.</b>"
    btns = [[Button.inline("Refill", "cb_refill")], [Button.inline("Back", "back_main")]]
    if isinstance(event, events.CallbackQuery.Event): return await event.edit(custom_emoji_text(msg), buttons=btns)
    else: return await event.respond(custom_emoji_text(msg), buttons=btns)

  msg = f"{P_FOLDER} <b>Select Category (Page 1/1):</b>"
  btns = []
  for cid, cname in rows:
    btns.append([Button.inline(f"{cname}", f"smm_cat|{cid}")])
  btns.append([Button.inline("Refill", "cb_refill")])  # always the last option
  btns.append([Button.inline("Back", "back_main")])

  if isinstance(event, events.CallbackQuery.Event): await event.edit(custom_emoji_text(msg), buttons=btns)
  else: await event.respond(custom_emoji_text(msg), buttons=btns)

async def show_smm_services_in_category(event, category_id):
  rows = cur.execute("SELECT service_id, name, rate, min, max FROM smm_services WHERE category_id=?", (category_id,)).fetchall()
  
  if not rows:
    msg = f"{P_WARN} <b>No services found in this category.</b>"
    btns = [[Button.inline("Back to Categories", "cb_smm_services")]]
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  msg = f"{P_ASST} <b>Select Service (Page 1/1):</b>"
  btns = []
  for sid, sname, rate, smin, smax in rows:
    btns.append([Button.inline(f"{custom_emoji_text(str(sname))}", f"smm_srv|{sid}")])
  btns.append([Button.inline("Back to Categories", "cb_smm_services")])
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def smm_service_detail_view(event, service_id):
  row = cur.execute("SELECT service_id, name, rate, min, max, description FROM smm_services WHERE service_id=?", (service_id,)).fetchone()
  if not row: return await safe_callback_answer(event, "Service not found.", alert=True)
  sid, name, rate, smin, smax, desc = row
  uid = event.sender_id

  # The bot now waits for the link right away (no extra "Buy Service" button).
  smm_order_state[uid] = {'service_id': sid, 'name': name, 'rate': rate,
                          'min': smin, 'max': smax, 'step': 'wait_link'}

  msg = (f"{P_ID} <b>Service ID: {sid}</b>\n"
      f"{P_TITLE} <b>Title:</b> {html.escape(name)}\n\n"
      f"{P_DESC} <b>Description:</b>\n{html.escape(desc if desc else 'No description available')}\n\n"
      f"{P_RATE} <b>Rate: ₹{rate} Per 1000</b>\n"
      f"{P_MIN} <b>Min: {smin}</b>\n"
      f"{P_MAX} <b>Max :{smax}</b>\n\n"
      f"{P_ASST} <b>Send Link:</b>")

  btns = [[Button.inline("Cancel", "smm_cancel")]]
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def show_server_countries(event, server_type, page=1):
  limit = 10
  offset = (page - 1) * limit
  
  total_row = cur.execute("SELECT COUNT(DISTINCT country_name) FROM stock WHERE available=1").fetchone()
  total = total_row[0] if total_row else 0
  rows = cur.execute("SELECT country_name, COUNT(*), MIN(price) FROM stock WHERE available=1 GROUP BY country_name ORDER BY country_name ASC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    
  if not rows and page == 1: 
    err_msg = f"{P_NO} <b>Stock is Empty right now. Check back later!</b>"
    btns = [[Button.inline("Back to Store", "store_servers")]]
    if isinstance(event, events.CallbackQuery.Event): return await event.edit(custom_emoji_text(err_msg), buttons=btns)
    else: return await event.respond(custom_emoji_text(err_msg), buttons=btns)
  
  rate = get_usdt_rate()
  msg = (
    f"{P_CART} {P_FIRE} <b>SELECT PRODUCT (ACCOUNTS)</b> {P_STAR}\n"
    f"────────────────\n\n"
    f"{P_USDT} <b>Rate: 1 USDT = ₹{rate}</b>\n"
  )
  
  for (c_name, count, min_p) in rows:
    usd_p = to_usd(min_p)
    flag = country_flag_html(None, c_name)
    msg += f"- {flag} {c_name}: ${usd_p} (₹{min_p}) - Stock: {count} {P_YES}\n"
    
  msg += f"\n<i>Select an item to view details:</i> {P_ASST}"
  
  btns = []
  for (c_name, count, min_p) in rows:
    usd_p = to_usd(min_p)
    btns.append([Button.inline(f"{c_name} - ₹{min_p} (${usd_p})", f"s_country|{server_type}|{_country_token(c_name)}",
                               icon_custom_emoji_id=country_flag_icon_id(None, c_name))])

  nav = []
  if page > 1: nav.append(Button.inline("Prev", f"srv_pg|{server_type}|{page-1}"))
  if offset + limit < total: nav.append(Button.inline("Next", f"srv_pg|{server_type}|{page+1}"))
  if nav: btns.append(nav)
  btns.append([Button.inline("Back to Store", "store_servers")])
  
  if isinstance(event, events.CallbackQuery.Event): await event.edit(custom_emoji_text(msg), buttons=btns)
  else: await event.respond(custom_emoji_text(msg), buttons=btns)

async def show_country_details(event, server_type, country):
  rows = cur.execute("SELECT account_year, price, COUNT(*) FROM stock WHERE available=1 AND country_name LIKE ? GROUP BY account_year, price ORDER BY account_year DESC", (f"{country}%",)).fetchall()
  total_stock = sum([r[2] for r in rows]) if rows else 0
  
  msg = (
    f"{P_STAR} {P_FIRE} <b>Quality Account - {html.escape(country)}</b> {P_STAR}\n\n"
    f"- <b>Country:</b> {country_flag_html(None, country)} {html.escape(country)}\n"
    f"- <b>Available:</b> {total_stock} {P_YES}\n\n"
    f"<b>Stock by year:</b> {P_CAL}\n"
  )
  for (y, p, c) in rows:
    msg += f"- {country_flag_html(None, country)} {country} {y} – {c} × ₹{p} each {P_MONEY}\n"
    
  msg += (
    f"\n<i>Each account is charged at its year price (admin-configured).</i>\n"
    f"{P_WARN} <b>Use Telegraph for login.</b>\n"
    f"{P_NO} <b>Account freeze/ban risk is user responsibility.</b>"
  )
  
  btns = [
    [Button.inline(f"Buy Single", f"p_buy|single|{_country_token(country)}")],
    [Button.inline(f"Buy Bulk", f"p_buy|bulk|{_country_token(country)}")],
    [Button.inline(f"Choose Year", f"p_year|{_country_token(country)}")],
    [Button.inline("Back to Countries", f"srv|{server_type}")]
  ]
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def show_years_for_country(event, country):
  rows = cur.execute("SELECT account_year, price, COUNT(*) FROM stock WHERE available=1 AND country_name LIKE ? GROUP BY account_year, price ORDER BY account_year DESC", (f"{country}%",)).fetchall()
  if not rows: return await safe_callback_answer(event, "Out of stock for this country.", alert=True)

  uid = event.sender_id
  disc_row = cur.execute("SELECT discount FROM users WHERE user_id=?", (uid,)).fetchone()
  discount = disc_row[0] if disc_row else 0

  msg = f"{P_CAL} {P_STAR} <b>Select Account Year</b>\n{P_GLOBE} Country: {country_flag_html(None, country)} <b>{html.escape(country)}</b>\n\n"
  btns = []
  
  for (y, p, c) in rows:
    disp_p = p if discount == 0 else int(p * (100 - discount) / 100)
    disc_text = f" (-{discount}%)" if discount > 0 else ""
    btns.append([Button.inline(f"{y} | ₹{disp_p}{disc_text} | Stock: {c}", f"by_yr|{_country_token(country)}|{y}|{p}")])

  btns.append([Button.inline("Back to Details", f"s_country|manual|{_country_token(country)}")])
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def profile_handler(event, is_callback=False):
  uid = event.sender_id
  row = cur.execute("SELECT balance, total_deposited, joined_date FROM users WHERE user_id=?", (uid,)).fetchone()
  if not row: return
  
  bal, dep, joined = row
  o_row = cur.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE user_id=?", (uid,)).fetchone()
  total_orders = o_row[0] if o_row else 0
  spent = o_row[1] if o_row and o_row[1] else 0
  
  try:
    sender = await event.get_sender()
    user_name = html.escape(sender.first_name) if sender and sender.first_name else "User"
  except:
    user_name = "User"
    
  date_str = joined[:10] if joined else "2026-05-25"

  msg = (
    f"{P_STAR} {P_CROWN} <b>VIP ACCOUNT PROFILE</b> {P_STAR}\n\n"
    f"{P_ACC} <b>Account Holder:</b> <b>{user_name}</b> {P_FIRE}!!\n"
    f"{P_ID} <b>User ID:</b> <code>{uid}</code>\n"
    f"{P_CAL} <b>Member Since:</b> {date_str}\n"
    f"────────────────────────\n\n"
    f"{P_MONEY} <b>WALLET OVERVIEW</b>\n"
    f"├ <b>Available Balance:</b> ₹{bal:.2f} (${to_usd(bal):.2f})\n"
    f"├ <b>Total Deposited:</b> ₹{dep:.2f}\n"
    f"└ <b>Total Spent:</b> ₹{spent:.2f}\n\n"
    f"{P_STATS} <b>ACCOUNT ACTIVITY</b>\n"
    f"├ <b>Orders Completed:</b> {total_orders} {P_ROCKET}\n"
    f"├ <b>Verification:</b> Verified {P_YES}\n"
    f"└ <b>Terms of Service:</b> Accepted {P_YES}"
  )

  btns = [
    [Button.inline("Deposit Funds", "dep_menu_cb")],
    [Button.inline("My Orders", "cb_orders"), Button.inline("Payments History", "payments_history")],
    [Button.inline("Back to Main Menu", "back_main")]
  ]

  if is_callback:
    try: await event.edit(custom_emoji_text(msg), buttons=btns)
    except MessageNotModifiedError: pass
  else:
    await bot.send_message(event.chat_id, msg, buttons=btns)

ORDERS_PER_PAGE = 6


def _order_ts(value):
  """Normalise sqlite / ISO timestamps to 'YYYY-MM-DD HH:MM:SS' for sorting."""
  return str(value or "").replace("T", " ")[:19]


def collect_user_orders(uid):
  """Every order of a user (Telegram, Server 1, WhatsApp, SMM) newest first."""
  items = []
  try:
    for country, yr, price, phone, d in cur.execute(
        "SELECT country, year, price, phone, date FROM orders WHERE user_id=?", (uid,)).fetchall():
      items.append({"ts": _order_ts(d), "kind": "tg", "country": country, "year": yr,
                    "price": price, "phone": phone, "btn": None})
  except Exception as ex:
    logger.warning(f"orders tg: {ex}")
  try:
    for oid, cname, ccode, number, price, status, code, d in cur.execute(
        "SELECT order_id, country_name, country_code, number, price, status, code, created_date "
        "FROM s2_orders WHERE user_id=? AND charged=1", (uid,)).fetchall():
      items.append({"ts": _order_ts(d), "kind": "s1", "country": cname, "ccode": ccode,
                    "price": price, "phone": number, "status": ("Code Ready" if code else _s1_status_text(status)),
                    "btn": f"srv1_ord|{oid}"})
  except Exception as ex:
    logger.warning(f"orders s1: {ex}")
  try:
    for o in _s2wa_user_orders(uid, 200):
      st = o.get("status", "")
      label = {"DONE": "Complete", "CANCELLED": "Cancelled", "WAIT_CODE": "Waiting",
               "WAIT_RETRY": "Retry"}.get(st, st.title() if st else "-")
      items.append({"ts": _order_ts(o.get("created_at")), "kind": "wa", "country": o.get("country_name"),
                    "price": o.get("price_inr"), "phone": o.get("phone"), "status": label,
                    "code": o.get("code"),
                    "btn": (f"s2wa_code:{o['activation_id']}" if st in ("WAIT_CODE", "WAIT_RETRY") else None)})
  except Exception as ex:
    logger.warning(f"orders wa: {ex}")
  try:
    for boid, sname, qty, price, status, d in cur.execute(
        "SELECT o.bot_order_id, COALESCE(s.name, 'Service ' || o.service_id), o.quantity, o.total_price, o.status, o.date "
        "FROM smm_orders o LEFT JOIN smm_services s ON s.service_id=o.service_id WHERE o.user_id=?", (uid,)).fetchall():
      items.append({"ts": _order_ts(d), "kind": "smm", "service": sname, "qty": qty,
                    "price": price, "boid": boid, "status": status, "btn": None})
  except Exception as ex:
    logger.warning(f"orders smm: {ex}")
  items.sort(key=lambda x: x["ts"], reverse=True)
  return items


async def orders_history_handler(event, is_callback=False, page=1):
  """ONE 'My Orders' screen: Telegram, WhatsApp and SMM orders together."""
  uid = event.sender_id
  items = collect_user_orders(uid)
  counts = {k: sum(1 for i in items if i["kind"] == k) for k in ("tg", "s1", "wa", "smm")}

  if not items:
    msg = f"{P_DOC} <b>My Orders</b>\n────────────────\n\n{P_WARN} <b>You don't have any orders yet.</b>"
    btns = [[Button.inline("Store", "cb_store")], [Button.inline("Back to Main", "back_main")]]
  else:
    total = len(items)
    pages = max(1, (total + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    page = max(1, min(int(page or 1), pages))
    chunk = items[(page - 1) * ORDERS_PER_PAGE: page * ORDERS_PER_PAGE]
    msg = (
      f"{P_DOC} {P_ROCKET} <b>My Orders</b>\n"
      f"────────────────\n"
      f"{P_PKG} <b>Total:</b> {total} | {P_TG} Telegram: {counts['tg'] + counts['s1']} | "
      f"{P_PHONE} WhatsApp: {counts['wa']} | {P_LIGHTNING} SMM: {counts['smm']}\n"
      f"{P_ASST} <b>Page:</b> {page} of {pages}\n\n"
    )
    btns = []
    for it in chunk:
      when = html.escape(it["ts"][:16])
      if it["kind"] == "tg":
        msg += (f"{P_TG} <b>Telegram Account</b>\n"
                f"{country_flag_html(None, it['country'])} {html.escape(str(it['country']))} ({it['year']}) — "
                f"<code>{html.escape(str(it['phone']))}</code>\n"
                f"{P_MONEY} ₹{it['price']} {P_CAL} {when}\n\n")
      elif it["kind"] == "s1":
        msg += (f"{P_TG} <b>Telegram Account</b> (Server 1)\n"
                f"{country_flag_html(it.get('ccode'), it['country'])} {html.escape(clean_country_name(it['country']))} — "
                f"<code>{html.escape(str(it['phone'] or 'Pending'))}</code>\n"
                f"{P_MONEY} ₹{it['price']} | {html.escape(it['status'])} {P_CAL} {when}\n\n")
      elif it["kind"] == "wa":
        code_txt = f" | {P_OTP} <code>{html.escape(str(it['code']))}</code>" if it.get("code") else ""
        msg += (f"{P_PHONE} <b>WhatsApp Account</b>\n"
                f"{country_flag_html(None, it['country'])} {html.escape(str(it['country']))} — "
                f"<code>{html.escape(str(it['phone']))}</code>\n"
                f"{P_MONEY} ₹{float(it['price'] or 0):.2f} | {html.escape(it['status'])}{code_txt} {P_CAL} {when}\n\n")
      else:
        msg += (f"{P_LIGHTNING} <b>SMM Service</b> #{it['boid']}\n"
                f"{P_GEAR} {html.escape(str(it['service']))}\n"
                f"{P_PKG} Qty: {it['qty']} | {P_MONEY} ₹{float(it['price'] or 0):.2f} | "
                f"{html.escape(str(it['status']))} {P_CAL} {when}\n\n")
      if it.get("btn"):
        label = {"s1": "Telegram", "wa": "WhatsApp"}.get(it["kind"], "Order")
        label = f"{label} {it.get('phone') or ''}".strip()[:40]
        btns.append([Button.inline(label, it["btn"])])
    nav = []
    if page > 1:
      nav.append(Button.inline("Prev", f"my_orders|{page-1}"))
    nav.append(Button.inline(f"{page}/{pages}", f"my_orders|{page}"))
    if page < pages:
      nav.append(Button.inline("Next", f"my_orders|{page+1}"))
    btns.append(nav)
    btns.append([Button.inline("Back to Main", "back_main")])

  if is_callback:
    try:
      await e_edit_or_send(event, custom_emoji_text(msg), btns)
    except MessageNotModifiedError:
      pass
  else:
    await bot.send_message(event.chat_id, custom_emoji_text(msg), buttons=btns, parse_mode='html')

async def payments_history_handler(event):
  uid = event.sender_id
  rows = cur.execute("SELECT amount, method_name, status, date FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,)).fetchall()
  
  if not rows:
    msg = f"{P_CARD} <b>You don't have any payment history yet.</b>"
  else:
    msg = f"{P_CARD} {P_MONEY} <b>Recent Payments:</b>\n\n"
    for amt, method, status, d in rows:
      msg += f"- ₹{amt} via {method} – <b>{status.upper()}</b> {P_YES}\n {P_CAL} {d}\n────────────────\n"

  btns = [[Button.inline("Back to Profile", "profile_callback")]]
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def _render_payment_methods(event):
  """Payment Methods admin screen. Toggle buttons ALWAYS flip the setting
  (previously the ON state sent a dead 'danger' callback, so it could never be
  switched off)."""
  ae = payment_enabled('fampay_enabled'); me = payment_enabled('manual_enabled')
  ue = payment_enabled('usdt_enabled')
  usdt_addr = get_usdt_address()
  msg = (f"{P_CARD} <b>Payment Methods</b>\n\n"
         f"FamPay Automatic: <b>{'ON' if ae else 'OFF'}</b>\n"
         f"UPI Manual: <b>{'ON' if me else 'OFF'}</b>\n"
         f"USDT Manual: <b>{'ON' if ue else 'OFF'}</b>\n\n"
         f"Automatic UPI: <code>{html.escape(get_fampay_upi())}</code>\n"
         f"Manual UPI: <code>{html.escape(get_manual_upi())}</code>\n"
         f"USDT Address: <code>{html.escape(usdt_addr or 'Not set')}</code>\n"
         f"USDT Network: <b>{html.escape(get_usdt_network())}</b>\n\n"
         f"<i>OFF methods are hidden from users in Add Funds. USDT Manual also stays hidden until an address is set.</i>")
  btns = [[Button.inline(f"FamPay Automatic: {'ON' if ae else 'OFF'}", "adm_toggle_fampay",
                         icon_custom_emoji_id=(_ICON_OK if ae else _ICON_NO))],
          [Button.inline(f"UPI Manual: {'ON' if me else 'OFF'}", "adm_toggle_manual",
                         icon_custom_emoji_id=(_ICON_OK if me else _ICON_NO))],
          [Button.inline(f"USDT Manual: {'ON' if ue else 'OFF'}", "adm_toggle_usdt",
                         icon_custom_emoji_id=(_ICON_OK if ue else _ICON_NO))],
          [Button.inline("Set FamPay UPI & Name", "adm_set_auto_upi")],
          [Button.inline("Set Manual UPI & Name", "adm_set_manual_upi")],
          [Button.inline("Set USDT Address & Network", "adm_set_usdt")],
          [Button.inline("Back to Admin", "adm_adminmain")]]
  try:
    return await event.edit(custom_emoji_text(msg), buttons=btns)
  except MessageNotModifiedError:
    return


async def deposit_menu(event):
  rows=[]
  if payment_enabled('fampay_enabled'):
    rows.append([Button.inline("FamPay Automatic", "depm_auto")])
  if payment_enabled('manual_enabled'):
    rows.append([Button.inline("UPI Manual", "depm_manual")])
  if usdt_manual_available():
    rows.append([Button.inline("USDT Manual", "depm_usdt")])
  rows.append([Button.inline("Back", "back_main")])
  msg=f"{P_CARD} {P_MONEY} <b>Select Payment Method</b>\n\nChoose an enabled method below."
  if len(rows) == 1:
    msg=f"{P_WARN} <b>Deposits are temporarily disabled.</b>\n\nNo payment method is available right now. Please contact support."
  if isinstance(event, events.CallbackQuery.Event): await event.edit(custom_emoji_text(msg),buttons=rows)
  else: await bot.send_message(event.chat_id,custom_emoji_text(msg),buttons=rows)

async def manual_deposit_init(event, method):
  """Open a button-based amount keypad for both payment methods."""
  uid = event.sender_id
  method_key = 'auto' if method == 'FamPay Automatic' else 'manual'
  deposit_input[uid] = {'step': 'amount_keypad', 'method': method, 'method_key': method_key, 'amount': ''}
  await show_deposit_amount_keypad(event, uid)

async def show_deposit_amount_keypad(event, uid):
  state = deposit_input.get(uid, {})
  method = state.get('method', 'UPI Manual')
  amount = state.get('amount', '') or '0'
  msg = (
    f"{P_CARD} <b>Custom Amount</b>\n\n"
    f"{P_MONEY} <b>Method:</b> {html.escape(method)}\n"
    f"{P_ASST} <b>Amount: ₹{html.escape(amount)}</b>\n\n"
    f"{P_ASST} <i>Enter the amount using the buttons:</i>"
  )
  btns = [
    [Button.inline(" 1", "dep_key|1"), Button.inline(" 2", "dep_key|2"), Button.inline(" 3", "dep_key|3")],
    [Button.inline(" 4", "dep_key|4"), Button.inline(" 5", "dep_key|5"), Button.inline(" 6", "dep_key|6")],
    [Button.inline(" 7", "dep_key|7"), Button.inline(" 8", "dep_key|8"), Button.inline(" 9", "dep_key|9")],
    [Button.inline(" Delete", "dep_key_del"), Button.inline(" 0", "dep_key|0"), Button.inline(" Confirm", "dep_key_confirm")],
    [Button.inline(" Back", "dep_menu_cb")]
  ]
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def generate_deposit_qr(event, uid):
  state = deposit_input.get(uid)
  if not state or state.get('step') != 'amount_keypad':
    return await safe_callback_answer(event, "Amount session expired. Please start again.", alert=True)
  raw_amount = state.get('amount', '')
  try:
    amt = int(raw_amount)
  except Exception:
    amt = 0
  if amt < 10:
    return await safe_callback_answer(event, "Minimum deposit is ₹10.", alert=True)

  method = state.get('method', 'UPI Manual')
  if method == 'USDT Manual':
    return await _generate_usdt_payment(event, uid, state, amt, raw_amount)
  is_auto = method == 'FamPay Automatic'
  upi_id = get_fampay_upi() if is_auto else get_manual_upi()
  payee = get_fampay_name() if is_auto else get_manual_name()

  # Keep the UPI URI internal only for QR generation. Never show a payment link to the user.
  upi_link = 'upi://pay?' + urlencode({'pa': upi_id, 'pn': payee, 'am': amt, 'cu': 'INR'})
  qr_url = 'https://api.qrserver.com/v1/create-qr-code/?size=350x350&data=' + quote(upi_link)
  qr_file = f"qr_{uid}_{int(time.time())}.png"

  await safe_callback_answer(event, "Generating payment QR...", alert=False)
  try:
    await event.edit(custom_emoji_text(f"{P_WAIT} <b>Generating payment QR...</b>\n\nAmount: <b>₹{amt}</b>"), buttons=[[Button.inline("Cancel", "cancel_action")]])
  except Exception:
    pass

  try:
    urllib.request.urlretrieve(qr_url, qr_file)
  except Exception as ex:
    logger.error(f"Deposit QR generation failed: {ex}")
    deposit_input[uid] = {'step': 'amount_keypad', 'method': method, 'method_key': state.get('method_key'), 'amount': raw_amount}
    return await event.edit(custom_emoji_text(f"{P_NO} <b>QR generation failed.</b>\n\nPlease try again."), buttons=[[Button.inline("Generate QR Again", "dep_key_confirm")], [Button.inline("Cancel", "cancel_action")]])

  deposit_input[uid] = {'step': 'wait_payment_verify', 'amount': amt, 'method': method, 'upi_id': upi_id, 'payee': payee}
  caption = (
    f"{P_CARD} <b>{html.escape(method)} Payment</b>\n\n"
    f"{P_MONEY} <b>Amount: ₹{amt}</b>\n"
    f"{P_ACC} <b>Payee: {html.escape(payee)}</b>\n\n"
    f"Scan the QR and complete the payment.\n"
    f"After payment, tap <b>Verify Payment</b> and send your payment screenshot."
  )
  btns = [[Button.inline(" Verify Payment", "dep_payment_verify")], [Button.inline(" Cancel", "cancel_action")]]
  try:
    await bot.send_file(uid, qr_file, caption=custom_emoji_text(caption), buttons=btns, force_document=False)
    try: os.remove(qr_file)
    except Exception: pass
    try: await event.delete()
    except Exception: pass
  except Exception as ex:
    logger.error(f"Failed to send deposit QR: {ex}")
    try: os.remove(qr_file)
    except Exception: pass
    deposit_input.pop(uid, None)
    await event.edit(custom_emoji_text(f"{P_NO} <b>Could not send the payment QR.</b> Please try again."), buttons=[[Button.inline("Back", "dep_menu_cb")]])

async def _generate_usdt_payment(event, uid, state, amt, raw_amount):
  """Manual USDT deposit: show address + exact USDT amount, then Send Screenshot / Cancel."""
  address = get_usdt_address()
  network = get_usdt_network()
  if not address or not payment_enabled('usdt_enabled'):
    deposit_input.pop(uid, None)
    return await event.edit(custom_emoji_text(f"{P_NO} <b>USDT payments are currently unavailable.</b>"),
                            buttons=[[Button.inline("Back", "dep_menu_cb")]])
  rate = get_usdt_rate()
  usdt_amount = max(0.01, round(amt / rate, 2))
  deposit_input[uid] = {'step': 'wait_payment_verify', 'amount': amt, 'method': 'USDT Manual',
                        'usdt_amount': usdt_amount, 'address': address, 'network': network}
  caption = (
    f"{P_USDT} <b>USDT Manual Payment</b>\n\n"
    f"{P_MONEY} <b>Send exactly:</b> <code>{usdt_amount:.2f}</code> USDT\n"
    f"{P_GLOBE} <b>Network:</b> <b>{html.escape(network)}</b>\n"
    f"{P_KEY} <b>Address:</b>\n<code>{html.escape(address)}</code>\n\n"
    f"{P_RATE} Rate: 1 USDT = ₹{rate:g}\n"
    f"{P_CARD} Wallet credit: <b>₹{amt}</b>\n\n"
    f"{P_WARN} <b>Only send USDT on the {html.escape(network)} network.</b> Funds sent on another network cannot be recovered.\n"
    f"After paying, tap <b>Send Screenshot</b> and upload your payment screenshot."
  )
  btns = [[Button.inline("Send Screenshot", "dep_payment_verify")], [Button.inline("Cancel", "cancel_action")]]
  qr_file = f"qr_usdt_{uid}_{int(time.time())}.png"
  try:
    urllib.request.urlretrieve(
      'https://api.qrserver.com/v1/create-qr-code/?size=350x350&data=' + quote(address), qr_file)
    await bot.send_file(uid, qr_file, caption=custom_emoji_text(caption), buttons=btns, force_document=False)
    try: await event.delete()
    except Exception: pass
  except Exception as ex:
    # QR is optional: fall back to the same details as a plain message.
    logger.warning(f"USDT QR failed, sending text only: {ex}")
    try:
      await event.edit(custom_emoji_text(caption), buttons=btns)
    except Exception:
      await bot.send_message(uid, custom_emoji_text(caption), buttons=btns, parse_mode='html')
  finally:
    try: os.remove(qr_file)
    except Exception: pass

async def confirm_purchase(event, country, year, price_str):
  uid = event.sender_id
  base_price = int(price_str)
  
  bal_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
  bal = bal_row[0] if bal_row else 0
  disc_row = cur.execute("SELECT discount FROM users WHERE user_id=?", (uid,)).fetchone()
  discount = disc_row[0] if disc_row else 0
  final_price = base_price if discount == 0 else int(base_price * (100 - discount) / 100)

  msg = (f"{P_CART} {P_FIRE} <b>Confirm Your Purchase</b> {P_STAR}\n\n"
      f"{P_FLAG} <b>Country:</b> {html.escape(country)}\n"
      f"{P_CAL} <b>Year:</b> {year}\n"
      f"{P_MONEY} <b>Final Price:</b> {P_INR}{final_price}\n\n"
      f"{P_CARD} <b>Your Balance:</b> {P_INR}{bal}\n\n"
      f"Do you want to proceed with this purchase? {P_ASST}")
  
  btns = [
    [Button.inline("Yes, Buy Now", f"buy_cf|{_country_token(country)}|{year}|{base_price}")],
    [Button.inline("No, Cancel", "cancel_action")]
  ]
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def process_purchase(event, country, year_str, price_str):
  uid, base_price = event.sender_id, int(price_str)

  disc_row = cur.execute("SELECT discount FROM users WHERE user_id=?", (uid,)).fetchone()
  discount = disc_row[0] if disc_row else 0
  final_price = base_price if discount == 0 else int(base_price * (100 - discount) / 100)

  async with get_user_lock(uid):
    row = cur.execute("SELECT phone, session_file, account_year, twofa FROM stock WHERE country_name LIKE ? AND account_year=? AND price=? AND available=1 LIMIT 1", (f"{country}%", int(year_str), base_price)).fetchone()

    if not row:
      return await safe_callback_answer(event, "Sold out! Another user just bought this account.", alert=True)
    
    phone, sess, actual_year, twofa_pass = row

    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (final_price, uid, final_price))
    if cur.rowcount == 0:
      return await safe_callback_answer(event, f"Insufficient Balance! Need ₹{final_price}", alert=True)

    cur.execute("UPDATE stock SET available=0 WHERE phone=?", (phone,))
    db.commit()

  await event.edit(custom_emoji_text(f"{P_WAIT} <b>Fetching Number (+{phone})...</b>"))
  clean_sess = sess if not sess.endswith(".session") else sess[:-8]
  client = TelegramClient(clean_sess, API_ID, API_HASH)
  
  try:
    await client.connect()
    if not await client.is_user_authorized(): raise Exception("Session dead")
  except Exception:
    async with get_user_lock(uid):
      cur.execute("DELETE FROM stock WHERE phone=?", (phone,))
      cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_price, uid))
      db.commit()
    await client.disconnect()
    delete_session_files(sess)
    return await event.edit(custom_emoji_text(f"{P_NO} <b>Account Invalid.</b> Money refunded. Try buying another."))

  msg = (f"{P_YES} {P_ROCKET} <b>Order Active!</b>\n\n"
      f"{P_PHONE} <b>Phone:</b> <code>{phone}</code>\n"
      f"{P_FLAG} <b>Country:</b> {html.escape(country)}\n\n"
      f"{P_STAR} <b>INSTRUCTIONS:</b>\n"
      f"1. Open Telegram & Add Account\n"
      f"2. Enter the number above.\n"
      f"3. {P_WAIT} <b>Please wait!</b> The bot is actively listening for your OTP and will send it automatically.\n\n"
      f"<i>{P_WARN} Note: If no OTP is received within 10 minutes, the bot will auto-cancel and refund your balance automatically.</i>")
  
  sent_msg = await event.edit(custom_emoji_text(msg))
  
  active_orders[phone] = {
    'uid': uid,
    'client': client, 'sess': sess, 'start_time': time.time(), 
    'paid': False, 'price': final_price, 'country': country, 'year': actual_year, 
    'twofa': twofa_pass, 'msg_id': sent_msg.id
  }
  asyncio.create_task(auto_otp_task(phone))

async def auto_otp_task(phone):
  if phone not in active_orders: return
  
  order = active_orders[phone]
  client = order['client']
  start_time = order['start_time']
  uid = order['uid']
  msg_id = order['msg_id']
  
  while time.time() - start_time < 600:
    if phone not in active_orders: return 
    try:
      msgs = await client.get_messages(777000, limit=5)
      code = None
      for m in msgs:
        if m.date.timestamp() > start_time - 10: 
          if m.message and re.search(r'\b\d{5}\b', m.message) and "Login detected" not in m.message:
            code = re.search(r'\b\d{5}\b', m.message).group()
            break
      
      if code:
        if not order['paid']:
          order['paid'] = True
          async with get_user_lock(uid):
            cur.execute("INSERT INTO orders (user_id, country, year, price, phone, otp) VALUES (?,?,?,?,?,?)", (uid, order['country'], order['year'], order['price'], phone, code))
            cur.execute("DELETE FROM stock WHERE phone=?", (phone,))
            db.commit()
          
          await log_primary_purchase(uid, order['country'], order['price'], order['price'], order['year'], 1, phone=phone)
        
        twofa_text = f"{P_2FA} <b>2FA:</b> <code>{html.escape(order['twofa'])}</code>" if order['twofa'] != "None" else f"{P_2FA} <b>2FA:</b> <code>Disabled (No Password)</code>"
        msg_text = (f"{P_YES} {P_FIRE} <b>Latest OTP Fetched!</b> {P_PARTY}\n\n"
              f"{P_PHONE} <b>Phone:</b> <code>{phone}</code>\n"
              f"{P_FLAG} <b>Country:</b> {html.escape(order['country'])}\n"
              f"{P_OTP} <b>OTP:</b> <code>{code}</code>\n"
              f"{twofa_text}")
        
        btns = [
          [Button.inline("Get OTP Again", f"get_otp_again|{phone}")],
          [Button.inline("Finish & Logout", f"logout_bot|{phone}")]
        ]
        try: await bot.edit_message(uid, msg_id, msg_text, buttons=btns)
        except: await bot.send_message(uid, msg_text, buttons=btns)
        return 
    except Exception: pass
    await asyncio.sleep(6) 
    
  if phone in active_orders and not active_orders[phone]['paid']:
    order = active_orders.pop(phone)
    try: await order['client'].disconnect()
    except: pass
    
    async with get_user_lock(uid):
      cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (order['price'], uid))
      cur.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
      db.commit()
      
    try: 
      await bot.edit_message(uid, msg_id, f"{P_TIME} <b>Order Expired!</b>\nThe 10-minute limit for <code>{phone}</code> ran out. Your money ({P_INR}{order['price']}) has been automatically refunded.")
    except: pass

async def init_session_purchase(event, country, year, price_str):
  uid, price = event.sender_id, int(price_str)
  stock_row = cur.execute("SELECT COUNT(*) FROM stock WHERE country_name LIKE ? AND account_year=? AND price=? AND available=1", (f"{country}%", int(year), price)).fetchone()
  stock = stock_row[0] if stock_row else 0
  if stock == 0: return await safe_callback_answer(event, "Out of stock!", alert=True)
  
  session_buy_state[uid] = {'country': country, 'year': year, 'price': price, 'stock': stock}
  disc_row = cur.execute("SELECT discount FROM users WHERE user_id=?", (uid,)).fetchone()
  discount = disc_row[0] if disc_row else 0
  p_disp = price if discount == 0 else int(price * (100 - discount) / 100)
  
  msg = (f"{P_STORE} {P_ROCKET} <b>Buy {html.escape(country)} ({year}) Sessions</b>\n\n"
      f"{P_MONEY} <b>Price per session:</b> {P_INR}{p_disp}\n"
      f"{P_PKG} <b>Available Stock:</b> {stock}\n\n"
      f"Reply to this message with the <b>Number of Sessions</b> you want to buy.")
  await event.edit(custom_emoji_text(msg), buttons=[[Button.inline("Cancel", "cancel_action")]])

async def process_bulk_sessions(event, uid, qty, state, final_cost):
  country, year, price = state['country'], int(state['year']), int(state['price'])
  await event.respond(custom_emoji_text(f"{P_WAIT} <b>Processing your sessions...</b>"))

  async with get_user_lock(uid):
    rows = cur.execute("SELECT phone, session_file, twofa, account_year FROM stock WHERE country_name LIKE ? AND account_year=? AND price=? AND available=1 LIMIT ?", (f"{country}%", year, price, qty)).fetchall()
    if len(rows) < qty:
      return await event.respond(custom_emoji_text(f"{P_NO} Stock changed during processing. Purchase Cancelled."))
    
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (final_cost, uid, final_cost))
    if cur.rowcount == 0:
      return await event.respond(custom_emoji_text(f"{P_NO} Insufficient Balance! Purchase Cancelled."))

    phones = [r[0] for r in rows]
    placeholders = ",".join("?" for _ in phones)
    cur.execute(f"UPDATE stock SET available=0 WHERE phone IN ({placeholders})", phones)
    
    price_per_acc = final_cost // qty
    for p in phones:
      cur.execute("INSERT INTO orders (user_id, country, price, phone, otp) VALUES (?,?,?,?,?)", (uid, country, price_per_acc, p, "SESSION_FILES"))
    db.commit()

  zip_name = f"sessions_{uid}_{int(time.time())}.zip"
  numbers_txt = ""

  try:
    with zipfile.ZipFile(zip_name, 'w') as zf:
      for phone, sess_file, twofa_pass, y in rows:
        base_s = sess_file if not sess_file.endswith(".session") else sess_file[:-8]
        for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
          src = base_s + ext
          if os.path.exists(src): zf.write(src, os.path.basename(src))
        
        pass_text = twofa_pass if twofa_pass != "None" else "No_Password"
        numbers_txt += f"+{phone} | pass:{pass_text}\n"
      
      numbers_txt += "\n\nPurchased from @Freshtgsales\n"
      zf.writestr("numbers.txt", numbers_txt)
      
    caption = f"{P_YES} {P_PARTY} <b>Bulk Purchase Successful!</b>\n\n{P_FLAG} Country: {html.escape(country)}\n{P_PKG} Quantity: {qty}\n{P_CARD} Total Paid: {P_INR}{final_cost}\n\n<i>(Note: Sessions are safely provided, the bot does not keep them active)</i>"
    await bot.send_file(uid, zip_name, caption=custom_emoji_text(caption))
    await log_primary_purchase(uid, country, price, final_cost, year, qty, phone=', '.join('+' + str(x) for x in phones))
  except Exception as e: await event.respond(custom_emoji_text(f"{P_WARN} Error creating zip: {e}"))
  finally:
    if os.path.exists(zip_name): os.remove(zip_name)

# ================= ADMIN PANEL =================
async def admin_panel_handler(event):
  uid = event.sender_id
  if not is_admin(uid): return
  
  status_text = BOT_STATUS_LABEL.get(get_bot_status(), "Bot ON")
  btns = []
  
  if uid == ADMIN_ID or has_perm(uid, 'p_settings'):
    btns.append([Button.inline(f"Status: {status_text}", "adm_togglebot")])
    
  r1 = []
  if uid == ADMIN_ID or has_perm(uid, 'p_add_stock') or has_perm(uid, 'p_manage_stock'):
    r1.append(Button.inline("Manual Acc", "adm_accmenu"))
  if uid == ADMIN_ID or has_perm(uid, 'p_manage_stock') or has_perm(uid, 'p_settings'):
    r1.append(Button.inline("SMM", "adm_smmmenu"))
  if r1: btns.append(r1)

  r3 = []
  if uid == ADMIN_ID or has_perm(uid, 'p_stats'):
    r3.extend([
      Button.inline("Statistics", "adm_stats"), 
      Button.inline("Broadcast", "adm_bcast")
    ])
    r3.append(Button.inline("User Info", "adm_userinfo"))
  if r3: btns.append(r3)

  r4 = []
  if uid == ADMIN_ID or has_perm(uid, 'p_bal'):
    r4.extend([
      Button.inline("Change Balance", "adm_bal"), 
      Button.inline("Ban User", "adm_ban")
    ])
  if r4: btns.append(r4)

  r5 = []
  if uid == ADMIN_ID or has_perm(uid, 'p_settings'):
    r5.extend([
      Button.inline("Discount", "adm_discount"), 
      Button.inline("USDT Rate", "adm_usdtrate")
    ])
    btns.append(r5)
    btns.append([
      Button.inline("Support User", "adm_supporturl"), 
      Button.inline("Support Channel", "adm_supportchan")
    ])
    btns.append([
      Button.inline("Update Welcome Photo", "adm_update_welcome_photo"),
      Button.inline("Change Logs Channel", "adm_changelogs")
    ])
    btns.append([
      Button.inline("Backup", "adm_backupusr"), 
      Button.inline("Restore", "adm_restoreusr")
    ])
    btns.append([
      Button.inline("Channels", "adm_forcechannels"),
      Button.inline("Payment Methods", "adm_paymentmethods")
    ])
    btns.append([
      Button.inline("Redeem Codes", "adm_redeemcodes"),
      Button.inline("Shop", "adm_digitalshop")
    ])
    btns.append([Button.inline("FamPay / IMAP", "adm_fampayset")])
    btns.append([Button.inline("Servers APIs", "adm_serverapis")])
    btns.append([Button.inline("Function Management", "fnmgmt_menu")])

  if uid == ADMIN_ID:
    btns.append([Button.inline("Manage Admins", "adm_manageadmins")])

  try:
    _total_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    _total_wallet = cur.execute("SELECT COALESCE(SUM(balance),0) FROM users").fetchone()[0] or 0
    _total_orders = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
  except Exception:
    _total_users = _total_wallet = _total_orders = 0

  _st = get_bot_status()
  _st_icon = {'on': P_ON, 'maintenance': P_WARN, 'off': P_OFF}.get(_st, P_ON)
  _st_name = {'on': 'Online', 'maintenance': 'Maintenance', 'off': 'Offline'}.get(_st, 'Online')
  dash_msg = (
    f"{P_PC} <b>ADVANCED ADMIN DASHBOARD</b> {P_CROWN}\n"
    f"────────────────\n\n"
    f"{P_STATS} <b>Bot Status:</b> {_st_icon} <b>{_st_name}</b>\n"
    f"<i>Tap the Status button to switch: ON → Maintenance → OFF</i>\n"
    f"{P_USERS} <b>Total Users:</b> <b>{_total_users}</b>\n"
    f"{P_MONEY} <b>Total Wallet:</b> {P_INR}{float(_total_wallet):.2f}\n"
    f"{P_CART} <b>Total Orders:</b> <b>{_total_orders}</b>"
  )
  await bot.send_message(event.chat_id, custom_emoji_text(dash_msg), buttons=btns)

async def manage_admins_menu(event):
  rows = cur.execute("SELECT user_id FROM admins").fetchall()
  msg = f"{P_USERS} <b>Manage Sub-Admins</b>\n\n"
  for r in rows: msg += f"{P_ACC} <code>{r[0]}</code>\n"
  btns = [
    [Button.inline("Add Admin", "adm_addadmin"), Button.inline("Edit Admin", "adm_editadminreq")],
    [Button.inline("Back", "adm_adminmain")]
  ]
  await event.edit(custom_emoji_text(msg), buttons=btns)

async def edit_admin_menu(event, target_id):
  row = cur.execute("SELECT p_add_stock, p_manage_stock, p_stats, p_bal, p_settings FROM admins WHERE user_id=?", (target_id,)).fetchone()
  if not row: return await safe_callback_answer(event, "Admin not found", alert=True)
  p = ["Yes" if x==1 else "No" for x in row]
  
  btns = [
    [Button.inline(f"Add Stock: {p[0]}", f"adm_tglperm|{target_id}|p_add_stock")],
    [Button.inline(f"Manage Stock: {p[1]}", f"adm_tglperm|{target_id}|p_manage_stock")],
    [Button.inline(f"Stats & Bcast: {p[2]}", f"adm_tglperm|{target_id}|p_stats")],
    [Button.inline(f"Bal & Users: {p[3]}", f"adm_tglperm|{target_id}|p_bal")],
    [Button.inline(f"Settings: {p[4]}", f"adm_tglperm|{target_id}|p_settings")],
    [Button.inline("Remove Admin", f"adm_deladmin|{target_id}")],
    [Button.inline("Back", "adm_manageadmins")]
  ]
  await event.edit(custom_emoji_text(f"{P_DOC} <b>Editing Admin:</b> <code>{target_id}</code>"), buttons=btns)

async def send_manage_stock_page(event, page):
  limit = 10
  offset = (page - 1) * limit
  rows = cur.execute("SELECT DISTINCT country_name FROM stock ORDER BY country_name").fetchall()
  total = len(rows)
  countries = rows[offset:offset+limit]
  
  btns = []
  for (c,) in countries: 
    btns.append([Button.inline(f"{html.escape(c)}", f"adm_msc|{c}")])
  
  nav = []
  if page > 1: nav.append(Button.inline("Prev", f"adm_mspg|{page-1}"))
  if offset + limit < total: nav.append(Button.inline("Next", f"adm_mspg|{page+1}"))
  if nav: btns.append(nav)
  btns.append([Button.inline("Back", "adm_adminmain")])
  await event.edit(custom_emoji_text(f"{P_DOC} <b>Manage Stock</b> (Page {page})\nSelect a country to edit its properties:"), buttons=btns)

async def send_manage_stock_country(event, c_name):
  years = cur.execute("SELECT DISTINCT account_year FROM stock WHERE country_name=? ORDER BY account_year DESC", (c_name,)).fetchall()
  btns = [
    [Button.inline("Edit Country Name", f"adm_msedit|name|{c_name}")],
    [Button.inline("Edit Common Price (All Years)", f"adm_msedit|cprice|{c_name}")]
  ]
  y_btns = []
  for (y,) in years: 
    y_btns.append(Button.inline(f"{y}", f"adm_msedit|yprice|{c_name}|{y}"))
  
  for i in range(0, len(y_btns), 3): btns.append(y_btns[i:i+3])
  btns.append([Button.inline("Back", "adm_mspg|1")])
  await event.edit(custom_emoji_text(f"{P_GLOBE} <b>Managing: {html.escape(c_name)}</b>\nSelect an option to edit:"), buttons=btns)

async def send_autoprice_page(event, page):
  limit = 10
  offset = (page - 1) * limit
  c_list = set([c for c in COUNTRY_CODES.values()])
  db_countries = cur.execute("SELECT DISTINCT country_name FROM stock").fetchall()
  for (c,) in db_countries: c_list.add(c)
  
  custom_countries = cur.execute("SELECT DISTINCT name FROM custom_countries").fetchall()
  for (c,) in custom_countries: c_list.add(c)

  c_list = sorted(list(c_list))
  total = len(c_list)
  countries = c_list[offset:offset+limit]
  
  btns = []
  for c in countries: 
    btns.append([Button.inline(f"{html.escape(c)}", f"adm_apc|{c}")])
    
  nav = []
  if page > 1: nav.append(Button.inline("Prev", f"adm_appg|{page-1}"))
  if offset + limit < total: nav.append(Button.inline("Next", f"adm_appg|{page+1}"))
  if nav: btns.append(nav)
  btns.append([Button.inline("Add Custom Country", "adm_ap_add_country")])
  btns.append([Button.inline("Back", "adm_adminmain")])
  await event.edit(custom_emoji_text(f"{P_ASST} <b>Auto Price Setup</b> (Page {page})\nSelect a country to set fixed prices:"), buttons=btns)

async def send_autoprice_country(event, c_name):
  btns = [[Button.inline("Set Common Price", f"adm_apset|{c_name}|Common")]]
  y_btns = []
  for y in range(2024, 1999, -1): 
    y_btns.append(Button.inline(f"{y}", f"adm_apset|{c_name}|{y}"))
  for i in range(0, len(y_btns), 4): btns.append(y_btns[i:i+4])
  btns.append([Button.inline("Back", "adm_appg|1")])
  await event.edit(custom_emoji_text(f"{P_GLOBE} <b>Auto Price: {html.escape(c_name)}</b>\nSelect 'Common' for default price, or specific years:"), buttons=btns)

async def admin_server_apis_menu(event):
  """Admin -> Servers APIs: pick a server, then manage its URL, key and margin."""
  msg = (
    f"{P_GEAR} <b>Servers APIs</b>\n"
    f"────────────────\n\n"
    f"Choose a server to change its API URL, API key and profit margin.\n\n"
  )
  btns = []
  for no, conf in SERVER_DEFS.items():
    api_url, api_key = get_server_api_config(no)
    status = "Configured" if (api_url and api_key) else "Not configured"
    msg += (f"{P_PC} <b>{conf['label']}</b> — <b>{status}</b>\n"
            f"{P_RATE} Profit Margin: <b>{get_server_margin(no):g}%</b>\n\n")
    btns.append([Button.inline(conf["label"], f"adm_srvapi_view|{no}")])
  btns.append([Button.inline("Back to Admin", "adm_adminmain")])
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def admin_server_view(event, server_no):
  """One server's settings page: change URL / key / margin, test, remove."""
  conf = SERVER_DEFS.get(int(server_no))
  if not conf:
    return await safe_callback_answer(event, "Unknown server.", alert=True)
  api_url, api_key = get_server_api_config(server_no)
  margin = get_server_margin(server_no)
  status = "Configured" if (api_url and api_key) else "Not configured"
  if conf.get("kind") == "tiger":
    about = (f"{P_ASST} <b>Server 2</b> sells WhatsApp OTP numbers through the Tiger SMS API. "
             f"Keep the provider balance topped up — users pay from their bot wallet.")
  else:
    about = (f"{P_ASST} <b>Server 1</b> uses the Nobelots Reseller API. Paste the "
             f"<code>nbl_live_...</code> key and keep the Nobelots wallet topped up — users pay from their bot wallet.")
  msg = (
    f"{P_GEAR} <b>{conf['label']}</b>\n"
    f"────────────────\n\n"
    f"{about}\n\n"
    f"{P_STATS} <b>Status:</b> {status}\n"
    f"{P_LINK} <b>API URL:</b> <code>{html.escape(api_url or 'Not set')}</code>\n"
    f"{P_KEY} <b>API Key:</b> <code>{html.escape(_mask_secret(api_key))}</code>\n"
    f"{P_RATE} <b>Profit Margin:</b> <b>{margin:g}%</b>"
  )
  btns = [
    [Button.inline("Change API URL", f"adm_srvapi_url|{server_no}")],
    [Button.inline("Change API Key", f"adm_srvapi_key|{server_no}")],
    [Button.inline(f"Set Profit Margin ({margin:g}%)", f"adm_srvapi_margin|{server_no}")],
    [Button.inline("Test API", f"adm_srvapi_test|{server_no}"),
     Button.inline("Remove API", f"adm_srvapi_del|{server_no}")],
    [Button.inline("Back to Servers APIs", "adm_serverapis")],
  ]
  return await e_edit_or_send(event, custom_emoji_text(msg), btns)


async def _server_quick_test(server_no):
  """Returns (ok, html_text) after checking the key against the provider."""
  conf = SERVER_DEFS.get(int(server_no)) or {}
  if conf.get("kind") == "tiger":
    try:
      bal = await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).balance)
      countries = await asyncio.to_thread(_s2wa_countries, True)
      try:
        rate = float(get_usdt_rate())
      except Exception:
        rate = 94.0
      return True, (f"{P_YES} <b>API connected!</b>\n"
                    f"{P_MONEY} Provider balance: ${bal:.4f} (≈ ₹{bal * rate:.2f})\n"
                    f"{P_PKG} Countries loaded: <b>{len(countries)}</b>")
    except Exception as ex:
      return False, f"{P_WARN} <b>Check failed:</b> {html.escape(_s2wa_human_error(ex))}"
  res = await asyncio.to_thread(fetch_phantom_balance, server_no)
  if isinstance(res, dict) and res.get("ok"):
    countries = await asyncio.to_thread(fetch_s2_countries, True)
    count = len(countries) if isinstance(countries, list) else 0
    return True, (f"{P_YES} <b>API connected!</b>\n"
                  f"{P_MONEY} API Wallet: ₹{res.get('balance', '-')}\n"
                  f"{P_PKG} Countries loaded: <b>{count}</b>")
  return False, f"{P_WARN} <b>Check failed:</b> {html.escape(_api_error_text(res))}"


async def admin_server_api_test(event, server_no):
  conf = SERVER_DEFS.get(server_no)
  if not conf:
    return await safe_callback_answer(event, "Unknown server.", alert=True)
  api_url, api_key = get_server_api_config(server_no)
  if not api_url or not api_key:
    return await safe_callback_answer(event, "Set the API URL and key first.", alert=True)

  await safe_callback_answer(event, "Testing API...", alert=False)
  lines = [f"{P_GEAR} <b>{conf['name']} API Test</b>", "────────────────", ""]

  if conf.get("kind") == "tiger":
    ok, text = await _server_quick_test(server_no)
    lines.append(text)
    if ok:
      try:
        available = await asyncio.to_thread(_s2wa_available)
        lines.append(f"{P_PKG} In stock: <b>{len(available)}</b> countries")
        preview = ""
        for c in available[:5]:
          preview += (f"{_s2wa_flag_html(c)} {html.escape(str(c['name']))} — "
                      f"₹{_s2wa_sell_price(c['cost']):.0f} ({c['count']})\n")
        if preview:
          lines.append("")
          lines.append(preview.rstrip())
      except Exception as ex:
        lines.append(f"{P_WARN} Price list: {html.escape(_s2wa_human_error(ex))}")
  else:
    balance_res = await asyncio.to_thread(fetch_phantom_balance, server_no)
    countries = await asyncio.to_thread(fetch_s2_countries, True)
    ok = isinstance(balance_res, dict) and balance_res.get("ok")
    if ok:
      lines.append(f"{P_YES} <b>Key Status:</b> Valid")
      lines.append(f"{P_MONEY} <b>API Wallet:</b> ₹{balance_res.get('balance', '-')} "
                   f"{html.escape(str(balance_res.get('currency') or 'INR'))}")
      if balance_res.get("spent_today") is not None:
        lines.append(f"{P_STATS} <b>Spent Today:</b> ₹{balance_res.get('spent_today')}")
      key_info = balance_res.get("key") if isinstance(balance_res.get("key"), dict) else {}
      if key_info.get("label"):
        lines.append(f"{P_KEY} <b>Key:</b> {html.escape(str(key_info.get('label')))}")
    else:
      lines.append(f"{P_NO} <b>Key Status:</b> Failed")
      lines.append(f"{P_WARN} {html.escape(_api_error_text(balance_res))}")

    if isinstance(countries, list):
      in_stock = [c for c in countries if int(c.get('stock') or 0) > 0]
      lines.append(f"{P_PKG} <b>Countries:</b> {len(countries)} ({len(in_stock)} in stock)")
      preview = ""
      for c in in_stock[:5]:
        pcode = str(c.get("code") or "").strip().upper()
        pname = clean_country_name(c.get("name") or pcode)
        preview += (f"{country_flag_html(pcode, pname)} {html.escape(pname)} — ₹{server_sell_price(c.get('price'))}"
                    f" ({c.get('stock')})\n")
      if preview:
        lines.append("")
        lines.append(preview.rstrip())
    else:
      lines.append(f"{P_WARN} Countries: {html.escape(str(countries.get('error')))}")

  lines.append("")
  lines.append(f"{P_LINK} URL: <code>{html.escape(api_url)}</code>")
  lines.append(f"{P_RATE} Margin: <b>{get_server_margin(server_no):g}%</b>")

  btns = [
    [Button.inline("Test Again", f"adm_srvapi_test|{server_no}")],
    [Button.inline(f"Back to {conf['name']}", f"adm_srvapi_view|{server_no}")],
  ]
  return await e_edit_or_send(event, custom_emoji_text("\n".join(lines)), btns)


def _reset_server_caches(server_no):
  if int(server_no) == 2:
    try:
      _S2WA_CACHE["countries"] = (0, None)
      _S2WA_CACHE["prices"] = {}
      _S2WA_CACHE["map"] = (0, None)
      _S2WA_CACHE["service"] = (0, None)
    except Exception:
      pass
  else:
    _s2_countries_cache["ts"] = 0
    _s2_countries_cache["data"] = []


class _AdminChatReply:
  """Lets a settings page be re-shown as a fresh message after a text conversation."""
  def __init__(self, chat_id, sender_id):
    self.chat_id = chat_id
    self.sender_id = sender_id

  async def respond(self, msg, buttons=None, parse_mode='html'):
    return await bot.send_message(self.chat_id, msg, buttons=buttons, parse_mode=parse_mode)


async def admin_actions(event):
  data_full = event.data.decode()
  if not data_full.startswith("adm_"): return
  uid = event.sender_id
  action_data = data_full[4:]
  chat = event.chat_id
  
  if action_data == "adminmain":
    await event.delete()
    class FakeEvent: chat_id = chat; sender_id = uid
    return await admin_panel_handler(FakeEvent())

  if action_data == "togglebot" and has_perm(uid, 'p_settings'):
    new_status = set_bot_status(BOT_STATUS_NEXT.get(get_bot_status(), 'maintenance'))
    _alert = {'on': "Bot is now ON - everyone can use it.",
              'maintenance': "Maintenance mode ON - only admins can use the bot.",
              'off': "Bot is now OFF - only admins can use it."}[new_status]
    await safe_callback_answer(event, _alert, alert=True)
    class FakeEvent: chat_id = chat; sender_id = uid
    await admin_panel_handler(FakeEvent())
    await event.delete()
    return

  elif action_data == "forcechannels":
    rows = cur.execute("SELECT id, channel_id, title FROM force_channels").fetchall()
    msg = f"{P_USERS} <b>Manage Force Channels</b>\n\n"
    if not rows: msg += "No force channels added yet."
    else: msg += "Tap a channel to remove it or change its link."
    btns = [[Button.inline(str(r[2] or r[1])[:40], f"adm_fch|{r[0]}", icon_custom_emoji_id="5832538679997895284")] for r in rows]
    btns.append([Button.inline("Add Channel", "adm_add_fchan")])
    btns.append([Button.inline("Back to Admin", "adm_adminmain")])
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data.startswith("fch|"):
    fid = int(action_data.split("|")[1])
    r = cur.execute("SELECT id, channel_id, invite_url, title FROM force_channels WHERE id=?", (fid,)).fetchone()
    if not r:
      return await safe_callback_answer(event, "Channel not found.", alert=True)
    msg = (f"{P_GLOBE} <b>{html.escape(str(r[3] or 'Channel'))}</b>\n\n"
           f"{P_ID} Chat ID: <code>{html.escape(str(r[1]))}</code>\n"
           f"{P_LINK} Link: {html.escape(str(r[2] or ''))}")
    btns = [
      [Button.inline("Remove Channel", f"adm_fchdel|{r[0]}")],
      [Button.inline("Change Link", f"adm_fchlink|{r[0]}", icon_custom_emoji_id="5834886399316201457")],
      [Button.inline("Back", "adm_forcechannels")]
    ]
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data.startswith("fchdel|"):
    fid = int(action_data.split("|")[1])
    r = cur.execute("SELECT channel_id FROM force_channels WHERE id=?", (fid,)).fetchone()
    if r:
      cur.execute("DELETE FROM force_join_requests WHERE channel_id=?", (str(r[0]),))
    cur.execute("DELETE FROM force_channels WHERE id=?", (fid,))
    db.commit()
    await safe_callback_answer(event, "Force channel removed!", alert=True)
    rows = cur.execute("SELECT id, channel_id, title FROM force_channels").fetchall()
    msg = f"{P_USERS} <b>Manage Force Channels</b>\n\n" + ("Tap a channel to remove it or change its link." if rows else "No force channels added yet.")
    btns = [[Button.inline(str(x[2] or x[1])[:40], f"adm_fch|{x[0]}", icon_custom_emoji_id="5832538679997895284")] for x in rows]
    btns.append([Button.inline("Add Channel", "adm_add_fchan")])
    btns.append([Button.inline("Back to Admin", "adm_adminmain")])
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data == "paymentmethods" and has_perm(uid, 'p_settings'):
    return await _render_payment_methods(event)

  elif action_data == "toggle_fampay" and has_perm(uid, 'p_settings'):
    set_setting('fampay_enabled', 'off' if payment_enabled('fampay_enabled') else 'on')
    await safe_callback_answer(event, "FamPay Automatic: " + ("ON" if payment_enabled('fampay_enabled') else "OFF"))
    return await _render_payment_methods(event)

  elif action_data == "toggle_manual" and has_perm(uid, 'p_settings'):
    set_setting('manual_enabled', 'off' if payment_enabled('manual_enabled') else 'on')
    await safe_callback_answer(event, "UPI Manual: " + ("ON" if payment_enabled('manual_enabled') else "OFF"))
    return await _render_payment_methods(event)

  elif action_data == "toggle_usdt" and has_perm(uid, 'p_settings'):
    set_setting('usdt_enabled', 'off' if payment_enabled('usdt_enabled') else 'on')
    await safe_callback_answer(event, "USDT Manual: " + ("ON" if payment_enabled('usdt_enabled') else "OFF"))
    return await _render_payment_methods(event)

  elif action_data == "set_usdt" and has_perm(uid, 'p_settings'):
    await event.delete()
    async with bot.conversation(chat, timeout=300) as conv:
      async def get_reply(txt):
        await conv.send_message(custom_emoji_text(txt+"\n\n<i>(Type /cancel to abort)</i>")); r=await conv.get_response()
        if (r.raw_text or '').strip().lower()=='/cancel': raise ValueError
        return r
      try:
        addr=(await get_reply(f"{P_KEY} <b>Enter your USDT wallet address:</b>")).raw_text.strip()
        net=(await get_reply(f"{P_GLOBE} <b>Enter the network</b> (for example TRC20, BEP20, ERC20):")).raw_text.strip().upper()
        if len(addr) < 20 or re.search(r"\s", addr):
          return await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid wallet address.</b>"))
        if not re.fullmatch(r"[A-Z0-9 _\-]{2,20}", net):
          return await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid network name.</b>"))
        set_setting('usdt_address', addr); set_setting('usdt_network', net)
        await conv.send_message(custom_emoji_text(
          f"{P_YES} <b>USDT settings saved.</b>\n\n{P_KEY} <code>{html.escape(addr)}</code>\n{P_GLOBE} Network: <b>{html.escape(net)}</b>"))
      except ValueError: await conv.send_message("Cancelled.")
    return

  elif action_data in ("set_auto_upi","set_manual_upi") and has_perm(uid, 'p_settings'):
    is_auto = action_data == "set_auto_upi"
    await event.delete()
    async with bot.conversation(chat, timeout=300) as conv:
      async def get_reply(txt):
        await conv.send_message(custom_emoji_text(txt+"\n\n<i>(Type /cancel to abort)</i>")); r=await conv.get_response()
        if (r.text or '').strip().lower()=='/cancel': raise ValueError
        return r
      try:
        upi=(await get_reply("Enter UPI ID:")).text.strip(); name=(await get_reply("Enter Payee Name:")).text.strip()
        if not re.match(r"^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+$",upi): return await conv.send_message("Invalid UPI ID.")
        prefix='fampay' if is_auto else 'manual'
        set_setting(prefix+'_upi',upi); set_setting(prefix+'_name',name)
        await conv.send_message(custom_emoji_text("Payment UPI settings saved successfully."))
      except ValueError: await conv.send_message("Cancelled.")
    return

  elif action_data == "fampayset":
    upi = get_fampay_upi()
    name = get_fampay_name()
    msg = (f"{P_CARD} <b>FamPay / UPI & IMAP Settings</b>\n\n"
        f"Current UPI ID: <code>{upi}</code>\n"
        f"Payee Name: <code>{name}</code>\n\n"
        f"Click below to update UPI ID, Payee Name, or IMAP configuration for automatic verification.")
    btns = [
      [Button.inline("Change FamPay UPI & Name", "adm_set_auto_upi")],
      [Button.inline("Change Manual UPI & Name", "adm_set_manual_upi")],
      [Button.inline("Configure IMAP (Gmail)", "adm_set_imap")],
      [Button.inline("Payment Methods", "adm_paymentmethods")],
      [Button.inline("Back to Admin", "adm_adminmain")]
    ]
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data == "accmenu" and (uid == ADMIN_ID or has_perm(uid, 'p_add_stock') or has_perm(uid, 'p_manage_stock')):
    btns = []
    if uid == ADMIN_ID or has_perm(uid, 'p_add_stock'):
      btns.append([Button.inline("Add Single Acc", "adm_addstock"), Button.inline("Add ZIP", "adm_addzip")])
    if uid == ADMIN_ID or has_perm(uid, 'p_manage_stock'):
      btns.append([Button.inline("Manage Acc", "adm_managestock"), Button.inline("Auto Price", "adm_autoprice")])
      btns.append([Button.inline("Delete Account", "adm_delacc")])
    btns.append([Button.inline("Back to Admin", "adm_adminmain")])
    return await event.edit(custom_emoji_text(f"{P_ACC} <b>Manual Acc (TG Accounts)</b>\n\nManage your own Telegram account stock:"), buttons=btns)

  elif action_data == "smmmenu" and (uid == ADMIN_ID or has_perm(uid, 'p_manage_stock') or has_perm(uid, 'p_settings')):
    btns = []
    if uid == ADMIN_ID or has_perm(uid, 'p_settings'):
      btns.append([Button.inline("SMM API", "adm_smm_api"), Button.inline("Categories", "adm_smm_cats")])
    if uid == ADMIN_ID or has_perm(uid, 'p_manage_stock'):
      btns.append([Button.inline("Add Service", "adm_smm_addsrv"), Button.inline("Bulk Add", "adm_smm_bulksrv")])
      btns.append([Button.inline("Manage", "adm_smm_managesrv"), Button.inline("Delete", "adm_smm_delsrv")])
    btns.append([Button.inline("Back to Admin", "adm_adminmain")])
    return await event.edit(custom_emoji_text(f"{P_FOLDER} <b>SMM Controls</b>\n\nManage SMM API, categories and services:"), buttons=btns)

  elif action_data == "smm_cats":
    rows = cur.execute("SELECT id, name FROM smm_categories").fetchall()
    msg = f"{P_FOLDER} <b>Manage SMM Categories</b>\n\n"
    if not rows: msg += "No categories created yet."
    else:
      for r in rows: msg += f"ID: {r[0]} | Name: {html.escape(r[1])}\n"
    btns = [
      [Button.inline(" Create Category", "adm_smm_addcat")],
      [Button.inline(" Remove Category", "adm_smm_delcat")],
      [Button.inline(" Back to Admin", "adm_adminmain")]
    ]
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data == "smm_managesrv":
    rows = cur.execute("SELECT service_id, name FROM smm_services LIMIT 15").fetchall()
    if not rows: return await safe_callback_answer(event, "No services added yet.", alert=True)
    msg = f"{P_GEAR} <b>Manage SMM Service</b>\nSelect a service to edit:"
    btns = []
    for sid, sname in rows:
      btns.append([Button.inline(f"Edit: {sname} ({sid})", f"adm_smm_editsrv|{sid}")])
    btns.append([Button.inline(" Back", "adm_adminmain")])
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data.startswith("smm_editsrv|"):
    sid = int(action_data.split("|")[1])
    await event.delete()
    class FakeEvent: chat_id = chat; sender_id = uid
    async with bot.conversation(chat, timeout=600) as conv:
      async def get_reply(txt):
        await conv.send_message(custom_emoji_text(txt + "\n\n<i>(Type /cancel to abort)</i>"))
        resp = await conv.get_response()
        if resp.text == "/cancel": raise ValueError("Cancelled")
        return resp
      try:
        edit_msg = (f"{P_GEAR} <b>Editing Service ID: {sid}</b>\n"
              f"1. Edit Name\n2. Edit Description\n3. Edit Price (Rate)\n4. Edit Category\n\n"
              f"Reply with option number (1, 2, 3, or 4):")
        opt = (await get_reply(edit_msg)).text.strip()
        if opt == '1':
          new_name = (await get_reply("Enter new Service Name:")).text.strip()
          cur.execute("UPDATE smm_services SET name=? WHERE service_id=?", (new_name, sid))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Service Name updated successfully!"))
        elif opt == '2':
          new_desc = (await get_reply("Enter new Description:")).text.strip()
          cur.execute("UPDATE smm_services SET description=? WHERE service_id=?", (new_desc, sid))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Service Description updated successfully!"))
        elif opt == '3':
          new_rate = float((await get_reply("Enter new Price (Rate per 1k):")).text.strip())
          cur.execute("UPDATE smm_services SET rate=? WHERE service_id=?", (new_rate, sid))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Service Price updated successfully!"))
        elif opt == '4':
          cats = cur.execute("SELECT id, name FROM smm_categories").fetchall()
          c_txt = "Select new Category ID:\n"
          for c in cats: c_txt += f"ID: {c[0]} - {c[1]}\n"
          new_cid = int((await get_reply(c_txt)).text.strip())
          cur.execute("UPDATE smm_services SET category_id=? WHERE service_id=?", (new_cid, sid))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Service Category updated successfully!"))
        else:
          await conv.send_message(custom_emoji_text("Invalid option selected."))
      except ValueError: await conv.send_message(custom_emoji_text(f"{P_NO} Cancelled."))
      except Exception as ex: await conv.send_message(custom_emoji_text(f"{P_NO} Error: {ex}"))
    return

  elif action_data == "smm_delsrv":
    rows = cur.execute("SELECT service_id, name FROM smm_services LIMIT 15").fetchall()
    if not rows: return await safe_callback_answer(event, "No services added yet.", alert=True)
    msg = f"{P_NO} <b>Remove Service</b>\nSelect service ID to delete:"
    btns = []
    for sid, sname in rows:
      btns.append([Button.inline(f"Del: {sname} ({sid})", f"adm_smm_dsrv|{sid}")])
    btns.append([Button.inline(" Back", "adm_adminmain")])
    return await event.edit(custom_emoji_text(msg), buttons=btns)

  elif action_data.startswith("smm_dsrv|"):
    sid = int(action_data.split("|")[1])
    cur.execute("DELETE FROM smm_services WHERE service_id=?", (sid,))
    db.commit()
    await safe_callback_answer(event, "Service Removed Successfully!", alert=True)
    class FakeEvent: chat_id = chat; sender_id = uid
    return await admin_panel_handler(FakeEvent())

  elif action_data == "redeemcodes" and has_perm(uid, 'p_settings'):
    rows=cur.execute("SELECT code,amount,max_users,used_count,active FROM redeem_codes ORDER BY created_date DESC LIMIT 20").fetchall()
    msg=f"{P_GIFT} <b>Redeem Codes</b>\n\n"
    for code,amount,mx,used,active in rows: msg += f"<code>{html.escape(code)}</code> - ₹{amount} - {used}/{mx} - {'ON' if active else 'OFF'}\n"
    if not rows: msg += "No redeem codes created yet.\n"
    btns=[[Button.inline("Create Code","adm_redeem_add")],[Button.inline("Remove Code","adm_redeem_remove")],[Button.inline("Back to Admin","adm_adminmain")]]
    return await event.edit(custom_emoji_text(msg),buttons=btns)

  elif action_data in ("redeem_add","redeem_remove") and has_perm(uid, 'p_settings'):
    await event.delete()
    async with bot.conversation(chat, timeout=300) as conv:
      async def get_reply(txt):
        await conv.send_message(custom_emoji_text(txt+"\n\n<i>(Type /cancel to abort)</i>")); r=await conv.get_response()
        if (r.text or '').strip().lower()=='/cancel': raise ValueError
        return r
      try:
        if action_data == 'redeem_add':
          code=(await get_reply("Enter code (e.g. AKOP):")).text.strip().upper()
          amount=int((await get_reply("Enter amount in INR (e.g. 5):")).text.strip())
          max_users=int((await get_reply("Enter max users (e.g. 10):")).text.strip())
          if not re.fullmatch(r"[A-Z0-9_-]{3,40}",code) or amount<=0 or max_users<=0: raise ValueError
          cur.execute("INSERT OR REPLACE INTO redeem_codes(code,amount,max_users,used_count,created_by,active) VALUES(?,?,?,?,?,1)",(code,amount,max_users,0,uid)); db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} <b>Redeem Code Created</b>\n\n<code>{code}</code> {amount} {max_users}"))
        else:
          code=(await get_reply("Enter code to remove:")).text.strip().upper()
          cur.execute("UPDATE redeem_codes SET active=0 WHERE code=?",(code,)); db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Code <code>{html.escape(code)}</code> removed."))
      except ValueError: await conv.send_message("Invalid input or cancelled.")
    return

  elif action_data == "digitalshop" and has_perm(uid, 'p_settings'):
    return await digital_shop_admin_menu(event)

  elif action_data in ("digital_add","digital_remove") and has_perm(uid, 'p_settings'):
    await event.delete()
    async with bot.conversation(chat, timeout=600) as conv:
      async def get_reply(txt):
        await conv.send_message(custom_emoji_text(txt+"\n\n<i>(Type /cancel to abort)</i>")); r=await conv.get_response()
        if (r.text or '').strip().lower()=='/cancel': raise ValueError
        return r
      try:
        if action_data == 'digital_add':
          _SKIP = ('skip', '/skip', 'none', 'no', '-', 'na', 'n/a')
          name=((await get_reply("Enter Product Name:")).raw_text or '').strip()
          if not name: raise ValueError

          # Description is optional.
          desc_msg = await get_reply("Enter Product Description, or type <b>skip</b> to leave it empty:")
          desc = (desc_msg.text or '').strip()
          if desc.lower() in _SKIP: desc = ''

          # Price is the ONLY required value besides the name.
          price=int((await get_reply("Enter Product Price (₹) <b>(required)</b>:")).text.strip())
          if price<=0: raise ValueError

          # Preview image is optional.
          preview = await get_reply("Send product preview photo/screenshot now, or type <b>skip</b> to continue without a preview:")
          preview_path = ''
          preview_file_id = ''
          preview_text = (preview.text or '').strip().lower()
          if preview_text not in _SKIP:
            if not preview.photo:
              return await conv.send_message(custom_emoji_text(f"{P_NO} Please send a photo/screenshot or type <b>skip</b>."))
            os.makedirs('digital_shop/previews',exist_ok=True)
            preview_path = await bot.download_media(preview, file='digital_shop/previews/') or ''
            preview_file_id = str(preview.photo.id)

          # Delivery file is optional too. Without a file the buyer gets the
          # product name + description as a text message after paying.
          product_file = await get_reply("Now send the <b>product file</b> to deliver after purchase (document/file/photo), or type <b>skip</b> to deliver the description as text:")
          file_path = '__none__'
          if (product_file.text or '').strip().lower() in _SKIP and not getattr(product_file, 'media', None):
            pass
          elif not getattr(product_file, 'media', None):
            return await conv.send_message(custom_emoji_text(f"{P_NO} Please send a file or type <b>skip</b>."))
          else:
            os.makedirs('digital_shop/files',exist_ok=True)
            file_path = await bot.download_media(product_file, file='digital_shop/files/') or ''
            if not file_path or not os.path.isfile(file_path):
              return await conv.send_message(custom_emoji_text(f"{P_NO} Product file could not be saved. Please try again."))

          cur.execute("INSERT INTO digital_products(name,description,price,photo_file_id,photo_path,file_path) VALUES(?,?,?,?,?,?)",(name,desc,price,preview_file_id,preview_path,file_path))
          db.commit()
          preview_status = 'Preview added' if preview_path else 'No preview'
          file_status = 'Delivery file saved' if file_path != '__none__' else 'No file (text delivery)'
          desc_status = 'Description added' if desc else 'No description'
          await conv.send_message(custom_emoji_text(f"{P_YES} Product <b>{html.escape(name)}</b> added successfully.\n\nPrice: ₹{price}\n{desc_status}\n{preview_status}\n{file_status}"))
        else:
          pid=int((await get_reply("Enter Product ID to remove:")).text.strip())
          cur.execute("UPDATE digital_products SET active=0 WHERE id=?",(pid,)); db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Product #{pid} removed from the shop."))
      except ValueError: await conv.send_message("Invalid input or cancelled.")
      except Exception as ex: await conv.send_message(custom_emoji_text(f"{P_NO} Error: {html.escape(str(ex))}"))
    return

  elif action_data == "stats" and has_perm(uid, 'p_stats'):
    u_row = cur.execute("SELECT COUNT(*) FROM users").fetchone()
    u = u_row[0] if u_row else 0
    s_row = cur.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()
    s = s_row[0] if s_row else 0
    bal_row = cur.execute("SELECT SUM(balance) FROM users").fetchone()
    total_bal = bal_row[0] if bal_row and bal_row[0] else 0
    o_row = cur.execute("SELECT COUNT(*), SUM(price) FROM orders").fetchone()
    total_orders = o_row[0] if o_row else 0
    total_spent = o_row[1] if o_row and o_row[1] else 0
    
    msg = (f"{P_STATS} <b>ADVANCED STATS</b>\n\n{P_USERS} <b>Total Users:</b> {u}\n{P_PKG} <b>Accounts in Stock:</b> {s}\n\n"
        f"{P_CARD} <b>Overall Users Balance:</b> {P_INR}{total_bal}\n"
        f"{P_CART} <b>Total Accounts Sold:</b> {total_orders}\n{P_USDT} <b>Overall Sales Amount:</b> {P_INR}{total_spent}")
    return await event.edit(custom_emoji_text(msg), buttons=[[Button.inline("Back", "adm_adminmain")]])

  elif action_data == "manageadmins" and uid == ADMIN_ID:
    return await manage_admins_menu(event)

  elif action_data.startswith("tglperm|") and uid == ADMIN_ID:
    _, t_id, p_name = action_data.split("|")
    cur.execute(f"UPDATE admins SET {p_name} = CASE WHEN {p_name}=1 THEN 0 ELSE 1 END WHERE user_id=?", (t_id,))
    db.commit()
    return await edit_admin_menu(event, t_id)
    
  elif action_data.startswith("deladmin|") and uid == ADMIN_ID:
    t_id = action_data.split("|")[1]
    cur.execute("DELETE FROM admins WHERE user_id=?", (t_id,))
    db.commit()
    await safe_callback_answer(event, "Admin Removed", alert=True)
    return await manage_admins_menu(event)

  elif action_data == "managestock" and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_page(event, 1)
  elif action_data.startswith("mspg|") and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_page(event, int(action_data.split("|")[1]))
  elif action_data.startswith("msc|") and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_country(event, action_data.split("|")[1])
  elif action_data == "autoprice" and has_perm(uid, 'p_manage_stock'): return await send_autoprice_page(event, 1)
  elif action_data.startswith("appg|") and has_perm(uid, 'p_manage_stock'): return await send_autoprice_page(event, int(action_data.split("|")[1]))
  elif action_data.startswith("apc|") and has_perm(uid, 'p_manage_stock'): return await send_autoprice_country(event, action_data.split("|")[1])
    
  elif action_data == "backupusr" and has_perm(uid, 'p_settings'):
    if uid != ADMIN_ID:
      return await safe_callback_answer(event, "Only the owner can create a full backup.", alert=True)
    await safe_callback_answer(event, "Creating full backup...", alert=False)
    zip_path = None
    try:
      zip_path, n_files = await asyncio.to_thread(build_full_backup)
      size_mb = os.path.getsize(zip_path) / (1024 * 1024)
      await bot.send_file(
        chat, zip_path, force_document=True,
        caption=custom_emoji_text(
          f"{P_FOLDER} <b>Full Backup</b>\n"
          f"{P_DOC} Script + Database + {n_files} session/media files\n"
          f"{P_TIME} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {size_mb:.1f} MB\n\n"
          f"<i>Use the Restore button and send this zip to restore everything.</i>"))
    except Exception as ex:
      logger.error(f"Full backup failed: {ex}", exc_info=True)
      await bot.send_message(chat, custom_emoji_text(f"{P_NO} Backup failed: {html.escape(str(ex))}"))
    finally:
      if zip_path and os.path.exists(zip_path):
        try: os.remove(zip_path)
        except Exception: pass
    return

  elif action_data == "serverapis" and has_perm(uid, 'p_settings'):
    return await admin_server_apis_menu(event)

  elif action_data.startswith("srvapi_view|") and has_perm(uid, 'p_settings'):
    try:
      server_no = int(action_data.split("|")[1])
    except Exception:
      return await safe_callback_answer(event, "Invalid server.", alert=True)
    return await admin_server_view(event, server_no)

  elif action_data.startswith("srvapi_test|") and has_perm(uid, 'p_settings'):
    try:
      server_no = int(action_data.split("|")[1])
    except Exception:
      return await safe_callback_answer(event, "Invalid server.", alert=True)
    return await admin_server_api_test(event, server_no)

  elif action_data.startswith("srvapi_del|") and has_perm(uid, 'p_settings'):
    try:
      server_no = int(action_data.split("|")[1])
    except Exception:
      return await safe_callback_answer(event, "Invalid server.", alert=True)
    conf = SERVER_DEFS.get(server_no)
    if conf:
      set_setting(conf["url_key"], "")
      set_setting(conf["key_key"], "")
      _reset_server_caches(server_no)
    await safe_callback_answer(event, "Server API removed.", alert=True)
    return await admin_server_view(event, server_no)

  async with bot.conversation(chat, timeout=600) as conv:
    async def get_reply(txt):
      await conv.send_message(custom_emoji_text(txt + "\n\n<i>(Type /cancel to abort)</i>"))
      resp = await conv.get_response()
      if resp.text == "/cancel": raise ValueError("Cancelled")
      return resp

    try:
      if action_data.startswith(("srvapi_url|", "srvapi_key|")) and has_perm(uid, 'p_settings'):
        change_url = action_data.startswith("srvapi_url|")
        try:
          server_no = int(action_data.split("|")[1])
        except Exception:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Invalid server."))
        conf = SERVER_DEFS.get(server_no)
        if not conf:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Unknown server."))

        if change_url:
          cur_url, _ = get_server_api_config(server_no)
          raw = (await get_reply(
            f"{P_LINK} <b>{conf['name']} — Change API URL</b>\n\n"
            f"Current: <code>{html.escape(cur_url or 'Not set')}</code>\n"
            f"<i>Example: {conf.get('default_url', 'https://panel.example.com')}</i>\n\n"
            f"Send the new API URL:"
          )).text.strip()
          new_url = clean_html_url(raw)
          if not new_url.startswith(("http://", "https://")):
            return await conv.send_message(custom_emoji_text(
              f"{P_NO} <b>Invalid URL.</b> It must start with http:// or https://"))
          if conf.get("kind") == "tiger" and "handler_api" not in new_url:
            new_url = new_url.rstrip("/") + "/stubs/handler_api.php"
          set_setting(conf["url_key"], new_url)
          done = f"{P_YES} <b>{conf['name']} API URL updated.</b>"
        else:
          raw = (await get_reply(
            f"{P_KEY} <b>{conf['name']} — Change API Key</b>\n\n"
            f"Send the new API key:"
          )).text.strip()
          if not raw or " " in raw:
            return await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid API key.</b>"))
          set_setting(conf["key_key"], raw)
          done = f"{P_YES} <b>{conf['name']} API key updated.</b>"

        _reset_server_caches(server_no)
        await conv.send_message(custom_emoji_text(f"{done}\n{P_WAIT} Checking the connection..."))
        _ok, check_text = await _server_quick_test(server_no)
        await conv.send_message(custom_emoji_text(check_text))
        await admin_server_view(_AdminChatReply(chat, uid), server_no)

      elif action_data.startswith("srvapi_margin|") and has_perm(uid, 'p_settings'):
        try:
          server_no = int(action_data.split("|")[1])
        except Exception:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Invalid server."))
        conf = SERVER_DEFS.get(server_no)
        if not conf:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Unknown server."))
        raw = (await get_reply(
          f"{P_RATE} <b>Enter Profit Margin % for {conf['name']}</b>\n"
          f"<i>Example: 20 means API price + 20% profit. Enter 0 to sell at API price.</i>\n"
          f"Current: <b>{get_server_margin(server_no):g}%</b>"
        )).text.strip().replace("%", "")
        try:
          margin = float(raw)
          if margin < 0 or margin > 500:
            raise ValueError
        except Exception:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Enter a number between 0 and 500."))
        set_setting(conf["margin_key"], f"{margin:g}")
        if int(server_no) == 2:
          _reset_server_caches(2)
        await conv.send_message(custom_emoji_text(
          f"{P_YES} <b>Profit margin updated to {margin:g}%</b> for {conf['name']}."
        ))
        await admin_server_view(_AdminChatReply(chat, uid), server_no)

      elif action_data == "smm_api" and has_perm(uid, 'p_settings'):
        url_resp = (await get_reply(f"{P_GEAR} <b>Enter SMM API URL</b> (e.g., https://smmpanel.com/api/v2):")).text.strip()
        key_resp = (await get_reply(f"{P_KEY} <b>Enter SMM API Key:</b>")).text.strip()
        clean_u = clean_html_url(url_resp)
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smm_api_url', ?)", (clean_u,))
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smm_api_key', ?)", (key_resp,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} <b>SMM API credentials updated successfully!</b>\nClean URL: <code>{clean_u}</code>"))

      elif action_data == "smm_addcat" and has_perm(uid, 'p_manage_stock'):
        cname = (await get_reply(f"{P_FOLDER} <b>Enter Category Name</b> (e.g., Telegram):")).text.strip()
        cur.execute("INSERT INTO smm_categories (name) VALUES (?)", (cname,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} Category <b>{html.escape(cname)}</b> created successfully!"))

      elif action_data == "smm_delcat" and has_perm(uid, 'p_manage_stock'):
        rows = cur.execute("SELECT id, name FROM smm_categories").fetchall()
        if not rows: return await conv.send_message(custom_emoji_text("No categories found."))
        txt = "Reply with Category ID to delete:\n"
        for r in rows: txt += f"ID: {r[0]} - {r[1]}\n"
        cid = int((await get_reply(txt)).text.strip())
        cur.execute("DELETE FROM smm_categories WHERE id=?", (cid,))
        cur.execute("DELETE FROM smm_services WHERE category_id=?", (cid,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} Category and its services removed!"))

      elif action_data == "smm_bulksrv" and has_perm(uid, 'p_manage_stock'):
        cats = cur.execute("SELECT id, name FROM smm_categories").fetchall()
        if not cats: return await conv.send_message(custom_emoji_text("Please create a category first using 'Categories' menu."))
        
        cat_text = "Select Category ID for bulk services:\n"
        for c in cats: cat_text += f"ID: {c[0]} - {c[1]}\n"
        cid = int((await get_reply(cat_text)).text.strip())
        
        ids_resp = (await get_reply(f"{P_ID} <b>Enter Service IDs (separated by space, comma or newline):</b>\n<i>Example: 2222 6478 22461</i>")).text.strip()
        service_ids = re.findall(r'\d+', ids_resp)
        
        if not service_ids:
          return await conv.send_message(custom_emoji_text(f"{P_NO} No valid Service IDs found."))

        api_url, api_key = get_smm_api_config()
        if not api_url or not api_key:
          return await conv.send_message(custom_emoji_text(f"{P_NO} SMM API URL or Key not configured."))

        await conv.send_message(custom_emoji_text(f"{P_WAIT} <b>Fetching services from SMM API...</b>"))
        services_data = fetch_smm_services_from_api(api_url, api_key)
        
        api_services_dict = {}
        if services_data:
          if isinstance(services_data, dict):
            for k, v in services_data.items():
              if isinstance(v, dict):
                s_id = str(v.get('service', v.get('service_id', v.get('id', k))))
                api_services_dict[s_id] = v
              else:
                api_services_dict[str(k)] = {'name': str(v), 'rate': 0.0, 'min': 10, 'max': 10000}
          elif isinstance(services_data, list):
            for s in services_data:
              if isinstance(s, dict):
                s_id = str(s.get('service', s.get('service_id', s.get('id', ''))))
                if s_id: api_services_dict[s_id] = s

        markup_pct = float((await get_reply(f"{P_RATE} <b>Enter Profit Margin / Markup %</b> (e.g., enter <code>10</code> for 10% profit markup):")).text.strip() or 0)

        success_count = 0
        report_msg = f"{P_PKG} <b>Bulk Add Report ({markup_pct}% Markup):</b>\n\n"

        for sid_str in service_ids:
          sid_int = int(sid_str)
          target_srv = api_services_dict.get(str(sid_int))
          
          if target_srv and isinstance(target_srv, dict):
            sname = target_srv.get('name', f'Service {sid_int}')
            api_rate = float(target_srv.get('rate', 0.0))
            smin = int(target_srv.get('min', 10))
            smax = int(target_srv.get('max', 10000))
            sdesc = target_srv.get('description', '')
            
            srate = round(api_rate * (1 + markup_pct / 100.0), 2)
            
            cur.execute("INSERT OR REPLACE INTO smm_services (service_id, category_id, name, rate, min, max, description) VALUES (?,?,?,?,?,?,?)",
                  (sid_int, cid, sname, srate, smin, smax, sdesc))
            success_count += 1
            report_msg += f" ID {sid_int}: {html.escape(sname)} (₹{srate})\n"
          else:
            sname = f"Service {sid_int}"
            srate = 100.0
            smin, smax = 10, 10000
            sdesc = "Added via bulk"
            cur.execute("INSERT OR REPLACE INTO smm_services (service_id, category_id, name, rate, min, max, description) VALUES (?,?,?,?,?,?,?)",
                  (sid_int, cid, sname, srate, smin, smax, sdesc))
            success_count += 1
            report_msg += f" ID {sid_int}: Added with default values.\n"

        db.commit()
        report_msg += f"\n <b>Total Added:</b> {success_count} services successfully!"
        await conv.send_message(custom_emoji_text(report_msg))

      elif action_data == "smm_addsrv" and has_perm(uid, 'p_manage_stock'):
        cats = cur.execute("SELECT id, name FROM smm_categories").fetchall()
        if not cats: return await conv.send_message(custom_emoji_text("Please create a category first."))
        
        cat_text = "Select Category ID for the service:\n"
        for c in cats: cat_text += f"ID: {c[0]} - {c[1]}\n"
        cid = int((await get_reply(cat_text)).text.strip())
        
        sid_input = int((await get_reply(f"{P_ID} <b>Enter SMM Service ID:</b>")).text.strip())
        
        api_url, api_key = get_smm_api_config()
        target_srv = None
        
        if api_url and api_key:
          await conv.send_message(custom_emoji_text(f"{P_WAIT} <b>Fetching service details from SMM API...</b>"))
          services_data = fetch_smm_services_from_api(api_url, api_key)
          
          if services_data:
            if isinstance(services_data, dict):
              for k, v in services_data.items():
                if str(k) == str(sid_input) or (isinstance(v, dict) and str(v.get('service', v.get('service_id', v.get('id', '')))) == str(sid_input)):
                  target_srv = v if isinstance(v, dict) else {'name': str(v)}
                  target_srv['service'] = sid_input
                  break
            elif isinstance(services_data, list):
              for s in services_data:
                if isinstance(s, dict) and str(s.get('service', s.get('service_id', s.get('id', '')))) == str(sid_input):
                  target_srv = s
                  break

        if target_srv and isinstance(target_srv, dict):
          sname = target_srv.get('name', f'Service {sid_input}')
          api_rate = float(target_srv.get('rate', 0.0))
          smin = int(target_srv.get('min', 10))
          smax = int(target_srv.get('max', 10000))
          sdesc = target_srv.get('description', '')
          await conv.send_message(custom_emoji_text(f"{P_YES} <b>API details fetched successfully!</b>\n- Name: {html.escape(sname)}\n- Rate: ₹{api_rate}\n- Min: {smin} | Max: {smax}"))
        else:
          await conv.send_message(custom_emoji_text(f"{P_WARN} Auto-fetch failed due to API/Cloudflare. Please enter details manually:"))
          sname = (await get_reply("Enter Service Name:")).text.strip()
          api_rate = float((await get_reply("Enter API Rate per 1000 (₹):")).text.strip())
          smin = int((await get_reply("Enter Min Quantity:")).text.strip())
          smax = int((await get_reply("Enter Max Quantity:")).text.strip())
          sdesc = (await get_reply("Enter Description (or type 'none'):")).text.strip()

        markup_pct = float((await get_reply(f"{P_RATE} <b>API Rate:</b> ₹{api_rate}\n\n<b>Enter Profit Margin / Markup % (e.g., 10 for 10%):</b>")).text.strip() or 0)
        srate = round(api_rate * (1 + markup_pct / 100.0), 2)

        cur.execute("INSERT OR REPLACE INTO smm_services (service_id, category_id, name, rate, min, max, description) VALUES (?,?,?,?,?,?,?)",
              (sid_input, cid, sname, srate, smin, smax, sdesc))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} <b>Service Added Successfully!</b>\n\n- ID: <code>{sid_input}</code>\n- Name: {html.escape(sname)}\n- Rate/1k: ₹{srate} ({markup_pct}% markup)\n- Min: {smin} | Max: {smax}"))

      elif action_data == "update_welcome_photo" and has_perm(uid, 'p_settings'):
        resp = await get_reply(f"{P_EYE} <b>Send new welcome photo (image):</b>")
        if resp.photo:
          await bot.download_media(resp, "23593.jpg")
          await conv.send_message(custom_emoji_text(f"{P_YES} <b>Welcome photo updated successfully!</b>"))
        else:
          await conv.send_message(custom_emoji_text(f"{P_NO} This is not a valid photo. Try again."))

      elif action_data == "changelogs" and has_perm(uid, 'p_settings'):
        new_ch = (await get_reply(f"{P_GLOBE} <b>Enter new Logs Channel ID (e.g., -100xxxxxxxxxx):</b>\n\n<i>Add this bot as admin in the channel first (with \"Invite Users via Link\" permission).</i>")).text.strip()
        if not re.fullmatch(r"-?\d{5,20}", new_ch):
          return await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid channel ID.</b> It must look like <code>-1001234567890</code>."))
        ok, reason = await _is_bot_channel_admin(new_ch)
        if not ok:
          return await conv.send_message(custom_emoji_text(
            f"{P_NO} <b>Logs channel not changed.</b>\n\n{html.escape(reason)}\n\n"
            f"Make the bot an admin of that channel, then try again."))
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('log_channel_id', ?)", (new_ch,))
        db.commit()
        link = await refresh_selling_logs_link(new_ch)
        if not link:
          manual = (await get_reply(f"{P_WARN} <b>Could not auto-generate the link.</b>\nSend the channel invite link now (https://t.me/...), or type <b>skip</b> to keep the current Selling Logs link:")).text.strip()
          if manual.lower() != 'skip' and _has_valid_button_url(manual):
            link = _normalize_tg_url(manual, "")
            set_setting('selling_logs_link', link)
        await conv.send_message(custom_emoji_text(
          f"{P_YES} <b>Logs Channel updated successfully:</b> <code>{html.escape(new_ch)}</code>\n\n"
          f"{P_GLOBE} <b>Selling Logs button link:</b> {html.escape(link or get_selling_logs_link())}"))

      elif action_data == "add_fchan":
        title = (await get_reply("Enter Channel Title/Name (e.g., Updates Channel):")).text.strip()
        ch_id = (await get_reply("Enter Channel Chat ID (e.g., -100xxxxxxxxxx):")).text.strip()

        # Never save a force channel until the bot itself is confirmed as admin/creator.
        bot_admin_ok, admin_reason = await _is_bot_channel_admin(ch_id)
        if not bot_admin_ok:
          await conv.send_message(custom_emoji_text(
            f"{P_NO} <b>Channel verification failed.</b>\n\n"
            f"<b>Reason:</b> {html.escape(admin_reason)}\n\n"
            "Add the bot to that channel as an <b>Administrator</b>, then try again."
          ))
          return

        # No manual invite URL is required. Telegram creates the invite link for
        # this channel and that generated link is stored for the Join button.
        await conv.send_message(custom_emoji_text(
          "Bot admin verified successfully.\n\n"
          "Creating the channel invite link automatically..."
        ))
        invite_ok, inv, invite_reason = await _create_force_channel_invite(ch_id)
        if not invite_ok:
          await conv.send_message(custom_emoji_text(
            f"{P_NO} <b>Invite link creation failed.</b>\n\n"
            f"<b>Reason:</b> {html.escape(invite_reason)}\n\n"
            "Make sure the bot has permission to <b>Invite Users via Link</b> in this channel and try again."
          ))
          return

        # Replace an existing entry for the same channel instead of creating duplicates.
        cur.execute("DELETE FROM force_channels WHERE channel_id=?", (ch_id,))
        cur.execute(
          "INSERT INTO force_channels (channel_id, invite_url, title) VALUES (?,?,?)",
          (ch_id, inv, title)
        )
        db.commit()
        await conv.send_message(custom_emoji_text(
          f"{P_YES} <b>Force channel added successfully!</b>\n\n"
          f"Title: {html.escape(title)}\n"
          f"Chat ID: <code>{html.escape(ch_id)}</code>\n"
          f"Join link created automatically."
        ))

      elif action_data.startswith("fchlink|"):
        fid = int(action_data.split("|")[1])
        r = cur.execute("SELECT channel_id, title FROM force_channels WHERE id=?", (fid,)).fetchone()
        if not r:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Channel not found."))
        raw_link = (await get_reply(
          f"{P_LINK} <b>Send the new join link for {html.escape(str(r[1] or r[0]))}</b>\n"
          f"<i>Public (https://t.me/username) or private (https://t.me/+xxxx) link. "
          f"Request-to-join links are supported.</i>")).text.strip()
        new_link = await _validate_force_invite_url(clean_html_url(raw_link))
        if not new_link:
          return await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid link.</b> Link not changed."))
        cur.execute("UPDATE force_channels SET invite_url=? WHERE id=?", (new_link, fid))
        db.commit()
        await conv.send_message(custom_emoji_text(
          f"{P_YES} <b>Link updated.</b>\n\n{P_LINK} {html.escape(new_link)}\n\n"
          f"Force join now accepts both joined members and users with a pending join request."))

      elif action_data == "del_fchan":
        rows = cur.execute("SELECT id, title, channel_id FROM force_channels").fetchall()
        if not rows: return await conv.send_message(custom_emoji_text("No channels to delete."))
        txt = "Reply with ID to delete:\n"
        for r in rows: txt += f"ID: {r[0]} - {r[1]} ({r[2]})\n"
        del_id = int((await get_reply(txt)).text.strip())
        cur.execute("DELETE FROM force_channels WHERE id=?", (del_id,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} Force channel removed!"))

      elif action_data == "set_upi":
        new_upi = (await get_reply("Enter new UPI ID (e.g., yourname@fampay):")).text.strip()
        new_name = (await get_reply("Enter Payee Name (e.g., Aaditya Tg Store):")).text.strip()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('fampay_upi', ?)", (new_upi,))
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('fampay_name', ?)", (new_name,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} FamPay UPI settings updated!"))

      elif action_data == "set_imap":
        srv = (await get_reply("Enter IMAP Server (e.g., imap.gmail.com):")).text.strip()
        mail_id = (await get_reply("Enter Gmail Email Address (e.g., aroy327154@gmail.com):")).text.strip()
        pwd = (await get_reply("Enter Gmail App Password (e.g., yasc qrso aunp dnbc):")).text.strip()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('imap_server', ?)", (srv,))
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('imap_email', ?)", (mail_id,))
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('imap_password', ?)", (pwd,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} IMAP credentials saved successfully for automatic UTR verification!"))

      elif action_data == "ap_add_country" and has_perm(uid, 'p_manage_stock'):
        code = (await get_reply(f"{P_PHONE} <b>Enter Country Calling Code (without +):</b>\n<i>Example: 91</i>")).text.replace("+", "").strip()
        name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text.strip())
        
        cur.execute("INSERT OR REPLACE INTO custom_countries (code, name) VALUES (?,?)", (code, name))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} <b>Custom Country Added Successfully!</b>\n{name} (+{code})\n\n<i>It will now automatically be recognized when adding stock!</i>"))

      elif action_data == "userinfo" and has_perm(uid, 'p_stats'):
        t_uid = int((await get_reply(f"{P_ACC} <b>Enter User ID:</b>")).text)
        u_row = cur.execute("SELECT balance, total_deposited, joined_date, banned, discount FROM users WHERE user_id=?", (t_uid,)).fetchone()
        if not u_row: return await conv.send_message(custom_emoji_text(f"{P_NO} User not found."))
        
        o_row = cur.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE user_id=?", (t_uid,)).fetchone()
        
        bal, dep, joined, is_banned, disc = u_row
        o_count = o_row[0] if o_row else 0
        o_spent = o_row[1] if o_row and o_row[1] else 0
        
        msg = (f"{P_ACC} <b>USER INFO:</b> <code>{t_uid}</code>\n\n"
            f"{P_MONEY} Balance: {P_INR}{bal}\n"
            f"{P_CARD} Total Deposited: {P_INR}{dep}\n"
            f"{P_CART} Total Orders: {o_count}\n"
            f"{P_USDT} Total Spent: {P_INR}{o_spent}\n"
            f"{P_GIFT} Discount: {disc}%\n"
            f"{P_CAL} Joined: {joined}\n"
            f"{P_OFF} Banned: {'Yes' if is_banned else 'No'}")
        await conv.send_message(custom_emoji_text(msg))

      elif action_data == "addadmin" and uid == ADMIN_ID:
        new_ad = int((await get_reply(f"{P_ACC} <b>Enter User ID for new Admin:</b>")).text)
        cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_ad,))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} Admin added!"))
        class FakeEvent: 
          async def edit(self, text, buttons): await bot.send_message(chat, text, buttons=buttons)
          async def answer(self, txt, alert): pass
        await edit_admin_menu(FakeEvent(), new_ad)
        
      elif action_data == "editadminreq" and uid == ADMIN_ID:
        t_id = int((await get_reply(f"{P_ACC} <b>Enter User ID to edit:</b>")).text)
        class FakeEvent: 
          async def edit(self, text, buttons): await bot.send_message(chat, text, buttons=buttons)
          async def answer(self, txt, alert): pass
        await edit_admin_menu(FakeEvent(), t_id)

      elif action_data.startswith("msedit|") and has_perm(uid, 'p_manage_stock'):
        parts = action_data.split("|")
        action, c_name = parts[1], parts[2]
        
        if action == "name":
          new_name = html.escape((await get_reply(f"{P_DOC} <b>Enter NEW Name for {html.escape(c_name)}:</b>")).text)
          cur.execute("UPDATE stock SET country_name=? WHERE country_name=?", (new_name, c_name))
          cur.execute("UPDATE auto_prices SET country=? WHERE country=?", (new_name, c_name))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} Country '{html.escape(c_name)}' successfully renamed to '{new_name}'!"))
          
        elif action == "cprice":
          new_p = int((await get_reply(f"{P_MONEY} <b>Enter NEW Common Price for all {html.escape(c_name)} accounts:</b>")).text)
          cur.execute("UPDATE stock SET price=? WHERE country_name=?", (new_p, c_name))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} All existing '{html.escape(c_name)}' accounts updated to {P_INR}{new_p}!"))
          
        elif action == "yprice":
          year = parts[3]
          new_p = int((await get_reply(f"{P_MONEY} <b>Enter NEW Price for {html.escape(c_name)} ({year}):</b>")).text)
          cur.execute("UPDATE stock SET price=? WHERE country_name=? AND account_year=?", (new_p, c_name, year))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} All existing '{html.escape(c_name)}' ({year}) accounts updated to {P_INR}{new_p}!"))
          
      elif action_data.startswith("apset|") and has_perm(uid, 'p_manage_stock'):
        parts = action_data.split("|")
        c_name, year = parts[1], parts[2]
        new_p = int((await get_reply(f"{P_ASST} <b>Enter Auto-Price for {html.escape(c_name)} ({year}):</b>\n<i>(Enter 0 to remove this auto-price)</i>")).text)
        if new_p == 0:
          cur.execute("DELETE FROM auto_prices WHERE country=? AND year=?", (c_name, year))
          await conv.send_message(custom_emoji_text(f"{P_YES} Auto-Price for {html.escape(c_name)} ({year}) removed!"))
        else:
          cur.execute("INSERT OR REPLACE INTO auto_prices (country, year, price) VALUES (?,?,?)", (c_name, year, new_p))
          await conv.send_message(custom_emoji_text(f"{P_YES} Auto-Price for {html.escape(c_name)} ({year}) set to {P_INR}{new_p}! Incoming accounts will use this price automatically."))
        db.commit()

      elif action_data == "addzip" and has_perm(uid, 'p_add_stock'):
        resp = await get_reply(f"{P_PKG} <b>Send the ZIP file containing <code>.session</code> files:</b>")
        if not resp.file or not resp.file.name.endswith('.zip'): return await conv.send_message(custom_emoji_text(f"{P_NO} Invalid file."))
        
        await conv.send_message(custom_emoji_text(f"{P_WAIT} <b>Extracting & Scanning Accounts...</b>"))
        zip_path = await bot.download_media(resp, "temp_sessions.zip")
        extracted_dir = f"temp_extracted_{int(time.time())}"
        os.makedirs(extracted_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(extracted_dir)

        groups = {}
        for file in os.listdir(extracted_dir):
          if not file.endswith(".session"): continue
          sess_path = os.path.join(extracted_dir, file)
          clean_path = sess_path[:-8]
          try:
            client = TelegramClient(clean_path, API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized(): await client.disconnect(); continue
            me = await client.get_me()
            phone = getattr(me, 'phone', None)
            if not phone: await client.disconnect(); continue
            
            c_name = get_country_info(phone)
            pwd = await client(GetPasswordRequest())
            has_2fa = pwd.has_password
            year = await detect_account_year(client)
            await client.disconnect()

            key = (c_name, year, has_2fa)
            if key not in groups: groups[key] = []
            groups[key].append({"phone": phone, "path": clean_path})
          except Exception as e: logger.error(f"Scan error: {e}")

        for key in list(groups.keys()):
          if key[0] == "Unknown":
            sample_phone = groups[key][0]["phone"]
            await conv.send_message(custom_emoji_text(f"{P_WARN} <b>Country not recognized for +{sample_phone}!</b>"))
            new_name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text)
            new_key = (new_name, key[1], key[2])
            groups[new_key] = groups.pop(key)

        success = 0
        for (c_name, year, has_2fa), accs in groups.items():
          twofa_pass = "None"
          if has_2fa: twofa_pass = html.escape((await get_reply(f"{P_2FA} <b>Enter 2FA Password for {len(accs)}x {html.escape(c_name)} accounts:</b>")).text)

          auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year=?", (c_name, str(year))).fetchone()
          if not auto_row: auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year='Common'", (c_name,)).fetchone()

          if auto_row:
            price = auto_row[0]
            await conv.send_message(custom_emoji_text(f"{P_FIRE} <b>Auto-Price Applied:</b> {len(accs)}x {html.escape(c_name)} ({year}) at {P_INR}{price}."))
          else:
            existing_price = cur.execute("SELECT price FROM stock WHERE country_name=? LIMIT 1", (c_name,)).fetchone()
            if existing_price:
              price = existing_price[0]
              await conv.send_message(custom_emoji_text(f"{P_FIRE} <b>Auto-Added:</b> {len(accs)}x {html.escape(c_name)} at {P_INR}{price} (Copied from DB)."))
            else:
              price = int((await get_reply(f"{P_DOC} Found {len(accs)}x {html.escape(c_name)} ({year}).\n{P_MONEY} Enter Price (₹):")).text)

          for acc in accs:
            perm_base = f"sessions/{acc['phone']}"
            for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
              if os.path.exists(acc['path'] + ext): shutil.move(acc['path'] + ext, perm_base + ext)
            cur.execute("INSERT OR REPLACE INTO stock (phone, session_file, country_name, account_year, category, price, available, twofa) VALUES (?,?,?,?,?,?,?,?)", 
                  (acc['phone'], perm_base + ".session", c_name, year, 'Good', price, 1, twofa_pass))
            success += 1
        db.commit()
        os.remove(zip_path); shutil.rmtree(extracted_dir)
        await conv.send_message(custom_emoji_text(f"{P_YES} {P_PARTY} <b>Bulk Interactive Upload Complete!</b>\n{P_ON} Added: {success}"))

      elif action_data == "addstock" and has_perm(uid, 'p_add_stock'):
        phone = (await get_reply(f"{P_PHONE} Enter Phone (+919999...):")).text.replace(" ", "").replace("+", "")
        sp = f"sessions/{phone}"
        client = TelegramClient(sp, API_ID, API_HASH)
        await client.connect()
        sreq = await client.send_code_request(phone)
        
        twofa_pass = "None"
        try: 
          await client.sign_in(phone, (await get_reply(f"{P_OTP} OTP:")).text, phone_code_hash=sreq.phone_code_hash)
        except SessionPasswordNeededError: 
          twofa_pass = html.escape((await get_reply(f"{P_2FA} 2FA Pass required. Enter it now:")).text)
          await client.sign_in(password=twofa_pass)
        
        c_name = get_country_info(phone)
        
        if c_name == "Unknown":
          await conv.send_message(custom_emoji_text(f"{P_WARN} <b>Country not recognized for +{phone}!</b>"))
          c_name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text)
        
        auto_year = await detect_account_year(client)
        await client.disconnect()
        
        year = int((await get_reply(f"{P_CAL} Detected Year: <b>{auto_year}</b>\nReply with Year to confirm or change:")).text)
        auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year=?", (c_name, str(year))).fetchone()
        if not auto_row: auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year='Common'", (c_name,)).fetchone()

        if auto_row:
          price = auto_row[0]
          await conv.send_message(custom_emoji_text(f"{P_FIRE} <b>Auto-Price Applied:</b> {P_INR}{price} for {html.escape(c_name)} ({year})"))
        else:
          existing_price = cur.execute("SELECT price FROM stock WHERE country_name=? LIMIT 1", (c_name,)).fetchone()
          if existing_price:
            price = existing_price[0]
            await conv.send_message(custom_emoji_text(f"{P_FIRE} <b>Auto-detected Price:</b> {P_INR}{price} for {html.escape(c_name)}"))
          else: price = int((await get_reply(f"{P_MONEY} Price (₹):")).text)
        
        cur.execute("INSERT OR REPLACE INTO stock (phone, session_file, country_name, account_year, category, price, available, twofa) VALUES (?,?,?,?,?,?,?,?)", 
              (phone, sp + ".session", c_name, year, 'Good', price, 1, twofa_pass))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} <b>Added!</b> {html.escape(c_name)}"))

      elif action_data == "supporturl" and has_perm(uid, 'p_settings'):
        url_inp = (await get_reply(f"{P_DOC} <b>Enter new Support Username or URL:</b>\n<i>(Examples: <code>https://t.me/m/P7am0xdlZmE1</code>)</i>")).text.strip()
        normalized = _normalize_tg_url(url_inp, "")
        if not normalized:
          await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid Telegram support link.</b>\nPlease enter a valid <code>https://t.me/username</code>, <code>https://t.me/+invite</code>, or <code>@username</code>."))
        else:
          cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('support_url', ?)", (normalized,))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} <b>Support Link updated successfully!</b>\nTarget: <code>{html.escape(normalized)}</code>"))

      elif action_data == "supportchan" and has_perm(uid, 'p_settings'):
        chan_inp = (await get_reply(f"{P_GLOBE} <b>Enter new Support/Updates Channel Link or Username:</b>\n<i>(Examples: <code>https://t.me/...</code> or <code>@MyChannel</code>)</i>")).text.strip()
        normalized = _normalize_tg_url(chan_inp, "")
        if not normalized:
          await conv.send_message(custom_emoji_text(f"{P_NO} <b>Invalid Telegram channel link.</b>\nPlease enter a valid <code>https://t.me/channel</code>, <code>https://t.me/+invite</code>, or <code>@channel</code>."))
        else:
          cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('support_channel_url', ?)", (normalized,))
          db.commit()
          await conv.send_message(custom_emoji_text(f"{P_YES} <b>Support/Updates Channel Link updated successfully!</b>\nTarget: <code>{html.escape(normalized)}</code>"))

      elif action_data == "bcast" and has_perm(uid, 'p_stats'):
        txt = (await get_reply(f"{P_DOC} <b>Message (Supports HTML & tg-emoji tags):</b>")).text
        btn_name = (await get_reply("Button Name (or 'skip'):")).text
        url = (await get_reply("URL:")).text if btn_name.lower() != 'skip' else None
        btn = _safe_url_button(btn_name, url) if url else None
        btns = [[btn]] if btn is not None else None
        users = cur.execute("SELECT user_id FROM users").fetchall()
        s, f = 0, 0
        await conv.send_message(custom_emoji_text(f"{P_TG} Broadcasting..."))
        for (u_id,) in users:
          try: 
            await bot.send_message(int(u_id), txt, buttons=btns, parse_mode='html')
            s += 1
          except: f += 1
          await asyncio.sleep(0.1) 
        await conv.send_message(custom_emoji_text(f"{P_YES} Done! Sent: {s} | Failed: {f}"))

      elif action_data == "bal" and has_perm(uid, 'p_bal'):
        t_uid = int((await get_reply(f"{P_ACC} <b>User ID:</b>")).text)
        amt = int((await get_reply(f"{P_MONEY} <b>Amount (Negative to deduct):</b>")).text)
        update_balance(t_uid, amt)
        await conv.send_message(custom_emoji_text(f"{P_YES} Added {P_INR}{amt} to {t_uid}."))
        
      elif action_data == "discount" and has_perm(uid, 'p_settings'):
        t_uid = int((await get_reply(f"{P_ACC} <b>User ID:</b>")).text)
        pct = int((await get_reply(f"{P_GIFT} <b>Discount % (0 to remove):</b>")).text)
        cur.execute("UPDATE users SET discount=? WHERE user_id=?", (pct, t_uid))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} User {t_uid} has {pct}% discount."))

      elif action_data == "usdtrate" and has_perm(uid, 'p_settings'):
        r = float((await get_reply(f"{P_USDT} <b>New USDT Rate (INR):</b>")).text)
        cur.execute("UPDATE settings SET value=? WHERE key='usdt_rate'", (str(r),))
        db.commit()
        await conv.send_message(custom_emoji_text(f"{P_YES} Rate set to {r}."))

      elif action_data == "restoreusr" and has_perm(uid, 'p_settings'):
        if uid != ADMIN_ID:
          return await conv.send_message(custom_emoji_text(f"{P_NO} Only the owner can restore a backup."))
        resp = await get_reply(
          f"{P_DOC} <b>Send the full backup <code>.zip</code> file.</b>\n"
          f"{P_WARN} Script, database and sessions will be replaced and the bot will restart.")
        if not resp.file or not (resp.file.name or "").lower().endswith(".zip"):
          return await conv.send_message(custom_emoji_text(f"{P_NO} Invalid file. Send the backup .zip."))
        tmp_zip = f"temp_restore_{int(time.time())}.zip"
        try:
          await bot.download_media(resp, tmp_zip)
          await conv.send_message(custom_emoji_text(f"{P_WAIT} Restoring everything..."))
          n_files = restore_full_backup(tmp_zip)
        except ValueError as ex:
          return await conv.send_message(custom_emoji_text(f"{P_NO} {html.escape(str(ex))}"))
        finally:
          if os.path.exists(tmp_zip):
            try: os.remove(tmp_zip)
            except Exception: pass
        await conv.send_message(custom_emoji_text(
          f"{P_YES} <b>Restore complete.</b>\n{P_FOLDER} Database + {n_files} files + script restored.\n"
          f"{P_CW} Restarting bot..."))
        asyncio.get_event_loop().call_later(2, _restart_bot)

      elif action_data == "delacc" and has_perm(uid, 'p_manage_stock'):
        raw = (await get_reply(f"{P_PHONE} <b>Send the account phone number to delete</b> (e.g. 919876543210):")).text
        digits = re.sub(r"\D", "", raw or "")
        if not digits: return await conv.send_message(custom_emoji_text(f"{P_NO} Invalid number."))
        row = cur.execute("SELECT phone, session_file, country_name, account_year, price, available FROM stock "
                          "WHERE REPLACE(REPLACE(phone,'+',''),' ','')=?", (digits,)).fetchone()
        if not row: return await conv.send_message(custom_emoji_text(f"{P_NO} Account not found in stock."))
        phone, sess, c_name, yr, pr, avail = row
        if phone in active_orders:
          return await conv.send_message(custom_emoji_text(f"{P_WARN} This account is in an active order. Try later."))
        ok = (await get_reply(
          f"{P_WARN} <b>Delete this account?</b>\n{P_PHONE} <code>{html.escape(str(phone))}</code>\n"
          f"{P_GLOBE} {html.escape(str(c_name))} | {yr} | ₹{pr}\n\nReply <b>YES</b> to confirm.")).text.strip().upper()
        if ok != "YES": return await conv.send_message(custom_emoji_text(f"{P_NO} Cancelled."))
        cur.execute("DELETE FROM stock WHERE phone=?", (phone,))
        db.commit()
        if sess: delete_session_files(sess)
        await conv.send_message(custom_emoji_text(f"{P_YES} Account <code>{html.escape(str(phone))}</code> deleted from stock."))

      elif action_data == "ban" and has_perm(uid, 'p_bal'):
        t_uid = int((await get_reply(f"{P_ACC} <b>User ID:</b>")).text)
        is_ban = cur.execute("SELECT banned FROM users WHERE user_id=?", (t_uid,)).fetchone()
        if not is_ban: return await conv.send_message(custom_emoji_text(f"{P_NO} User not found."))
        ns = 0 if is_ban[0] == 1 else 1
        cur.execute("UPDATE users SET banned=? WHERE user_id=?", (ns, t_uid))
        db.commit()
        await conv.send_message(custom_emoji_text(f"User {t_uid} status updated: {'Banned' if ns == 1 else 'Unbanned'}."))

    except ValueError: await conv.send_message(custom_emoji_text(f"{P_NO} Cancelled."))
    except Exception as e: await conv.send_message(custom_emoji_text(f"{P_NO} Error: {e}"))

@bot.on(events.NewMessage(pattern=r"(?i)^/refill(?:\s+(\d+))?"))
async def handle_refill_command(e):
  try:
    uid = e.sender_id
    if not uid: return
    ensure_user(uid)
    if is_user_banned(uid): return

    match = e.pattern_match.group(1)
    if not match:
      refill_state[uid] = {'step': 'wait_order_id'}
      await e.respond(custom_emoji_text(f"{P_ASST} <b>Please enter your Bot Order ID for refill:</b>\n<i>(Type /cancel to abort)</i>"))
    else:
      bot_order_id = int(match)
      order_row = cur.execute("SELECT user_id, smm_order_id FROM smm_orders WHERE bot_order_id=?", (bot_order_id,)).fetchone()
      if not order_row:
        return await e.respond(custom_emoji_text(f"{P_NO} Order ID <code>{bot_order_id}</code> not found in database."))
      owner_uid, smm_order_id = order_row
      if owner_uid != uid and not is_admin(uid):
        return await e.respond(custom_emoji_text(f"{P_NO} This order does not belong to you."))
      if not smm_order_id or smm_order_id == 'SUCCESS':
        return await e.respond(custom_emoji_text(f"{P_NO} Valid SMM Panel Order ID not available for this order."))
      
      refill_state[uid] = {'step': 'wait_screenshot', 'bot_order_id': bot_order_id, 'smm_order_id': smm_order_id}
      await e.respond(
        custom_emoji_text(f"{P_DOC} <b>Order ID Verified: #{bot_order_id}</b>\n\n"
        f"Please send a <b>screenshot</b> showing the invite link joined statistics (showing member list and joined count, exactly like the reference example).\n\n"
        f"<i>Send the screenshot now:</i>")
      )
  except Exception as ex:
    logger.error(f"Refill error: {ex}")

@bot.on(events.NewMessage(pattern=r"(?i)^/s1raw(?:@\w+)?(?:\s+([A-Za-z]{2}))?\s*$"))
async def handle_s1_raw(e):
  """Admin only: show the raw Server 1 API account JSON (to verify field names)."""
  if not e.sender_id or not is_admin(e.sender_id):
    return
  code = (e.pattern_match.group(1) or "IN").upper()
  items = await asyncio.to_thread(fetch_s1_items, code, True, None, 20, None, None)
  if isinstance(items, dict) or not items:
    return await e.respond(f"No accounts / error for {code}: {items if isinstance(items, dict) else 'empty'}")
  raw = json.dumps(items[0].get("raw"), indent=1, ensure_ascii=False)[:3500]
  await e.respond(f"<b>Raw API account ({code})</b>\n<pre>{html.escape(raw)}</pre>", parse_mode="html")


@bot.on(events.NewMessage(pattern=r"(?i)^/admin(?:@\w+)?\s*$"))
async def handle_admin_command(e):
  """Open the admin panel only through /admin."""
  uid = e.sender_id
  if not uid:
    return
  if not is_admin(uid):
    await e.respond("You are not authorized to use the admin panel.")
    return
  for state in (session_buy_state, deposit_input, smm_order_state, refill_state, waiting_proof, admin_dep_state):
    state.pop(uid, None)
  try:
    await admin_panel_handler(e)
  except Exception:
    logger.exception("Admin panel error for %s", uid)
    await e.respond("Admin panel could not be opened. Please check the bot logs.")

@bot.on(events.NewMessage(pattern=r"(?i)^/start"))
async def handle_start(e):
  try:
    uid = e.sender_id
    if not uid: return
    
    existing_user = cur.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone()
    is_new_user = existing_user is None
    ensure_user(uid)
    if is_new_user:
      await notify_new_user(uid, e)
    if is_user_banned(uid): return

    if not is_bot_online() and not is_admin(uid):
      return await e.respond(custom_emoji_text(bot_block_text()))
    
    session_buy_state.pop(uid, None)
    deposit_input.pop(uid, None)
    waiting_proof.pop(uid, None)
    smm_order_state.pop(uid, None)
    refill_state.pop(uid, None)
    redeem_state.pop(uid, None)
    S1_SEARCH_STATE.pop(uid, None)

    is_joined = await check_channel_joined(uid)
    if not is_joined:
      rows = cur.execute("SELECT title, invite_url FROM force_channels").fetchall()
      btns = []
      for title, invite_url in rows:
        b = _safe_url_button(title or "Join Channel", invite_url)
        if b is not None:
          btns.append([b])
      btns.append([Button.inline("Verify Joined", "verify_join")])
      msg = f"{P_WARN} <b>You must join our channels first!</b>"
      return await e.respond(custom_emoji_text(msg), buttons=btns)

    await send_main_menu(e, uid)
  except Exception as ex: 
    logger.error(f"Start Error: {ex}", exc_info=True)

@bot.on(events.NewMessage(pattern=r"(?i)^/cancel(?:@\w+)?\s*$"))
async def handle_cancel(e):
  """Abort any pending multi-step flow (deposit UTR, screenshot, buy, etc.)."""
  uid = e.sender_id
  if not uid:
    return
  had_state = False
  for _state in (deposit_input, waiting_proof, session_buy_state,
                 smm_order_state, refill_state, redeem_state, S1_SEARCH_STATE):
    if uid in _state:
      had_state = True
      _state.pop(uid, None)
  if had_state:
    await e.respond(custom_emoji_text(f"{P_NO} <b>Cancelled.</b> Nothing was charged."))
  else:
    await e.respond(custom_emoji_text(f"{P_ASST} Nothing to cancel."))


@bot.on(events.NewMessage())
async def handle_all_messages(e):
  try:
    uid = e.sender_id
    if not uid: return
    if getattr(e, 'text', None) and e.text and e.text.startswith('/'): return
    if not is_bot_online() and not is_admin(uid):
      return await e.respond(custom_emoji_text(bot_block_text()))
    
    ensure_user(uid)
    if is_user_banned(uid): return

    if uid in redeem_state:
      state=redeem_state.get(uid,{})
      text=(e.text or '').strip()
      if text.lower() == '/cancel':
        redeem_state.pop(uid,None); return await e.respond("Redeem cancelled.")
      if state.get('step') == 'wait_code' and text:
        redeem_state.pop(uid,None)
        code=text.upper()
        row=cur.execute("SELECT amount,max_users,used_count,active FROM redeem_codes WHERE code=?",(code,)).fetchone()
        if not row: return await e.respond("Invalid redeem code.")
        amount,mx,used,active=row
        if not active or used>=mx: return await e.respond("This code is no longer available.")
        if cur.execute("SELECT 1 FROM redeem_claims WHERE code=? AND user_id=?",(code,uid)).fetchone(): return await e.respond("You have already redeemed this code.")
        async with get_user_lock(uid):
          cur.execute("INSERT INTO redeem_claims(code,user_id) VALUES(?,?)",(code,uid))
          cur.execute("UPDATE redeem_codes SET used_count=used_count+1 WHERE code=? AND active=1 AND used_count<?",(code,mx))
          if cur.rowcount != 1:
            cur.execute("DELETE FROM redeem_claims WHERE code=? AND user_id=?",(code,uid)); db.commit(); return await e.respond("This code just reached its limit.")
          update_balance(uid,amount); db.commit()
        return await e.respond(custom_emoji_text(f"{P_YES} <b>Redeem Successful!</b>\nAmount Added: ₹{amount}"))

    if uid in refill_state:
      state = refill_state[uid]
      step = state['step']
      text = e.text.strip() if e.text else ""

      if text.lower() == '/cancel':
        refill_state.pop(uid, None)
        return await e.respond(custom_emoji_text(f"{P_NO} Refill process cancelled."))

      if step == 'wait_order_id':
        if not text.isdigit():
          return await e.respond(custom_emoji_text(f"{P_NO} Please enter a valid numeric Bot Order ID."))
        bot_order_id = int(text)
        order_row = cur.execute("SELECT user_id, smm_order_id FROM smm_orders WHERE bot_order_id=?", (bot_order_id,)).fetchone()
        if not order_row:
          return await e.respond(custom_emoji_text(f"{P_NO} Order ID <code>{bot_order_id}</code> not found in database."))
        owner_uid, smm_order_id = order_row
        if owner_uid != uid and not is_admin(uid):
          return await e.respond(custom_emoji_text(f"{P_NO} This order does not belong to you."))
        if not smm_order_id or smm_order_id == 'SUCCESS':
          return await e.respond(custom_emoji_text(f"{P_NO} Valid SMM Panel Order ID not available for this order."))
        
        state['bot_order_id'] = bot_order_id
        state['smm_order_id'] = smm_order_id
        state['step'] = 'wait_screenshot'
        refill_state[uid] = state
        
        await e.respond(
          custom_emoji_text(f"{P_DOC} <b>Order ID Verified: #{bot_order_id}</b>\n\n"
          f"Please send a <b>screenshot</b> showing the invite link joined statistics (showing member list and joined count, exactly like the reference example).\n\n"
          f"<i>Send the screenshot now:</i>")
        )
        return
      elif step == 'wait_screenshot':
        if not e.photo:
          return await e.respond(custom_emoji_text(f"{P_NO} Please send a valid image screenshot."))
        
        bot_order_id = state['bot_order_id']
        smm_order_id = state['smm_order_id']
        refill_state.pop(uid, None)
        
        await e.respond(custom_emoji_text(f"{P_WAIT} <b>Processing refill request and sending to SMM panel... Please wait.</b>"))
        
        api_url, api_key = get_smm_api_config()
        refill_res = None
        if api_url and api_key:
          refill_res = refill_smm_order_api(api_url, api_key, smm_order_id)
        
        # Forward refill request screenshot directly to ADMIN_ID (Admin DM)
        try:
          log_msg = (
            f"{P_BELL} <b>NEW REFILL REQUEST WITH SCREENSHOT</b>\n\n"
            f"{P_ACC} User ID: <code>{uid}</code>\n"
            f"{P_ID} Bot Order ID: <code>{bot_order_id}</code>\n"
            f"{P_GEAR} Panel Order ID: <code>{smm_order_id}</code>\n"
            f"{P_TIME} Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
          )
          await bot.send_file(ADMIN_ID, e.photo, caption=custom_emoji_text(log_msg))
        except Exception as ex:
          logger.error(f"Failed to forward refill screenshot to admin DM: {ex}")
        
        if refill_res and isinstance(refill_res, dict) and ('refill' in refill_res or refill_res.get('status') == 'success' or 'refill_id' in refill_res):
          refill_id = refill_res.get('refill', refill_res.get('refill_id', 'SUCCESS'))
          await e.respond(custom_emoji_text(f"{P_YES} <b>Refill Request Submitted Successfully!</b> {P_PARTY}\n\n- Bot Order ID: <code>{bot_order_id}</code>\n- Panel Refill ID: <code>{refill_id}</code>\n\n<i>Your screenshot has been verified and submitted.</i>"))
        else:
          err = refill_res.get('error', 'Unknown refill error') if isinstance(refill_res, dict) else 'Refill API connection failed'
          await e.respond(custom_emoji_text(f"{P_YES} <b>Refill Screenshot Received & Forwarded to Admin!</b>\n\nNote: Panel response: {html.escape(str(err))}. Your request has been logged for review."))
        
        await send_main_menu(e, uid)
        return

    if uid in smm_order_state:
      state = smm_order_state[uid]
      step = state['step']
      text = e.text.strip()

      if step == 'wait_link':
        # e.text is HTML-formatted (bot.parse_mode='html'), which turned a pasted
        # URL into '<a href="...">...</a>'. Use the plain text and extract the URL.
        state['link'] = clean_html_url((e.raw_text or text).strip())
        state['step'] = 'wait_qty'
        smm_order_state[uid] = state
        await e.respond(custom_emoji_text(f"{P_QTY} <b>Enter Quantity:</b>\n(Min: {state['min']} | Max: {state['max']}):"), buttons=[[Button.inline("Cancel", "smm_cancel")]])
        return
      elif step == 'wait_qty':
        try:
          qty = int(re.sub(r'[^\d]', '', text))
          if qty < state['min'] or qty > state['max']:
            return await e.respond(custom_emoji_text(f"{P_NO} Quantity must be between {state['min']} and {state['max']}."))
          
          total_price = (qty / 1000.0) * state['rate']
          state['qty'] = qty
          state['total_price'] = total_price
          
          bal_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
          bal = bal_row[0] if bal_row else 0
          if bal < total_price:
            smm_order_state.pop(uid, None)
            err_msg = (
              f"{P_NO} <b>Insufficient Funds!</b>\n\n"
              f"<b>Order Cost:</b> ₹{total_price:.4f}\n"
              f"<b>Your Balance:</b> ₹{bal:.4f}\n\n"
              f"Please use /addfunds to top up your account."
            )
            return await e.respond(custom_emoji_text(err_msg))

          api_url, api_key = get_smm_api_config()
          if not api_url or not api_key:
            smm_order_state.pop(uid, None)
            return await e.respond(custom_emoji_text(f"{P_NO} SMM API is not configured by admin."))

          await e.respond(custom_emoji_text(f"{P_WAIT} <b>Placing order to SMM Panel... Please wait.</b>"))
          api_res = place_smm_order_api(api_url, api_key, state['service_id'], state['link'], qty)
          
          if api_res and isinstance(api_res, dict) and ('order' in api_res or api_res.get('status') == 'success'):
            smm_order_id = str(api_res.get('order', api_res.get('order_id', 'SUCCESS')))
            async with get_user_lock(uid):
              cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (total_price, uid, total_price))
              cur.execute("INSERT INTO smm_orders (user_id, service_id, link, quantity, total_price, smm_order_id, status) VALUES (?,?,?,?,?,?,?)",
                    (uid, state['service_id'], state['link'], qty, total_price, smm_order_id, 'Completed'))
              db.commit()
              bot_order_id = cur.lastrowid

            await log_smm_sale(
              uid, state['name'], bot_order_id, smm_order_id,
              state['link'], qty, total_price
            )
            smm_order_state.pop(uid, None)
            await e.respond(custom_emoji_text(f"{P_YES} <b>SMM Order Placed Successfully!</b> {P_PARTY}\n\n"
                    f"{P_GEAR} Service: {html.escape(state['name'])}\n"
                    f"{P_ID} Bot Order ID: <code>{bot_order_id}</code>\n"
                    f"{P_GEAR} Panel Order ID: <code>{smm_order_id}</code>\n"
                    f"{P_LINK} Link: {html.escape(state['link'])}\n"
                    f"{P_PKG} Quantity: {qty}\n"
                    f"{P_MONEY} Total Cost: ₹{total_price:.4f}\n\n"
                    f"<i>(Note: For refill use /refill {bot_order_id} or click Refill button)</i>"))
            await send_main_menu(e, uid)
          else:
            err_msg = api_res.get('error', 'Unknown error from SMM API') if isinstance(api_res, dict) else 'API connection failed'
            smm_order_state.pop(uid, None)
            await e.respond(custom_emoji_text(f"{P_NO} <b>SMM Order Failed:</b> {html.escape(str(err_msg))}"))
          return
        except ValueError:
          return await e.respond(custom_emoji_text(f"{P_NO} Please enter a valid number for quantity."))

    if uid in waiting_proof and waiting_proof[uid].get('step') == 'wait_utr':
      info = waiting_proof.pop(uid)
      amt = info['amount']
      raw_utr = (e.text or "").strip()

      if raw_utr.lower() in ("/cancel", "cancel"):
        return await e.reply(custom_emoji_text(
          f"{P_NO} Deposit cancelled. No money was added."))

      # FamPay / UPI UTRs are 12 digits, but some banks use 8-22 chars.
      utr = re.sub(r"[\s\-]", "", raw_utr).upper()
      if not re.fullmatch(r"[A-Z0-9]{8,30}", utr):
        waiting_proof[uid] = info
        return await e.reply(custom_emoji_text(
          f"{P_NO} <b>Invalid UTR.</b>\n\n"
          f"Send the transaction reference only (8-30 letters/digits).\n"
          f"<i>FamPay app → History → tap the payment → copy UTR.</i>\n\n"
          f"Send <code>/cancel</code> to abort."))
        
      await e.respond(custom_emoji_text(f"{P_WAIT} <b>Verifying transaction via automated Gmail IMAP... Please wait.</b>"))
      
      settings_row_user = cur.execute("SELECT value FROM settings WHERE key='imap_email'").fetchone()
      settings_row_pass = cur.execute("SELECT value FROM settings WHERE key='imap_password'").fetchone()
      g_user = settings_row_user[0].strip() if settings_row_user and settings_row_user[0] else ""
      g_pass = settings_row_pass[0].strip() if settings_row_pass and settings_row_pass[0] else ""
      
      # Never credit the same UTR twice (approved or still pending).
      existing_utr = cur.execute(
        "SELECT id, status FROM deposits WHERE UPPER(REPLACE(REPLACE(COALESCE(utr,''),' ',''),'-',''))=? "
        "AND status IN ('approved','pending') LIMIT 1", (utr,)).fetchone()
      if existing_utr or utr in _UTR_IN_PROGRESS:
        waiting_proof[uid] = info
        return await e.respond(custom_emoji_text(
          f"{P_NO} <b>This UTR has already been used.</b>\n"
          f"Please enter a different transaction UTR or send <code>/cancel</code>."))

      # Reserve the UTR while we verify so two quick submissions can never
      # both be credited. The mailbox is polled over ONE connection for up to
      # ~45s, so the payment is credited the moment the email arrives.
      _UTR_IN_PROGRESS.add(utr)
      credited = False
      try:
        paid_amount = await check_payment_in_gmail_async(
          utr, g_user, g_pass, expected_amount=amt, wait_seconds=45)

        if paid_amount is not None and paid_amount + 0.01 >= amt:
          # Credit what was actually paid when it is a sane over-payment
          # (max 2x the requested amount), otherwise credit the requested amount.
          credit = float(amt)
          try:
            if amt <= float(paid_amount) <= amt * 2:
              credit = round(float(paid_amount), 2)
          except Exception:
            pass
          async with get_user_lock(uid):
            dup = cur.execute(
              "SELECT id FROM deposits WHERE UPPER(REPLACE(REPLACE(COALESCE(utr,''),' ',''),'-',''))=? "
              "AND status IN ('approved','pending') LIMIT 1", (utr,)).fetchone()
            if dup:
              return await e.respond(custom_emoji_text(
                f"{P_NO} <b>This UTR has already been used.</b>"))
            prev_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
            prev_bal = prev_row[0] if prev_row else 0
            update_balance(uid, credit)
            cur.execute("INSERT INTO deposits (user_id, amount, method_name, status, utr) VALUES (?,?,?,?,?)", (uid, credit, "FamPay UPI", "approved", utr))
            cur.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE user_id=?", (credit, uid))
            db.commit()
          credited = True
      finally:
        _UTR_IN_PROGRESS.discard(utr)

      if credited:
        try:
          await log_primary_deposit_success(uid, credit, "FamPay UPI", utr)
        except Exception:
          pass

        user_msg = (f"{P_YES} {P_PARTY} <b>Payment Verified Automatically!</b>\n\n"
              f"{P_MONEY} <b>Amount Credited:</b> ₹{credit:g}\n"
              f"{P_CARD} Previous Balance: ₹{prev_bal:g} | New Balance: ₹{prev_bal + credit:g}\n"
              f"{P_ID} UTR: <code>{html.escape(utr)}</code>")
        await e.respond(custom_emoji_text(user_msg))
        await send_main_menu(e, uid)
      else:
        # Fallback: If automated check fails, ask for a screenshot for manual review.
        waiting_proof[uid] = {'step': 'wait_screenshot', 'amount': amt, 'utr': utr}
        await e.respond(
          custom_emoji_text(f"{P_WARN} <b>Automatic verification failed.</b>\n\n"
          f"No matching payment email was found for UTR <code>{html.escape(utr)}</code>, "
          f"or the amount in the email was lower than ₹{amt}.\n\n"
          f"{P_ASST} Send a <b>screenshot</b> of your payment receipt and the admin will approve it manually.\n"
          f"<i>Send <code>/cancel</code> to abort.</i>")
        )
      return

    if uid in waiting_proof and waiting_proof[uid].get('step') == 'wait_screenshot':
      if not e.photo:
        return await e.reply(custom_emoji_text(f"{P_NO} Please send a valid image screenshot."))
      
      info = waiting_proof.pop(uid)
      amt = info['amount']
      utr = info['utr']
      
      cur.execute("INSERT INTO deposits (user_id, amount, method_name, status, utr) VALUES (?,?,?,?,?)", (uid, amt, "FamPay UPI (Pending Screenshot)", "pending", utr))
      db.commit()
      dep_id = cur.lastrowid
      
      cap = (f"{P_BELL} <b>NEW FAMPAY/UPI MANUAL DEPOSIT REVIEW</b>\n\n"
          f"{P_ACC} User ID: <code>{uid}</code>\n"
          f"{P_MONEY} Amount: <b>₹{amt}</b>\n"
          f"{P_CARD} UTR: <code>{utr}</code>\n"
          f"{P_ID} Ref ID: <code>{dep_id}</code>")
      btns = [
        [Button.inline(f"Accept (₹{amt})", f"dep_acc|{dep_id}|{uid}|FamPay UPI|exact|{amt}"),
         Button.inline("Reject", f"dep_rej|{dep_id}|{uid}")]
      ]
      
      # Send manual deposit review with screenshot to the owner and all configured admins.
      await send_admins_file(e.photo, cap, buttons=btns)
        
      await e.respond(custom_emoji_text(f"{P_YES} <b>Payment screenshot forwarded to Admin successfully!</b>\nAdmin will review it and add the balance shortly."))
      await send_main_menu(e, uid)
      return

    text = e.text or ""
    if not text: return

    if text in ["Store", "Add Funds", "Profile", "Orders History", "Support", "Updates", "__ADMIN_PANEL_REMOVED__"]:
      session_buy_state.pop(uid, None)
      deposit_input.pop(uid, None)
      admin_dep_state.pop(uid, None)
      smm_order_state.pop(uid, None)
      refill_state.pop(uid, None)
      S1_SEARCH_STATE.pop(uid, None)

    # Server 1 mini-app search input (country search / account keyword).
    if uid in S1_SEARCH_STATE:
      st = S1_SEARCH_STATE.pop(uid, None) or {}
      if text.strip().lower() == "/cancel":
        return await e.respond(custom_emoji_text(f"{P_NO} Search cancelled."))
      if st.get("kind") == "country":
        return await server1_country_search_results(e, text)
      if st.get("kind") == "keyword":
        f = _s1_filters(uid)
        f["search"] = text.strip()
        cc = str(st.get("cc") or "").strip().upper()
        if cc:
          return await server1_country_detail(e, cc, 1)
        return await server1_filters_menu(e)

    if uid in session_buy_state:
      state = session_buy_state[uid]
      try:
        qty = int(re.sub(r'[^\d]', '', text))
        if qty < 1: raise ValueError
        if qty > state['stock']: return await e.respond(custom_emoji_text(f"{P_WARN} <b>Not enough stock!</b> Max is {state['stock']}."))
        
        disc_row = cur.execute("SELECT discount FROM users WHERE user_id=?", (uid,)).fetchone()
        discount = disc_row[0] if disc_row else 0
        total_cost = qty * state['price']
        if discount > 0: total_cost = int(total_cost * (100 - discount) / 100)
          
        bal_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        user_bal = bal_row[0] if bal_row else 0
        if user_bal < total_cost: return await e.respond(custom_emoji_text(f"{P_NO} <b>Insufficient Balance!</b>\nYou need {P_INR}{total_cost} to buy {qty} sessions."))

        session_buy_state.pop(uid)
        await process_bulk_sessions(e, uid, qty, state, total_cost)
        return
      except ValueError: return await e.respond(custom_emoji_text(f"{P_NO} Please enter a valid number."))

    if uid in deposit_input and deposit_input[uid].get('step') == 'wait_payment_screenshot':
      if not e.photo:
        return await e.respond(custom_emoji_text(f"{P_NO} Please send the payment screenshot."))
      info = deposit_input.pop(uid)
      amt = info['amount']
      method = info.get('method', 'UPI Manual')
      cur.execute("INSERT INTO deposits (user_id,amount,method_name,status,utr) VALUES (?,?,?,?,?)", (uid, amt, method, 'pending', ''))
      db.commit()
      dep_id = cur.lastrowid
      cap = (f"{P_BELL} <b>NEW {html.escape(method.upper())} DEPOSIT REVIEW</b>\n\n"
          f"{P_ACC} User ID: <code>{uid}</code>\n"
          f"{P_MONEY} Amount: <b>₹{amt}</b>\n"
          f"{P_CARD} Method: <b>{html.escape(method)}</b>\n"
          + (f"{P_USDT} USDT Expected: <b>{info['usdt_amount']:.2f} USDT</b> ({html.escape(str(info.get('network', '')))})\n"
             if info.get('usdt_amount') else "") +
          f"{P_ID} Ref ID: <code>{dep_id}</code>")
      btns = [[Button.inline(f"Accept ₹{amt}", f"dep_acc|{dep_id}|{uid}|{method}|exact|{amt}"), Button.inline("Reject", f"dep_rej|{dep_id}|{uid}")]]
      sent_admins = await send_admins_file(e.photo, cap, buttons=btns)
      if sent_admins:
        await e.respond(custom_emoji_text(f"{P_YES} <b>Screenshot sent to all admins.</b>\nYour payment is pending verification."))
      else:
        await e.respond(custom_emoji_text(f"{P_WARN} Screenshot received, but no admin could be reached right now."))
      return

  except Exception as ex: logger.error(f"Message Error: {ex}", exc_info=True)

@bot.on(events.CallbackQuery)
async def handle_callback_query(e):
  try:
    # Do not pre-answer the callback here. Individual branches answer alerts
    # when needed; pre-answering makes later alert/error responses invisible
    # and was causing many buttons to look dead. Successful edit/respond calls
    # also clear the Telegram button spinner.
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid):
      return await safe_callback_answer(
        e, "Bot is under maintenance. Please try again later." if get_bot_status() == 'maintenance'
        else "Bot is currently OFF. Please come back later.", alert=True)
      
    ensure_user(uid)
    if is_user_banned(uid): return await safe_callback_answer(e, "BANNED", alert=True)
    raw_data = getattr(e, "data", b"")
    if isinstance(raw_data, bytes):
      data = raw_data.decode("utf-8", errors="replace")
    else:
      data = str(raw_data or "")

    # Leaving a Shop photo/file message: send the next screen as a fresh text
    # message so the old photo never stays glued above unrelated screens.
    _mkey = (e.chat_id, getattr(e, "message_id", None) or getattr(getattr(e, "query", None), "msg_id", None))
    if _mkey in _SHOP_PREVIEW_MSGS or _mkey in _SHOP_DELIVERED_MSGS:
      _orig_edit = e.edit
      _delete_old = _mkey in _SHOP_PREVIEW_MSGS

      async def _edit_as_new(*args, **kwargs):
        text = args[0] if args else kwargs.get("text")
        if text is None or kwargs.get("file") is not None:
          return await _orig_edit(*args, **kwargs)
        if _delete_old:
          try:
            await e.delete()
          except Exception:
            pass
          _SHOP_PREVIEW_MSGS.discard(_mkey)
        return await bot.send_message(
          e.chat_id, text, buttons=kwargs.get("buttons"),
          parse_mode=kwargs.get("parse_mode", "html"))
      e.edit = _edit_as_new

    if data == "cb_store":
      try:
        await store_servers_menu(e)
      except Exception as ex:
        logger.error(f"Store callback error: {ex}", exc_info=True)
        await safe_callback_answer(e, "Store could not be opened. Please try /start again.", alert=True)
    elif data == "digital_shop":
      try:
        await digital_shop_menu(e)
      except Exception as ex:
        logger.error(f"Shop callback error: {ex}", exc_info=True)
        try:
          await bot.send_message(e.chat_id, custom_emoji_text(f"{P_NO} <b>Shop</b>\n\nPlease try again."), buttons=[[Button.inline("Back to Store", "store_servers")]], parse_mode='html')
        except Exception:
          pass
    elif data.startswith("digital_product|"):
      await digital_product_view(e, int(data.split("|")[1]))
    elif data.startswith("digital_buy|"):
      await digital_buy(e, int(data.split("|")[1]))
    elif data == "redeem_start":
      redeem_state[uid] = {'step':'wait_code'}
      await e.edit(custom_emoji_text("Enter your redeem code (for example: AKOP):"), buttons=[[Button.inline("Cancel","cancel_action")]])
    elif data == "smm_cancel":
      smm_order_state.pop(uid, None)
      await safe_callback_answer(e, "Cancelled.")
      await send_main_menu(e, uid)
    elif data == "cb_smm_services":
      smm_order_state.pop(uid, None)
      await show_smm_categories(e)
    elif data.startswith("smm_cat|"):
      smm_order_state.pop(uid, None)
      cid = int(data.split("|")[1])
      await show_smm_services_in_category(e, cid)
    elif data.startswith("smm_srv|"):
      sid = int(data.split("|")[1])
      await smm_service_detail_view(e, sid)
    elif data.startswith("smm_buy|"):
      sid = int(data.split("|")[1])
      row = cur.execute("SELECT service_id, name, rate, min, max FROM smm_services WHERE service_id=?", (sid,)).fetchone()
      if not row: return await safe_callback_answer(e, "Service not found.", alert=True)
      s_id, s_name, s_rate, s_min, s_max = row
      smm_order_state[uid] = {'service_id': s_id, 'name': s_name, 'rate': s_rate, 'min': s_min, 'max': s_max, 'step': 'wait_link'}
      await e.edit(custom_emoji_text(f"{P_ID} <b>Service ID: {s_id}</b>\n{P_TITLE} <b>Title: {html.escape(s_name)}</b>\n\n{P_ASST} <b>Send Link:</b>"), buttons=[[Button.inline(" Cancel", "cancel_action")]])
    elif data == "cb_addfunds":
      await deposit_menu(e)
    elif data == "cb_profile":
      await profile_handler(e, is_callback=True)
    elif data == "cb_orders":
      await orders_history_handler(e, is_callback=True)
    elif data == "cb_refill":
      refill_state[uid] = {'step': 'wait_order_id'}
      msg = f"{P_ID} <b>SMM Service Refill</b>\n\nPlease reply with your <b>Bot Order ID</b> that you want to refill:"
      btns = [[Button.inline("Cancel", "cancel_action")]]
      await e.edit(custom_emoji_text(msg), buttons=btns)
    elif data == "cb_support":
      # Backward-compatible handler for older menus.
      support_url = get_support_url()
      if not _has_valid_button_url(support_url):
        return await safe_callback_answer(e, custom_emoji_text(" Support link is not configured by Admin yet."), alert=True)
      await safe_callback_answer(e, custom_emoji_text(" Opening Support..."), alert=False)
      await e.respond(
        custom_emoji_text(f"{P_ON} <b>Support</b>\n\n{P_ASST} Tap below to contact support."),
        buttons=[[_safe_url_button("Support", support_url)],
             [Button.inline("Back to Main", "back_main")]]
      )
    elif data == "cb_updates":
      # Backward-compatible handler for older menus.
      updates_url = get_support_channel_url()
      if not _has_valid_button_url(updates_url):
        return await safe_callback_answer(e, custom_emoji_text(" Updates channel link is not configured by Admin yet."), alert=True)
      await safe_callback_answer(e, custom_emoji_text(" Opening Updates..."), alert=False)
      await e.respond(
        custom_emoji_text(f"{P_STAR} <b>Channel Updates & News</b> {P_ROCKET}\n\n{P_ASST} Tap below to open the official updates channel."),
        buttons=[[_safe_url_button("Updates", updates_url)],
             [Button.inline("Back to Main", "back_main")]]
      )
    elif data == "verify_join":
      if not await check_channel_joined(uid): return await safe_callback_answer(e, "You must join the channels first!", alert=True)
      await send_main_menu(e, uid)

    elif data == "cancel_action":
      deposit_input.pop(uid, None); waiting_proof.pop(uid, None); session_buy_state.pop(uid, None); smm_order_state.pop(uid, None); refill_state.pop(uid, None); redeem_state.pop(uid, None)
      try: await e.edit(custom_emoji_text(f"{P_NO} <b>Cancelled.</b>"))
      except MessageNotModifiedError: pass

    elif data == "store_servers":
      await store_servers_menu(e)

    elif data == "srv1_accounts":
      await server1_category_menu(e)

    elif data == "srv1_countries":
      await server1_countries_menu(e, 1)

    elif data.startswith("srv1_cat|"):
      await server1_pick_category(e, data.split("|", 1)[1])

    elif data == "srv1_agree":
      await server1_agree(e)

    elif data == "srv1_decline":
      await server1_decline(e)

    elif data.startswith("srv1_pg|"):
      await server1_countries_menu(e, int(data.split("|")[1]))

    elif data == "srv1_ref":
      await server1_countries_menu(e, 1, force_refresh=True)

    elif data.startswith("srv1_sort|"):
      await server1_set_sort(e, data.split("|", 1)[1])

    elif data.startswith("srv1_c|"):
      await server1_country_detail(e, data.split("|")[1], 1)

    elif data.startswith("srv1_l|"):
      await server1_country_detail(e, data.split("|")[1], 1)

    elif data.startswith("srv1_ip|"):
      p = data.split("|")
      await server1_country_detail(e, p[1], int(p[2]))

    elif data.startswith("srv1_ipr|"):
      p = data.split("|")
      await server1_country_detail(e, p[1], int(p[2]), force_refresh=True)

    elif data.startswith("srv1_i|"):
      p = data.split("|")
      await server1_item_detail(e, p[1], p[2], int(p[3]))

    elif data.startswith("srv1_buy|"):
      p = data.split("|")
      await server1_buy_number(e, p[1], p[2] if len(p) > 2 else None)

    elif data.startswith("srv1_bulk|"):
      await server1_bulk_menu(e, data.split("|", 1)[1])

    elif data.startswith("srv1_bq|"):
      p = data.split("|")
      await server1_bulk_buy(e, p[1], int(p[2]))

    elif data == "srv1_filters":
      await server1_filters_menu(e)

    elif data.startswith("srv1_fch|"):
      await server1_filter_choice(e, data.split("|", 1)[1])

    elif data.startswith("srv1_fset|"):
      p = data.split("|")
      await server1_filter_set(e, p[1], p[2] if len(p) > 2 else "any")

    elif data == "srv1_freset":
      await server1_filter_reset(e)

    elif data.startswith("srv1_fsearch"):
      await server1_filter_search(e, data.split("|", 1)[1] if "|" in data else "")

    elif data == "srv1_csearch":
      await server1_country_search_prompt(e)

    elif data.startswith("srv1_code|"):
      await server1_order_detail(e, data.split("|", 1)[1], poll=True)

    elif data.startswith("srv1_ord|"):
      await server1_order_detail(e, data.split("|", 1)[1], poll=False)

    elif data.startswith("srv1_ses|"):
      await server1_send_session(e, data.split("|", 1)[1])

    elif data.startswith("srv1_sec|"):
      await server1_secure_account(e, data.split("|", 1)[1])

    elif data == "srv1_orders":
      await orders_history_handler(e, is_callback=True)

    elif data == "back_main":
      try:
        await send_main_menu(e, uid)
      except Exception as ex:
        logger.error(f"back_main failed: {ex}", exc_info=True)
        try:
          await bot.send_message(
            uid,
            custom_emoji_text(f"{P_NO} <b>Could not open the main menu.</b>\n\n"
                              f"Please send /start to reload the bot."),
            buttons=[[Button.inline("Try Again", "back_main")]],
            parse_mode='html')
        except Exception:
          await safe_callback_answer(e, "Please send /start to reload the bot.", alert=True)

    elif data == "profile_callback":
      await profile_handler(e, is_callback=True)

    elif data.startswith("my_orders|"):
      await orders_history_handler(e, is_callback=True, page=int(data.split("|")[1]))
    elif data == "my_orders_list":
      await orders_history_handler(e, is_callback=True)

    elif data == "payments_history":
      await payments_history_handler(e)

    elif data == "dep_menu_cb":
      await deposit_menu(e)

    elif data.startswith("dep_key|"):
      state = deposit_input.get(uid)
      if not state or state.get('step') != 'amount_keypad':
        return await safe_callback_answer(e, "Amount session expired. Please start again.", alert=True)
      digit = data.split("|", 1)[1]
      if digit not in '0123456789':
        return await safe_callback_answer(e, "Invalid amount button.", alert=True)
      current = state.get('amount', '')
      if len(current) >= 8:
        return await safe_callback_answer(e, "Amount is too large.", alert=True)
      if not current and digit == '0':
        return await safe_callback_answer(e, "Amount cannot start with 0.", alert=True)
      state['amount'] = current + digit
      await show_deposit_amount_keypad(e, uid)

    elif data == "dep_key_del":
      state = deposit_input.get(uid)
      if not state or state.get('step') != 'amount_keypad':
        return await safe_callback_answer(e, "Amount session expired. Please start again.", alert=True)
      state['amount'] = state.get('amount', '')[:-1]
      await show_deposit_amount_keypad(e, uid)

    elif data == "dep_key_confirm":
      await generate_deposit_qr(e, uid)

    elif data == "dep_payment_verify":
      state = deposit_input.get(uid)
      if not state or state.get('step') != 'wait_payment_verify':
        return await safe_callback_answer(e, "Payment session expired. Please start again.", alert=True)
      amt = int(state.get('amount') or 0)
      method = state.get('method') or 'UPI Manual'

      if method == 'FamPay Automatic':
        # Automatic UTR verification: ask for the 12-digit UTR and check the
        # FamPay payment email through Gmail IMAP. Screenshot is only the
        # fallback when the email cannot be matched.
        deposit_input.pop(uid, None)
        waiting_proof[uid] = {'step': 'wait_utr', 'amount': amt, 'auto': True}
        await e.edit(custom_emoji_text(
          f"{P_CARD} <b>Verify Payment</b>\n\n"
          f"{P_MONEY} Amount: <b>₹{amt}</b>\n"
          f"{P_ACC} Method: <b>FamPay Automatic</b>\n\n"
          f"{P_ASST} <b>Send your UTR / Transaction ID now.</b>\n"
          f"<i>FamPay app → History → tap the payment → copy the 12-digit UTR.</i>\n\n"
          f"{P_WAIT} Payment is verified automatically — no screenshot needed.\n"
          f"Send <code>/cancel</code> to abort."
        ), buttons=[[Button.inline(" Cancel", "cancel_action")]])
      else:
        state['step'] = 'wait_payment_screenshot'
        _usdt_line = (f"USDT Sent: <b>{state['usdt_amount']:.2f} USDT</b> ({html.escape(str(state.get('network', '')))})\n"
                      if state.get('usdt_amount') else "")
        await e.edit(custom_emoji_text(
          f"{P_CARD} <b>Verify Payment</b>\n\n"
          f"Amount: <b>₹{state['amount']}</b>\n"
          + _usdt_line +
          f"Method: <b>{html.escape(method)}</b>\n\n"
          f"{P_ASST} <b>Now send your payment screenshot here.</b>\n"
          f"The screenshot will be sent to all admins for verification."
        ), buttons=[[Button.inline(" Cancel", "cancel_action")]])

    elif data.startswith("dep_verify_start|"):
      # Backward compatibility for old payment messages: use screenshot verification.
      amt = int(data.split("|")[1])
      deposit_input[uid] = {'step': 'wait_payment_screenshot', 'amount': amt, 'method': 'FamPay Automatic'}
      await e.edit(custom_emoji_text(f"{P_CARD} <b>Verify Payment</b>\n\nAmount: <b>₹{amt}</b>\n\n{P_ASST} <b>Send your payment screenshot here.</b>\nIt will be forwarded to all admins for manual verification."), buttons=[[Button.inline(" Cancel", "cancel_action")]])

    elif data == "srv|manual":
      await show_server_countries(e, 'manual', 1)

    elif data.startswith("srv_pg|"):
      p = data.split("|")
      await show_server_countries(e, p[1], int(p[2]))

    elif data.startswith("s_country|"):
      p = data.split("|", 2)
      country = _resolve_country_ref(p[2]) if len(p) > 2 else ""
      await show_country_details(e, p[1], country)

    elif data.startswith("p_buy|"):
      p = data.split("|", 2)
      flow = p[1]
      country = _resolve_country_ref(p[2]) if len(p) > 2 else ""
      if flow == 'single':
        rows = cur.execute("SELECT account_year, price FROM stock WHERE available=1 AND country_name LIKE ? ORDER BY price ASC LIMIT 1", (f"{country}%",)).fetchone()
        if not rows: return await safe_callback_answer(e, "Out of stock!", alert=True)
        await confirm_purchase(e, country, rows[0], rows[1])
      else:
        rows = cur.execute("SELECT account_year, price FROM stock WHERE available=1 AND country_name LIKE ? ORDER BY price ASC LIMIT 1", (f"{country}%",)).fetchone()
        if not rows: return await safe_callback_answer(e, "Out of stock!", alert=True)
        await init_session_purchase(e, country, rows[0], rows[1])

    elif data.startswith("p_year|"):
      country_ref = data.split("|", 1)[1]
      country = _resolve_country_ref(country_ref)
      await show_years_for_country(e, country)

    elif data.startswith("by_yr|"):
      p = data.split("|")
      country = _resolve_country_ref(p[1])
      await confirm_purchase(e, country, p[2], p[3])

    elif data.startswith("buy_cf|"):
      p = data.split("|")
      country = _resolve_country_ref(p[1])
      await process_purchase(e, country, p[2], p[3])

    elif data.startswith("get_otp_again|"):
      phone = data.split("|")[1]
      if phone not in active_orders:
        return await safe_callback_answer(e, "Session already logged out or expired.", alert=True)
      
      order = active_orders[phone]
      client = order['client']
      start_time = order['start_time']
      
      await safe_callback_answer(e, "Fetching latest OTP...", alert=False)
      try:
        msgs = await client.get_messages(777000, limit=5)
        latest_code = None
        for m in msgs:
          if m.date.timestamp() > start_time - 10:
            if m.message and re.search(r'\b\d{5}\b', m.message) and "Login detected" not in m.message:
              latest_code = re.search(r'\b\d{5}\b', m.message).group()
              break
        
        if latest_code:
          twofa_text = f"{P_2FA} <b>2FA:</b> <code>{html.escape(order['twofa'])}</code>" if order['twofa'] != "None" else f"{P_2FA} <b>2FA:</b> <code>Disabled (No Password)</code>"
          msg = (f"{P_YES} {P_FIRE} <b>Latest OTP Fetched!</b>\n\n"
              f"{P_PHONE} <b>Phone:</b> <code>{phone}</code>\n"
              f"{P_FLAG} <b>Country:</b> {html.escape(order['country'])}\n"
              f"{P_OTP} <b>OTP:</b> <code>{latest_code}</code>\n"
              f"{twofa_text}")
          btns = [
            [Button.inline("Get OTP Again", f"get_otp_again|{phone}")],
            [Button.inline("Finish & Logout", f"logout_bot|{phone}")]
          ]
          try: await e.edit(custom_emoji_text(msg), buttons=btns)
          except MessageNotModifiedError: pass
        else:
          await safe_callback_answer(e, "No new OTP found yet. Try again in a few seconds.", alert=True)
      except Exception:
        await safe_callback_answer(e, "Error fetching OTP.", alert=True)

    elif data.startswith("logout_bot|"):
      phone = data.split("|")[1]
      if phone in active_orders:
        order = active_orders.pop(phone)
        try: await order['client'].log_out()
        except: pass
        try: await order['client'].disconnect()
        except: pass
        delete_session_files(order['sess'])
        await e.edit(custom_emoji_text(f"{P_YES} <b>Session Finished & Logged out successfully.</b>"))
      else:
        await safe_callback_answer(e, "No active order found or already logged out.", alert=True)
    
    elif data == "depm_auto":
      if not payment_enabled('fampay_enabled'):
        await safe_callback_answer(e, "This payment method is currently disabled.", alert=True)
        return await deposit_menu(e)
      await manual_deposit_init(e, "FamPay Automatic")
    elif data == "depm_usdt":
      if not usdt_manual_available():
        await safe_callback_answer(e, "This payment method is currently unavailable.", alert=True)
        return await deposit_menu(e)
      await manual_deposit_init(e, "USDT Manual")
    elif data == "depm_manual":
      if not payment_enabled('manual_enabled'):
        await safe_callback_answer(e, "This payment method is currently disabled.", alert=True)
        return await deposit_menu(e)
      await manual_deposit_init(e, "UPI Manual")
    
    elif data.startswith("adm_") and is_admin(uid): await admin_actions(e)
    
    elif data.startswith("dep_acc|") and has_perm(uid, 'p_bal'):
      p = data.split("|")
      dep_id, t_uid, method, a_type = p[1], int(p[2]), p[3], p[4]
      row = cur.execute("SELECT status FROM deposits WHERE id=?", (dep_id,)).fetchone()
      if not row or row[0] != 'pending': return await e.edit(custom_emoji_text(f"{P_WARN} Already processed."))
      
      if a_type == "exact":
        amt = int(p[5]) 
        async with get_user_lock(t_uid):
          prev_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
          prev_bal = prev_row[0] if prev_row else 0
          update_balance(t_uid, amt)
          
          cur.execute("UPDATE deposits SET status='approved', amount=? WHERE id=?", (amt, dep_id))
          cur.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE user_id=?", (amt, t_uid))
          db.commit()
        await log_primary_deposit(t_uid, amt, method)
        
        user_msg = (f"{P_YES} {P_PARTY} <b>Deposit Approved!</b>\n\n{P_MONEY} <b>Amount Added:</b> ₹{amt}\n"
              f"Previous Balance: ₹{prev_bal} | New Balance: ₹{prev_bal+amt}")
        await bot.send_message(int(t_uid), custom_emoji_text(user_msg))
        try: await e.edit(custom_emoji_text(f"{P_YES} <b>MANUALLY CREDITED ₹{amt} TO {t_uid}</b>"))
        except MessageNotModifiedError: pass
        
    elif data.startswith("dep_rej|") and has_perm(uid, 'p_bal'):
      p = data.split("|")
      dep_id, t_uid = p[1], int(p[2])
      row = cur.execute("SELECT status FROM deposits WHERE id=?", (dep_id,)).fetchone()
      if not row or row[0] != 'pending': return await e.edit(custom_emoji_text(f"{P_WARN} Already processed."))
      admin_dep_state[uid] = {'target_uid': t_uid, 'dep_id': dep_id, 'step': 'wait_reason', 'msg_id': getattr(getattr(e, '_message', None), 'id', None)}
      await bot.send_message(uid, custom_emoji_text(f"{P_WARN} Reply to this message with the REASON for rejecting user <code>{t_uid}</code>:"))
      try: await safe_callback_answer(e, "Check your bot PMs to enter the reason.", alert=True)
      except: pass
    elif data.startswith("s2wa_"):
      await _s2wa_dispatch(e, data)

    elif data.startswith("fnmgmt"):
      await _fnm_dispatch(e, data)

    else:
      await safe_callback_answer(e, "This button is no longer active. Please open the menu again.", alert=True)

  except MessageNotModifiedError:
    # User tapped the same button again / content unchanged. Not an error.
    return
  except Exception as ex:
    logger.error(f"Callback Error: {ex}", exc_info=True)
    # Always leave the user with a visible response. If the callback was not
    # answered yet, the alert is useful; otherwise the chat message is the
    # fallback. Never let the error itself crash the callback handler.
    try:
      await safe_callback_answer(e, "This action failed. Please try again.", alert=True)
    except Exception:
      try:
        await bot.send_message(e.chat_id, f"Button error: {html.escape(str(ex))}")
      except Exception:
        pass


# =============================================================================
#  SERVER 2 [ WHATSAPP ACCOUNTS ]  +  FUNCTION MANAGEMENT  (integrated module)
#  ---------------------------------------------------------------------------
#  Tiger SMS API  ->  https://tiger-sms.com/api/openapi.json
#  All functions are prefixed _s2wa_ / _fnm_ so they never collide with the
#  rest of the bot. They reuse the bot's own db/cur, wallet, logs and styling.
# =============================================================================
import json as _s2wa_json
import time as _s2wa_time
import urllib.parse as _s2wa_urlparse
import urllib.request as _s2wa_urlreq
import urllib.error as _s2wa_urlerr
from datetime import datetime as _s2wa_datetime

_S2WA_HOSTS = [
  "https://api.tiger-sms.com/stubs/handler_api.php",
  "https://tiger-sms.com/stubs/handler_api.php",
]
_S2WA_BASE = _S2WA_HOSTS[0]
_S2WA_DEFAULT_SERVICE = "wa"
_S2WA_DEFAULT_MARGIN = 25.0
_S2WA_COUNTRIES_TTL = 6 * 3600
_S2WA_PRICES_TTL = 300

_S2WA_K_KEY = "s2_wa_api_key"
_S2WA_K_MARGIN = "s2_wa_margin"
_S2WA_K_SERVICE = "s2_wa_service"
_S2WA_K_ENABLED = "s2_wa_enabled"

_S2WA_FLAGS = {
    "russia": "\U0001F1F7\U0001F1FA", "brazil": "\U0001F1E7\U0001F1F7", "india": "\U0001F1EE\U0001F1F3",
    "indonesia": "\U0001F1EE\U0001F1E9", "usa": "\U0001F1FA\U0001F1F8", "united states": "\U0001F1FA\U0001F1F8",
    "united kingdom": "\U0001F1EC\U0001F1E7", "england": "\U0001F1EC\U0001F1E7", "germany": "\U0001F1E9\U0001F1EA",
    "france": "\U0001F1EB\U0001F1F7", "spain": "\U0001F1EA\U0001F1F8", "italy": "\U0001F1EE\U0001F1F9",
    "netherlands": "\U0001F1F3\U0001F1F1", "poland": "\U0001F1F5\U0001F1F1", "romania": "\U0001F1F7\U0001F1F4",
    "ukraine": "\U0001F1FA\U0001F1E6", "kazakhstan": "\U0001F1F0\U0001F1FF", "uzbekistan": "\U0001F1FA\U0001F1FF",
    "pakistan": "\U0001F1F5\U0001F1F0", "bangladesh": "\U0001F1E7\U0001F1E9", "nepal": "\U0001F1F3\U0001F1F5",
    "sri lanka": "\U0001F1F1\U0001F1F0", "philippines": "\U0001F1F5\U0001F1ED", "vietnam": "\U0001F1FB\U0001F1F3",
    "thailand": "\U0001F1F9\U0001F1ED", "malaysia": "\U0001F1F2\U0001F1FE", "singapore": "\U0001F1F8\U0001F1EC",
    "china": "\U0001F1E8\U0001F1F3", "japan": "\U0001F1EF\U0001F1F5", "south korea": "\U0001F1F0\U0001F1F7",
    "turkey": "\U0001F1F9\U0001F1F7", "egypt": "\U0001F1EA\U0001F1EC", "saudi arabia": "\U0001F1F8\U0001F1E6",
    "uae": "\U0001F1E6\U0001F1EA", "united arab emirates": "\U0001F1E6\U0001F1EA", "israel": "\U0001F1EE\U0001F1F1",
    "iran": "\U0001F1EE\U0001F1F7", "iraq": "\U0001F1EE\U0001F1F6", "morocco": "\U0001F1F2\U0001F1E6",
    "nigeria": "\U0001F1F3\U0001F1EC", "kenya": "\U0001F1F0\U0001F1EA", "south africa": "\U0001F1FF\U0001F1E6",
    "ghana": "\U0001F1EC\U0001F1ED", "mexico": "\U0001F1F2\U0001F1FD", "argentina": "\U0001F1E6\U0001F1F7",
    "colombia": "\U0001F1E8\U0001F1F4", "chile": "\U0001F1E8\U0001F1F1", "peru": "\U0001F1F5\U0001F1EA",
    "venezuela": "\U0001F1FB\U0001F1EA", "canada": "\U0001F1E8\U0001F1E6", "australia": "\U0001F1E6\U0001F1FA",
    "new zealand": "\U0001F1F3\U0001F1FF", "portugal": "\U0001F1F5\U0001F1F9", "greece": "\U0001F1EC\U0001F1F7",
    "czech": "\U0001F1E8\U0001F1FF", "hungary": "\U0001F1ED\U0001F1FA", "bulgaria": "\U0001F1E7\U0001F1EC",
    "serbia": "\U0001F1F7\U0001F1F8", "croatia": "\U0001F1ED\U0001F1F7", "sweden": "\U0001F1F8\U0001F1EA",
    "norway": "\U0001F1F3\U0001F1F4", "denmark": "\U0001F1E9\U0001F1F0", "finland": "\U0001F1EB\U0001F1EE",
    "switzerland": "\U0001F1E8\U0001F1ED", "austria": "\U0001F1E6\U0001F1F9", "belgium": "\U0001F1E7\U0001F1EA",
    "ireland": "\U0001F1EE\U0001F1EA", "belarus": "\U0001F1E7\U0001F1FE", "moldova": "\U0001F1F2\U0001F1E9",
    "georgia": "\U0001F1EC\U0001F1EA", "armenia": "\U0001F1E6\U0001F1F2", "azerbaijan": "\U0001F1E6\U0001F1FF",
    "kyrgyzstan": "\U0001F1F0\U0001F1EC", "tajikistan": "\U0001F1F9\U0001F1EF", "mongolia": "\U0001F1F2\U0001F1F3",
}


def _s2wa_flag(name):
  code = country_code_from_name(name)
  if code:
    return country_flag_fallback(code)
  return _S2WA_FLAGS.get((name or "").strip().lower(), "\U0001F30D")


def _s2wa_iso_from_flag(flag):
  """Decode a unicode flag emoji (two regional indicators) into ISO-3166-1
  alpha-2, e.g. \U0001F1F7\U0001F1FA -> "RU". Returns "" when it cannot."""
  try:
    chars = [c for c in str(flag or "") if 0x1F1E6 <= ord(c) <= 0x1F1FF]
    if len(chars) >= 2:
      return "".join(chr(ord(c) - 0x1F1E6 + 65) for c in chars[:2])
  except Exception:
    pass
  return ""


def _s2wa_flag_code(item):
  """Best-effort ISO-2 code for a WhatsApp country dict/flag/name."""
  if isinstance(item, dict):
    # Name decides the flag so country + flag always match.
    by_name = resolve_country_code(item.get("name"), None)
    if by_name:
      return by_name
    code = str(item.get("code") or "").strip().upper()
    if len(code) == 2 and code.isalpha():
      return code
    return _s2wa_iso_from_flag(item.get("flag"))
  raw = str(item or "").strip()
  if len(raw) == 2 and raw.isalpha():
    return raw.upper()
  return _s2wa_iso_from_flag(raw)


def _s2wa_flag_html(item):
  """Premium custom-emoji flag markup for WhatsApp panels."""
  code = _s2wa_flag_code(item)
  if not CUSTOM_EMOJI_ENABLED:
    return country_flag_fallback(code)
  return country_flag_html(code, item.get("name") if isinstance(item, dict) else None)


def _s2wa_flag_icon(item):
  """Custom emoji id used as the country button icon (None if unsupported)."""
  if not CUSTOM_EMOJI_ENABLED:
    return None
  return country_flag_icon_id(_s2wa_flag_code(item), item.get("name") if isinstance(item, dict) else None)


class _S2waError(Exception):
  pass


def _s2wa_hosts():
  """Admin-configured provider URL first, then the built-in mirrors."""
  hosts = []
  try:
    custom = str(get_setting("s2_wa_url", "") or "").strip()
  except Exception:
    custom = ""
  if custom:
    hosts.append(custom)
  hosts.extend(h for h in _S2WA_HOSTS if h not in hosts)
  return hosts


def _s2wa_http(action, api_key, **params):
  q = {"action": action, "api_key": api_key}
  for k, v in params.items():
    if v is not None:
      q[k] = v
  qs = _s2wa_urlparse.urlencode(q)
  last_err = None
  for base in _s2wa_hosts():
    url = base + "?" + qs
    req = _s2wa_urlreq.Request(url, headers={"User-Agent": "otpop-s2wa/1.0"})
    try:
      with _s2wa_urlreq.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace").strip()
        # A valid answer from this host: stop trying mirrors.
        if body:
          return body
        last_err = _S2waError("EMPTY_RESPONSE")
    except _s2wa_urlerr.HTTPError as ex:
      body = ""
      try:
        body = ex.read().decode("utf-8", "replace").strip()
      except Exception:
        pass
      if body == "BAD_KEY" or ex.code == 401:
        raise _S2waError("BAD_KEY")
      # A real API error (BAD_SERVICE / BAD_COUNTRY ...) -> do not retry mirrors.
      if body and ex.code < 500:
        raise _S2waError(body)
      last_err = _S2waError("HTTP_%s:%s" % (ex.code, body[:80]))
    except Exception as ex:
      last_err = _S2waError("NET:%s" % ex)
  raise last_err or _S2waError("NET:unknown")


class _S2waTiger(object):
  def __init__(self, api_key):
    if not api_key:
      raise _S2waError("NO_KEY")
    self.key = api_key

  def balance(self):
    raw = _s2wa_http("getBalance", self.key)
    if raw.startswith("ACCESS_BALANCE:"):
      try:
        return float(raw.split(":", 1)[1])
      except ValueError:
        raise _S2waError("BAD_BALANCE")
    raise _S2waError(raw)

  def countries(self):
    raw = _s2wa_http("getCountries", self.key)
    try:
      data = _s2wa_json.loads(raw)
    except Exception:
      raise _S2waError("BAD_JSON")
    if not isinstance(data, list):
      raise _S2waError("BAD_JSON")
    out = []
    for c in data:
      try:
        name = c.get("eng") or c.get("rus") or str(c["id"])
        flag = _s2wa_flag(name)
        out.append({"id": int(c["id"]), "name": name, "flag": flag,
                    "retry": c.get("retry"),
                    "code": resolve_country_code(name, None) or _s2wa_iso_from_flag(flag)})
      except Exception:
        continue
    out.sort(key=lambda x: x["name"].lower())
    return out

  def prices(self, service, country=None):
    params = {"service": service}
    if country is not None:
      params["country"] = country
    raw = _s2wa_http("getPrices", self.key, **params)
    try:
      return _s2wa_json.loads(raw)
    except Exception:
      raise _S2waError(raw)

  def price_for(self, service, country):
    data = self.prices(service, country)
    node = data.get(str(country), {}).get(service)
    if not node:
      return None
    try:
      return float(node["cost"]), int(node.get("count", 0))
    except Exception:
      return None

  def services(self):
    raw = _s2wa_http("getServicesList", self.key)
    try:
      data = _s2wa_json.loads(raw)
    except Exception:
      return []
    if isinstance(data, dict):
      return data.get("services") or []
    return []

  def price_map_v1(self, service=None):
    """getPrices -> {country_id(int): {service: {"cost": str, "count": int}}}"""
    raw = _s2wa_http("getPrices", self.key, service=service)
    try:
      data = _s2wa_json.loads(raw)
    except Exception:
      raise _S2waError(raw[:80] if raw else "BAD_JSON")
    if not isinstance(data, dict):
      raise _S2waError("BAD_JSON")
    return data

  def price_map_v3(self, service=None):
    """getPricesV3 -> {country_id(int): {service: {"price": float, "count": int}}}"""
    raw = _s2wa_http("getPricesV3", self.key, service=service)
    try:
      data = _s2wa_json.loads(raw)
    except Exception:
      raise _S2waError(raw[:80] if raw else "BAD_JSON")
    if not isinstance(data, dict):
      raise _S2waError("BAD_JSON")
    return data

  def get_number(self, service, country, max_price=None):
    params = {"service": service, "country": country}
    if max_price is not None:
      params["maxPrice"] = "%.4f" % max_price
    raw = _s2wa_http("getNumber", self.key, **params)
    if raw.startswith("ACCESS_NUMBER:"):
      parts = raw.split(":")
      if len(parts) >= 3:
        return parts[1], parts[2]
      raise _S2waError("BAD_NUMBER")
    raise _S2waError(raw)

  def status(self, activation_id):
    return _s2wa_http("getStatus", self.key, id=activation_id)

  def set_status(self, activation_id, status):
    return _s2wa_http("setStatus", self.key, id=activation_id, status=status)


# ---- config helpers --------------------------------------------------------
def _s2wa_api_key():
  return str(get_setting(_S2WA_K_KEY, "") or "").strip()


def _s2wa_margin():
  try:
    return float(get_setting(_S2WA_K_MARGIN, _S2WA_DEFAULT_MARGIN))
  except Exception:
    return _S2WA_DEFAULT_MARGIN


def _s2wa_service():
  return str(get_setting(_S2WA_K_SERVICE, _S2WA_DEFAULT_SERVICE) or _S2WA_DEFAULT_SERVICE)


def _s2wa_enabled():
  if str(get_setting(_S2WA_K_ENABLED, "on")).lower() != "on":
    return False
  return _fnm_on("server2wa")


def _s2wa_sell_price(cost_usd):
  try:
    rate = float(get_usdt_rate())
  except Exception:
    rate = 94.0
  return round(cost_usd * rate * (1.0 + _s2wa_margin() / 100.0), 2)


def _s2wa_wallet(uid):
  try:
    return float(_s1_wallet(uid)[0])
  except Exception:
    try:
      row = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
      return float(row[0] or 0) if row else 0.0
    except Exception:
      return 0.0


_S2WA_CACHE = {"countries": (0, None), "prices": {}, "map": (0, None), "service": (0, None)}


def _s2wa_countries(force=False):
  now = _s2wa_time.time()
  ts, data = _S2WA_CACHE["countries"]
  if not force and data is not None and now - ts < _S2WA_COUNTRIES_TTL:
    return data
  data = _S2waTiger(_s2wa_api_key()).countries()
  _S2WA_CACHE["countries"] = (now, data)
  return data


def _s2wa_resolve_service(force=False):
  """Return a service code that the provider actually knows.

  The configured code (default 'wa') is used when it exists in
  getServicesList; otherwise we auto-detect the WhatsApp entry so the price
  lookup never dies with BAD_SERVICE.
  """
  configured = _s2wa_service()
  now = _s2wa_time.time()
  ts, cached = _S2WA_CACHE["service"]
  if not force and cached and now - ts < _S2WA_COUNTRIES_TTL:
    return cached
  try:
    services = _S2waTiger(_s2wa_api_key()).services()
  except Exception:
    return configured
  codes = []
  for s in services or []:
    try:
      code = str(s.get("code") or "").strip()
      name = str(s.get("name") or "").lower()
      if code:
        codes.append((code, name))
    except Exception:
      continue
  if not codes:
    return configured
  if any(c == configured for c, _n in codes):
    _S2WA_CACHE["service"] = (now, configured)
    return configured
  # Auto-detect WhatsApp by name, then by common codes.
  for c, n in codes:
    if "whats" in n:
      _S2WA_CACHE["service"] = (now, c)
      return c
  for c, _n in codes:
    if c in ("wa", "whatsapp", "wa_", "wb"):
      _S2WA_CACHE["service"] = (now, c)
      return c
  return configured


def _s2wa_prices_map(force=False):
  """Return {country_id(int): (cost_usd float, count int)} for WhatsApp.

  Tries, in order: getPrices(service) -> getPricesV3(service) ->
  getPrices(no filter) -> getPricesV3(no filter). This makes the country
  list work across every provider variant instead of failing on one call.
  """
  now = _s2wa_time.time()
  ts, cached = _S2WA_CACHE["map"]
  if not force and cached is not None and now - ts < _S2WA_PRICES_TTL:
    return cached

  tiger = _S2waTiger(_s2wa_api_key())
  service = _s2wa_resolve_service(force)
  wanted = {service, "wa", "whatsapp", "wb"}
  errors = []

  def _extract(raw_map, price_key):
    out = {}
    if not isinstance(raw_map, dict):
      return out
    for cid, node in raw_map.items():
      try:
        cid_i = int(cid)
      except Exception:
        continue
      if not isinstance(node, dict):
        continue
      svc_node = None
      for cand in (service, "wa", "whatsapp", "wb"):
        if cand in node and isinstance(node[cand], dict):
          svc_node = node[cand]
          break
      if svc_node is None:
        # no-filter call: accept the first service node that looks like WhatsApp
        for k, v in node.items():
          if isinstance(v, dict) and str(k).lower() in wanted:
            svc_node = v
            break
      if svc_node is None:
        continue
      try:
        cost = float(svc_node.get(price_key, svc_node.get("cost", svc_node.get("price"))))
        count = int(svc_node.get("count", 0) or 0)
      except Exception:
        continue
      if cost > 0:
        out[cid_i] = (cost, count)
    return out

  attempts = [
    (lambda: tiger.price_map_v1(service), "cost"),
    (lambda: tiger.price_map_v3(service), "price"),
    (lambda: tiger.price_map_v1(None), "cost"),
    (lambda: tiger.price_map_v3(None), "price"),
  ]
  for fn, pk in attempts:
    try:
      raw = fn()
      parsed = _extract(raw, pk)
      if parsed:
        _S2WA_CACHE["map"] = (now, parsed)
        return parsed
    except Exception as ex:
      errors.append(str(ex))

  # Nothing parsed: surface a useful reason instead of a silent empty list.
  raise _S2waError(errors[-1] if errors else "NO_PRICES")


def _s2wa_price(country_id, force=False):
  try:
    pmap = _s2wa_prices_map(force)
  except Exception:
    return None
  return pmap.get(int(country_id))


# ---- local orders table ----------------------------------------------------
def _s2wa_ensure_table():
  cur.execute(
    """
    CREATE TABLE IF NOT EXISTS s2_wa_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid INTEGER NOT NULL,
        activation_id TEXT,
        phone TEXT,
        country_name TEXT,
        country_id INTEGER,
        service TEXT,
        cost_usd REAL,
        price_inr REAL,
        status TEXT,
        code TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """
  )
  cur.execute("CREATE INDEX IF NOT EXISTS idx_s2wa_uid ON s2_wa_orders(uid)")
  db.commit()


def _s2wa_new_order(uid, activation_id, phone, country_name, country_id, service, cost_usd, price_inr):
  now = _s2wa_datetime.utcnow().isoformat()
  cur.execute(
    "INSERT INTO s2_wa_orders(uid,activation_id,phone,country_name,country_id,"
    "service,cost_usd,price_inr,status,created_at,updated_at) "
    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
    (uid, activation_id, phone, country_name, country_id, service,
     cost_usd, price_inr, "WAIT_CODE", now, now),
  )
  db.commit()
  return cur.lastrowid


def _s2wa_update_order(activation_id, **fields):
  if not fields:
    return
  fields["updated_at"] = _s2wa_datetime.utcnow().isoformat()
  cols = ", ".join("%s=?" % k for k in fields)
  cur.execute("UPDATE s2_wa_orders SET %s WHERE activation_id=?" % cols,
              tuple(fields.values()) + (activation_id,))
  db.commit()


def _s2wa_get_order(activation_id):
  row = cur.execute("SELECT * FROM s2_wa_orders WHERE activation_id=?", (activation_id,)).fetchone()
  if not row:
    return None
  cols = [d[0] for d in cur.description]
  return dict(zip(cols, row))


def _s2wa_user_orders(uid, limit=10):
  rows = cur.execute("SELECT * FROM s2_wa_orders WHERE uid=? ORDER BY id DESC LIMIT ?",
                     (uid, limit)).fetchall()
  cols = [d[0] for d in cur.description]
  return [dict(zip(cols, r)) for r in rows]


# ---- UI helpers ------------------------------------------------------------
def _s2wa_sc(text):
  """Full small-caps rendering used by the WhatsApp panel (like the demo)."""
  try:
    return _button_font(str(text).lower())
  except Exception:
    return str(text)


_S2WA_RULE = "\u2500" * 18


def _s2wa_head(title):
  return "\u2726 %s \u2726" % _s2wa_sc(title)


async def _s2wa_send(event, text, buttons=None):
  # NOTE: intentionally NOT passed through custom_emoji_text() so the panel
  # keeps its emoji decorations (the demo look). Buttons still get their
  # premium custom-emoji icons from the global Button proxy.
  global CUSTOM_EMOJI_ENABLED
  bodies = [text]
  if "<tg-emoji" in str(text):
    bodies.append(strip_custom_emoji(text))
  for idx, body in enumerate(bodies):
    try:
      await event.edit(body, buttons=buttons, parse_mode="html")
      return
    except MessageNotModifiedError:
      return
    except Exception as ex:
      logger.warning("s2wa edit failed (try %s): %s", idx, ex)
      if idx == 0 and len(bodies) > 1:
        CUSTOM_EMOJI_ENABLED = False
  for idx, body in enumerate(bodies):
    try:
      await event.respond(body, buttons=buttons, parse_mode="html")
      return
    except Exception as ex:
      logger.warning("s2wa send failed (try %s): %s", idx, ex)


async def _s2wa_answer(event, text=None, alert=False):
  try:
    await safe_callback_answer(event, text or "", alert=alert)
  except Exception:
    pass


def _s2wa_back_row():
  return [Button.inline("Back to Store", "s2wa_store")]


def _s2wa_available():
  """List of countries that currently have a WhatsApp offer (cost > 0).

  Sold-out countries (count == 0) are hidden, but if the provider does not
  report stock at all we fall back to the full priced list so the screen is
  never empty.
  """
  countries = _s2wa_countries()
  pmap = _s2wa_prices_map()
  in_stock = []
  out_of_stock = []
  for c in countries:
    try:
      pr = pmap.get(int(c["id"]))
    except Exception:
      pr = None
    if not pr or pr[0] <= 0:
      continue
    item = {"id": int(c["id"]), "name": c["name"], "flag": c["flag"],
            "code": c.get("code") or _s2wa_iso_from_flag(c.get("flag")),
            "cost": pr[0], "count": pr[1]}
    if pr[1] > 0:
      in_stock.append(item)
    else:
      out_of_stock.append(item)
  return in_stock if in_stock else out_of_stock


def _s2wa_human_error(ex):
  s = str(ex)
  if "BAD_KEY" in s:
    return "Invalid API key. Please contact the admin."
  if "BAD_SERVICE" in s:
    return "WhatsApp is not available at the provider."
  if "NO_BALANCE" in s:
    return "Provider balance is empty. Please contact the admin."
  if "NO_NUMBERS" in s:
    return "No numbers are available right now. Please try again later."
  if "NO_PRICES" in s:
    return "The price list could not be loaded. Please try again later."
  if "NET:" in s:
    return "Network error. Please try again later."
  return "Error: %s" % s


# ---- screens ---------------------------------------------------------------
async def _s2wa_home(event, uid):
  if not _s2wa_enabled() and not is_admin(uid):
    await _s2wa_answer(event, "Server 2 is currently disabled.", alert=True)
    return
  if not _s2wa_api_key():
    if is_admin(uid):
      await _s2wa_send(
        event,
        "\u26a0\ufe0f <b>%s</b>\n\n%s\n\n%s\n<code>/s2wa_key &lt;your_32_char_key&gt;</code>"
        % (_s2wa_sc("Server 2 WhatsApp Accounts"),
           _s2wa_sc("API key is not set."),
           _s2wa_sc("Set it with:")),
        buttons=[_s2wa_back_row()],
      )
    else:
      await _s2wa_answer(event, "Server 2 is not available right now.", alert=True)
    return

  country_count = "\u2014"
  try:
    country_count = str(len(await asyncio.to_thread(_s2wa_available)))
  except Exception:
    country_count = "\u2014"

  text = (
    "\U0001F310 <b>%s</b>\n\n"
    "%s\n"
    "\u25b8 %s : \u20b9%.2f\n"
    "\u25b8 %s : %s %s\n"
    "\u25b8 %s : %.0f%%\n\n"
    "\U0001F680 %s"
  ) % (
    _s2wa_sc("Server 2 \u2022 WhatsApp Accounts"),
    _s2wa_head("WhatsApp OTP Number Store"),
    _s2wa_sc("Wallet"), _s2wa_wallet(uid),
    _s2wa_sc("Stock"), country_count, _s2wa_sc("Countries"),
    _s2wa_sc("Markup"), _s2wa_margin(),
    _s2wa_sc("Instant Delivery \u2022 24\u00d77"),
  )
  rows = [
    [Button.inline("Buy WhatsApp Number", "s2wa_countries")],
    [Button.inline("My Orders", "cb_orders"), Button.inline("Refresh", "s2wa_home")],
  ]
  if is_admin(uid):
    rows.append([Button.inline("Provider Balance", "s2wa_balance")])
  rows.append([Button.inline("Back to Store", "s2wa_store")])
  await _s2wa_send(event, text, buttons=rows)


async def _s2wa_countries_screen(event, uid, page=0):
  try:
    available = await asyncio.to_thread(_s2wa_available)
  except Exception as ex:
    await _s2wa_send(
      event,
      "\u274c <b>%s</b>\n\n%s\n\n<code>%s</code>"
      % (_s2wa_sc("Country Fetch Failed"), _s2wa_sc(_s2wa_human_error(ex)),
         html.escape(str(ex))[:120]),
      buttons=[[Button.inline("Try Again", "s2wa_countries")], _s2wa_back_row()],
    )
    return
  if not available:
    await _s2wa_send(
      event,
      "\u274c <b>%s</b>\n\n%s"
      % (_s2wa_sc("No Country Available"),
         _s2wa_sc("No WhatsApp numbers are available right now.")),
      buttons=[[Button.inline("Try Again", "s2wa_countries")], _s2wa_back_row()],
    )
    return

  per = 8
  pages = (len(available) + per - 1) // per
  page = max(0, min(page, pages - 1))
  chunk = available[page * per:(page + 1) * per]

  rows = []
  country_lines = []
  for c in chunk:
    price = _s2wa_sell_price(c["cost"])
    country_lines.append(
      "%s <b>%s</b> \u2014 \u20b9%.0f \u2022 %s %s"
      % (_s2wa_flag_html(c), html.escape(str(c["name"])), price,
         c["count"], _s2wa_sc("in stock")))
    rows.append([Button.inline(
      "%s \u2022 \u20b9%.0f \u2022 Stock %s" % (c["name"], price, c["count"]),
      "s2wa_c:%s" % c["id"],
      icon_custom_emoji_id=_s2wa_flag_icon(c))])

  nav = []
  if page > 0:
    nav.append(Button.inline("Prev", "s2wa_countries:%s" % (page - 1)))
  nav.append(Button.inline("%s/%s" % (page + 1, pages), "s2wa_noop"))
  if page < pages - 1:
    nav.append(Button.inline("Next", "s2wa_countries:%s" % (page + 1)))
  rows.append(nav)
  rows.append([Button.inline("My Orders", "cb_orders")])
  rows.append([Button.inline("Home", "s2wa_home"), Button.inline("Back", "s2wa_store")])

  text = (
    "%s <b>%s</b>\n\n"
    "%s\n"
    "%s\n"
    "\u25b8 %s : \u20b9%.2f\n"
    "\u25b8 %s : %s\n"
    "\u25b8 %s : %s\n\n"
    "%s\n\n"
    "%s"
  ) % (
    P_GLOBE, _s2wa_sc("Choose Country"),
    _s2wa_head("WhatsApp OTP Numbers"),
    _S2WA_RULE,
    _s2wa_sc("Wallet"), _s2wa_wallet(uid),
    _s2wa_sc("Available Countries"), len(available),
    _s2wa_sc("Markup"), ("%.0f%%" % _s2wa_margin()),
    "\n".join(country_lines),
    _s2wa_sc("Tap a country to see details"),
  )
  await _s2wa_send(event, text, buttons=rows)


async def _s2wa_country_detail(event, uid, country_id):
  try:
    data = await asyncio.to_thread(_s2wa_countries)
    country = next((c for c in data if int(c["id"]) == int(country_id)), None)
    pr = await asyncio.to_thread(_s2wa_price, country_id)
  except Exception as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return
  if not country:
    await _s2wa_answer(event, "Country not found", alert=True)
    return
  if not pr:
    await _s2wa_send(
      event,
      "%s <b>%s</b>\n\n%s"
      % (_s2wa_flag_html(country), _s2wa_sc(country["name"]),
         _s2wa_sc("WhatsApp numbers are not available for this country.")),
      buttons=[[Button.inline("Countries", "s2wa_countries")], _s2wa_back_row()],
    )
    return

  cost, count = pr
  price = _s2wa_sell_price(cost)
  wallet = _s2wa_wallet(uid)
  can_buy = wallet >= price
  retry_txt = "Yes" if str(country.get("retry")) in ("1", "True", "true") else "No"
  text = (
    "%s <b>%s</b>\n\n"
    "%s\n"
    "%s\n"
    "\u25b8 %s : WhatsApp\n"
    "\u25b8 %s : %s\n"
    "\u25b8 %s : %s %s\n"
    "\u25b8 %s : %s\n"
    "\u25b8 %s : %s\n\n"
    "%s"
  ) % (
    _s2wa_flag_html(country), _s2wa_sc(country["name"]),
    _s2wa_head("WhatsApp OTP Number"),
    _S2WA_RULE,
    _s2wa_sc("Service"),
    _s2wa_sc("Country"), _s2wa_sc(country["name"]),
    _s2wa_sc("Stock"), count, _s2wa_sc("Numbers"),
    _s2wa_sc("Retry Code"), _s2wa_sc(retry_txt),
    _s2wa_sc("Delivery"), _s2wa_sc("Instant"),
    ("\u2705 " + _s2wa_sc("Tap Buy Now to get your number")) if can_buy
    else ("\u274c " + _s2wa_sc("Insufficient wallet balance. Please add funds first.")),
  )
  rows = []
  if can_buy:
    rows.append([Button.inline("Buy Now \u2022 \u20b9%.0f" % price, "s2wa_buy:%s" % country_id)])
  rows.append([Button.inline("Refresh", "s2wa_c:%s" % country_id)])
  rows.append([Button.inline("Countries", "s2wa_countries"), Button.inline("Home", "s2wa_home")])
  await _s2wa_send(event, text, buttons=rows)


async def _s2wa_buy(event, uid, country_id):
  try:
    data = await asyncio.to_thread(_s2wa_countries)
    country = next((c for c in data if int(c["id"]) == int(country_id)), None)
    pr = await asyncio.to_thread(_s2wa_price, country_id, True)
  except Exception as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return
  if not country or not pr:
    await _s2wa_answer(event, "Not available", alert=True)
    return

  cost, _count = pr
  price = _s2wa_sell_price(cost)
  if _s2wa_wallet(uid) < price:
    await _s2wa_answer(event, "Insufficient balance. You need \u20b9%.2f" % price, alert=True)
    return

  await _s2wa_answer(event, "Allocating your number\u2026")
  service = _s2wa_resolve_service()
  try:
    act_id, phone = await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).get_number,
                                            service, country_id, cost)
  except _S2waError as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return

  try:
    update_balance(uid, -price)
  except Exception as ex:
    logger.warning("s2wa wallet debit failed: %s", ex)
  try:
    order_id = _s2wa_new_order(uid, act_id, phone, country["name"], country_id,
                               service, cost, price)
  except Exception as ex:
    logger.warning("s2wa order insert failed: %s", ex)
    order_id = "-"
  await log_wa_sale(uid, country, price, phone, act_id, order_id)

  text = (
    "\u2705 <b>%s</b>\n\n"
    "%s\n"
    "%s\n"
    "\u25b8 %s : %s %s\n"
    "\u25b8 %s : <code>%s</code>\n"
    "\u25b8 %s : \u20b9%.2f\n"
    "\u25b8 %s : #%s\n\n"
    "\u23f3 %s"
  ) % (
    _s2wa_sc("Number Allocated"),
    _s2wa_head("WhatsApp OTP Number"),
    _S2WA_RULE,
    _s2wa_sc("Country"), _s2wa_flag_html(country), _s2wa_sc(country["name"]),
    _s2wa_sc("Number"), phone,
    _s2wa_sc("Price"), price,
    _s2wa_sc("Order ID"), order_id,
    _s2wa_sc("Send OTP to this number and tap Get Code"),
  )
  rows = [
    [Button.inline("Get Code", "s2wa_code:%s" % act_id)],
    [Button.inline("Cancel", "s2wa_cancel:%s" % act_id), Button.inline("Home", "s2wa_home")],
  ]
  await _s2wa_send(event, text, buttons=rows)


async def _s2wa_poll_code(event, uid, act_id, manual=True):
  if manual:
    await _s2wa_answer(event, "Checking\u2026")
  try:
    raw = await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).status, act_id)
  except Exception as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return

  order = _s2wa_get_order(act_id) or {}
  phone = order.get("phone", "\u2014")
  country_name = order.get("country_name", "")

  if raw.startswith("STATUS_OK"):
    code = raw.split(":", 1)[1] if ":" in raw else ""
    _s2wa_update_order(act_id, status="DONE", code=code)
    try:
      await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).set_status, act_id, 6)
    except Exception:
      pass
    text = (
      "\U0001F389 <b>%s</b>\n\n"
      "%s\n"
      "\u25b8 %s : <code>%s</code>\n"
      "\u25b8 %s : <code>%s</code>\n"
      "\u25b8 %s : \u2705 %s\n\n"
      "\u2705 %s"
    ) % (
      _s2wa_sc("Code Received"),
      _s2wa_head("WhatsApp OTP Number"),
      _s2wa_sc("Number"), phone,
      _s2wa_sc("Code"), code,
      _s2wa_sc("Status"), _s2wa_sc("Complete"),
      _s2wa_sc("Order Finished"),
    )
    await _s2wa_send(event, text,
                     buttons=[[Button.inline("Home", "s2wa_home"), Button.inline("Back", "s2wa_store")]])
    return

  if raw.startswith("STATUS_WAIT_RETRY"):
    code = raw.split(":", 1)[1] if ":" in raw else ""
    _s2wa_update_order(act_id, status="WAIT_RETRY", code=code)
    text = (
      "\u26a0\ufe0f <b>%s</b>\n\n"
      "%s\n"
      "\u25b8 %s : <code>%s</code>\n"
      "\u25b8 %s : <code>%s</code>\n\n"
      "%s"
    ) % (
      _s2wa_sc("Retry Code"),
      _s2wa_head("WhatsApp OTP Number"),
      _s2wa_sc("Number"), phone,
      _s2wa_sc("Code"), code,
      _s2wa_sc("If this code does not work, tap Retry to get a new SMS."),
    )
    await _s2wa_send(event, text, buttons=[
      [Button.inline("Retry", "s2wa_retry:%s" % act_id)],
      [Button.inline("Check Again", "s2wa_code:%s" % act_id),
       Button.inline("Cancel", "s2wa_cancel:%s" % act_id)],
    ])
    return

  if raw in ("ACCESS_CANCEL", "STATUS_CANCEL"):
    _s2wa_update_order(act_id, status="CANCELLED")
    await _s2wa_send(event, "\u274c <b>%s</b>" % _s2wa_sc("Activation cancelled"),
                     buttons=[[Button.inline("Home", "s2wa_home")]])
    return

  if raw == "NO_ACTIVATION":
    await _s2wa_send(event, "\u274c <b>%s</b>" % _s2wa_sc("Activation not found (expired?)"),
                     buttons=[[Button.inline("Home", "s2wa_home")]])
    return

  _s2wa_update_order(act_id, status="WAIT_CODE")
  text = (
    "\u23f3 <b>%s</b>\n\n"
    "%s\n"
    "\u25b8 %s : <code>%s</code>\n"
    "\u25b8 %s : %s\n\n"
    "%s"
  ) % (
    _s2wa_sc("Code Not Received Yet"),
    _s2wa_head("WhatsApp OTP Number"),
    _s2wa_sc("Number"), phone,
    _s2wa_sc("Country"), _s2wa_sc(country_name),
    _s2wa_sc("Request the OTP in WhatsApp, then tap Check Again."),
  )
  await _s2wa_send(event, text, buttons=[
    [Button.inline("Check Again", "s2wa_code:%s" % act_id)],
    [Button.inline("Cancel", "s2wa_cancel:%s" % act_id), Button.inline("Home", "s2wa_home")],
  ])


async def _s2wa_retry(event, uid, act_id):
  try:
    await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).set_status, act_id, 3)
  except Exception as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return
  await _s2wa_answer(event, "Retry requested \u2705")
  await _s2wa_poll_code(event, uid, act_id, manual=False)


async def _s2wa_cancel(event, uid, act_id):
  order = _s2wa_get_order(act_id)
  if not order:
    await _s2wa_answer(event, "Order not found", alert=True)
    return
  try:
    raw = await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).set_status, act_id, 8)
  except Exception as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return
  if raw.startswith("STATUS_OK"):
    code = raw.split(":", 1)[1] if ":" in raw else ""
    _s2wa_update_order(act_id, status="DONE", code=code)
    await _s2wa_answer(event, "The SMS has already arrived \u2014 cancellation was not possible.", alert=True)
    await _s2wa_poll_code(event, uid, act_id, manual=False)
    return
  price = float(order.get("price_inr") or 0)
  try:
    update_balance(uid, price)
  except Exception:
    pass
  _s2wa_update_order(act_id, status="CANCELLED")
  text = (
    "\u274c <b>%s</b>\n\n"
    "\u25b8 %s : \u20b9%.2f\n"
    "\u25b8 %s : %s"
  ) % (
    _s2wa_sc("Cancelled"),
    _s2wa_sc("Refunded"), price,
    _s2wa_sc("Wallet"), _s2wa_sc("Balance updated"),
  )
  await _s2wa_send(event, text, buttons=[[Button.inline("Home", "s2wa_home")], _s2wa_back_row()])


_S2WA_STATUS_LABEL = {
  "DONE": ("\u2705", "Complete"),
  "CANCELLED": ("\u274c", "Cancelled"),
  "WAIT_CODE": ("\u23f3", "Waiting"),
  "WAIT_RETRY": ("\u26a0\ufe0f", "Retry"),
}


async def _s2wa_orders(event, uid):
  rows_data = _s2wa_user_orders(uid, 10)
  if not rows_data:
    await _s2wa_send(
      event,
      "\U0001F4C4 <b>%s</b>\n\n%s" % (_s2wa_sc("My Orders"),
                                     _s2wa_sc("You have no orders yet.")),
      buttons=[[Button.inline("Home", "s2wa_home")], _s2wa_back_row()],
    )
    return

  lines = [
    "\U0001F4C4 <b>%s</b>\n" % _s2wa_sc("My Orders"),
    _s2wa_head("Server 2 \u2022 WhatsApp"),
    "\u25b8 %s : %s %s\n" % (_s2wa_sc("Total"), len(rows_data), _s2wa_sc("Orders")),
  ]
  for o in rows_data:
    st = o.get("status", "")
    icon, label = _S2WA_STATUS_LABEL.get(st, ("\u2022", st.title() if st else "\u2014"))
    lines.append(
      "%s <code>%s</code> \u2022 \u20b9%.2f\n   %s : %s%s"
      % (icon, o.get("phone", "\u2014"), float(o.get("price_inr") or 0),
         _s2wa_sc("Status"), _s2wa_sc(label),
         (" \u2022 %s : <code>%s</code>" % (_s2wa_sc("Code"), o["code"])) if o.get("code") else "")
    )
  await _s2wa_send(event, "\n".join(lines),
                   buttons=[[Button.inline("Home", "s2wa_home")], _s2wa_back_row()])


async def _s2wa_balance(event, uid):
  if not is_admin(uid):
    await _s2wa_answer(event, "Admin only", alert=True)
    return
  try:
    bal = await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).balance)
  except Exception as ex:
    await _s2wa_answer(event, _s2wa_human_error(ex), alert=True)
    return
  try:
    rate = float(get_usdt_rate())
  except Exception:
    rate = 94.0
  text = (
    "\U0001F4B3 <b>%s</b>\n\n"
    "%s\n"
    "\u25b8 %s : $%.4f\n"
    "\u25b8 %s : \u20b9%.2f"
  ) % (
    _s2wa_sc("Provider Balance"),
    _s2wa_head("Tiger SMS"),
    _s2wa_sc("USD"), bal,
    _s2wa_sc("INR"), bal * rate,
  )
  await _s2wa_send(event, text,
                   buttons=[[Button.inline("Refresh", "s2wa_balance")],
                            [Button.inline("Home", "s2wa_home")]])


# ---- function management ---------------------------------------------------
_S2WA_FEATURES = [
  ("server1", "Server 1 [ Cheap Account ]", True),
  ("srv3manual", "Server 3 [ Manually Added Accounts ]", True),
  ("server2wa", "Server 2 [ WhatsApp Accounts ]", True),
  ("shop", "Digital Shop", True),
  ("smm", "Social Media Services", True),
]
_S2WA_FEATURE_META = {k: (lbl, dflt) for (k, lbl, dflt) in _S2WA_FEATURES}


def _fnm_on(key):
  meta = _S2WA_FEATURE_META.get(key)
  if not meta:
    return True
  # backward compatibility: this feature used to be stored as srv2manual
  if key == "srv3manual":
    legacy = str(get_setting("fn_srv2manual", "") or "").strip()
    current = str(get_setting("fn_srv3manual", "") or "").strip()
    if legacy and not current:
      return legacy.lower() == "on"
  return str(get_setting("fn_" + key, "on" if meta[1] else "off")).lower() == "on"


def _fnm_set(key, enabled):
  set_setting("fn_" + key, "on" if enabled else "off")


def _fnm_toggle(key):
  nv = not _fnm_on(key)
  _fnm_set(key, nv)
  return nv


async def _fnm_menu(event, uid):
  if not is_admin(uid):
    await _s2wa_answer(event, "Admin only", alert=True)
    return
  on_count = sum(1 for k, _l, _d in _S2WA_FEATURES if _fnm_on(k))
  lines = [
    "<b>Function Management</b>",
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
    "Total: <b>%s</b> \u00b7 ON: <b>%s</b> \u00b7 OFF: <b>%s</b>"
    % (len(_S2WA_FEATURES), on_count, len(_S2WA_FEATURES) - on_count),
    "",
    "Tap a feature to switch it ON or OFF.",
    "When a feature is OFF its button is <b>hidden</b> from the store.",
  ]
  rows = []
  for k, lbl, _d in _S2WA_FEATURES:
    state = _fnm_on(k)
    rows.append([Button.inline("%s \u2014 %s" % (lbl, "ON" if state else "OFF"),
                               "fnmgmt_t:%s" % k)])
  rows.append([Button.inline("Back to Admin", "fnmgmt_back")])
  await _s2wa_send(event, "\n".join(lines), buttons=rows)


async def _fnm_toggle_and_refresh(event, uid, key):
  if not is_admin(uid):
    await _s2wa_answer(event, "Admin only", alert=True)
    return
  if key not in _S2WA_FEATURE_META:
    await _s2wa_answer(event, "Unknown feature", alert=True)
    return
  nv = _fnm_toggle(key)
  await _s2wa_answer(event, "%s: %s" % (_S2WA_FEATURE_META[key][0], "ON \u2705" if nv else "OFF \u274c"), alert=True)
  await _fnm_menu(event, uid)


# ---- dispatchers (called from the main callback router) --------------------
async def _s2wa_dispatch(event, data):
  uid = event.sender_id
  if not _s2wa_enabled() and not is_admin(uid):
    await _s2wa_answer(event, "This feature is currently disabled.", alert=True)
    return
  if not _s2wa_api_key():
    if is_admin(uid):
      await _s2wa_home(event, uid)
    else:
      await _s2wa_answer(event, "Server 2 is not available right now.", alert=True)
    return
  if data == "s2wa_home":
    await _s2wa_home(event, uid)
  elif data == "s2wa_store":
    await store_servers_menu(event)
  elif data == "s2wa_countries":
    await _s2wa_countries_screen(event, uid, 0)
  elif data.startswith("s2wa_countries:"):
    await _s2wa_countries_screen(event, uid, int(data.split(":", 1)[1]))
  elif data.startswith("s2wa_c:"):
    await _s2wa_country_detail(event, uid, int(data.split(":", 1)[1]))
  elif data.startswith("s2wa_buy:"):
    await _s2wa_buy(event, uid, int(data.split(":", 1)[1]))
  elif data.startswith("s2wa_code:"):
    await _s2wa_poll_code(event, uid, data.split(":", 1)[1])
  elif data.startswith("s2wa_retry:"):
    await _s2wa_retry(event, uid, data.split(":", 1)[1])
  elif data.startswith("s2wa_cancel:"):
    await _s2wa_cancel(event, uid, data.split(":", 1)[1])
  elif data == "s2wa_orders":
    await orders_history_handler(event, is_callback=True)
  elif data == "s2wa_balance":
    await _s2wa_balance(event, uid)
  elif data == "s2wa_noop":
    await _s2wa_answer(event)
  else:
    await _s2wa_answer(event)


async def _fnm_dispatch(event, data):
  uid = event.sender_id
  if data == "fnmgmt_menu":
    await _fnm_menu(event, uid)
  elif data.startswith("fnmgmt_t:"):
    await _fnm_toggle_and_refresh(event, uid, data.split(":", 1)[1])
  elif data == "fnmgmt_back":
    await admin_panel_handler(event)
  else:
    await _s2wa_answer(event)


# ---- admin commands --------------------------------------------------------
@bot.on(events.NewMessage(pattern=r"(?i)^/(s2wa_|fn_|s1_secure)(\w*)(?:@\w+)?(?:\s+.*)?$"))
async def _s2wa_admin_commands(event):
  try:
    uid = event.sender_id
    if not uid or not is_admin(uid):
      return
    text = (event.raw_text or "").strip()
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/s2wa_key":
      if not arg:
        await event.reply("Current key: <code>%s</code>\nUsage: /s2wa_key &lt;key&gt;" % (_s2wa_api_key() or "(none)"))
        return
      set_setting(_S2WA_K_KEY, arg)
      _S2WA_CACHE["countries"] = (0, None)
      _S2WA_CACHE["prices"] = {}
      await event.reply("\u2705 Server 2 API key saved.")
    elif cmd == "/s2wa_margin":
      try:
        set_setting(_S2WA_K_MARGIN, float(arg))
        await event.reply("\u2705 Margin set to %s%%" % arg)
      except Exception:
        await event.reply("Current margin: %s%%\nUsage: /s2wa_margin 25" % _s2wa_margin())
    elif cmd == "/s2wa_service":
      if arg:
        set_setting(_S2WA_K_SERVICE, arg)
        _S2WA_CACHE["prices"] = {}
        await event.reply("\u2705 Service code set to <code>%s</code>" % arg)
      else:
        await event.reply("Current service: <code>%s</code>\nUsage: /s2wa_service wa" % _s2wa_service())
    elif cmd == "/s2wa_toggle":
      cur_on = str(get_setting(_S2WA_K_ENABLED, "on")).lower() == "on"
      set_setting(_S2WA_K_ENABLED, "off" if cur_on else "on")
      await event.reply("\u2705 Server 2 %s." % ("disabled" if cur_on else "enabled"))
    elif cmd == "/s1_secure":
      if arg.lower() in ("others", "all", "off"):
        set_setting("s1_secure_mode", arg.lower())
        await event.reply("\u2705 Server 1 session mode set to <b>%s</b>." % arg.lower())
      else:
        await event.reply(
          "Current mode: <b>%s</b>\n\nUsage: <code>/s1_secure others|all|off</code>\n"
          "\u2022 <b>others</b> \u2014 kill other sessions after buy, bot session after code\n"
          "\u2022 <b>all</b> \u2014 kill everything right after buy\n"
          "\u2022 <b>off</b> \u2014 do nothing" % _s1_secure_mode())
    elif cmd == "/s2wa_balance":
      try:
        bal = await asyncio.to_thread(_S2waTiger(_s2wa_api_key()).balance)
        await event.reply("Provider balance: $%.4f" % bal)
      except Exception as ex:
        await event.reply("\u274c %s" % ex)
    elif cmd == "/fn_list":
      lines = ["<b>Features</b>"]
      for k, lbl, _d in _S2WA_FEATURES:
        lines.append("%s <code>%s</code> \u2014 %s" % ("\U0001F7E2" if _fnm_on(k) else "\U0001F534", k, lbl))
      await event.reply("\n".join(lines))
    elif cmd in ("/fn_on", "/fn_off"):
      if arg not in _S2WA_FEATURE_META:
        await event.reply("Usage: %s &lt;key&gt;\nKeys: %s" % (cmd, ", ".join(k for k, _l, _d in _S2WA_FEATURES)))
        return
      _fnm_set(arg, cmd == "/fn_on")
      await event.reply("%s -> %s" % (_S2WA_FEATURE_META[arg][0], "ON" if cmd == "/fn_on" else "OFF"))
  except Exception as ex:
    logger.warning("s2wa admin command error: %s", ex)


try:
  _s2wa_ensure_table()
except Exception as _s2wa_ex:
  logger.warning("s2wa table init failed: %s", _s2wa_ex)


async def main():
  try:
    if not get_setting('selling_logs_link', '').strip():
      _lnk = await refresh_selling_logs_link()
      if _lnk:
        logger.info("Selling Logs link generated automatically: %s", _lnk)
  except Exception as _ex:
    logger.warning("Selling Logs link auto-generation skipped: %s", _ex)
  print("BOT STARTED SUCCESSFULLY")
  await bot.run_until_disconnected()

if __name__ == '__main__':
  bot.start(bot_token=BOT_TOKEN)
  loop = asyncio.get_event_loop()
  loop.run_until_complete(main())