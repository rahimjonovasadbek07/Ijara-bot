#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║     🏠 UZB IJARA BOTI — ULTRA PRO v2.0               ║
║━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━║
║  ✅ E'lon joylash (foto galereya)                    ║
║  ✅ Qidirish (viloyat, narx, xona soni)              ║
║  ✅ Manzil (Google Maps havolasi)                    ║
║  ✅ Ichki chat (to'g'ridan-to'g'ri xabar)            ║
║  ✅ Telefonsiz bog'lanish (bot orqali)               ║
║  ✅ Referal tizim (do'st taklif)                     ║
║  ✅ Statistika (eng ko'p qidirilgan)                 ║
║  ✅ Premium e'lon, narx formatlash                   ║
║  ✅ Bildirishnoma, reyting, sharhlar                 ║
║  ✅ Admin panel + moderatsiya                        ║
╚══════════════════════════════════════════════════════╝
"""

import os, re, sqlite3, logging, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import date, datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ╔══════════════════════════════════════╗
# ║           SOZLAMALAR                 ║
# ╚══════════════════════════════════════╝
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8639857905:AAHSavB78MZvX2zt03rmm5UJ_AwJNUzBp94")
ADMIN_IDS      = list(map(int, os.getenv("ADMIN_IDS", "8378370254").split(",")))
BOT_USERNAME   = os.getenv("BOT_USERNAME", "uzijara_bot")
PAYME_NUMBER   = os.getenv("PAYME_NUMBER", "9860350145446075")
CLICK_NUMBER   = os.getenv("CLICK_NUMBER", "9860350145446075")
CHANNEL_ID     = os.getenv("CHANNEL_ID", "")

PREMIUM_PRICE  = 20_000
FREE_ELONLAR   = 3
REFERRAL_BONUS = 5   # 5 do'st = 1 oy premium

# Conversation states
(ELON_TUR, ELON_VILOYAT, ELON_SHAHAR, ELON_XONA, ELON_QAVAT,
 ELON_MAYDON, ELON_NARX, ELON_TAVSIF, ELON_TEL, ELON_FOTO, ELON_MANZIL,
 QIDIRUV_VILOYAT, QIDIRUV_TUR, QIDIRUV_NARX, QIDIRUV_XONA,
 SHARH_MATN, CHAT_XABAR) = range(17)

VILOYATLAR = [
    "🏙️ Toshkent shahri", "🌆 Toshkent viloyati", "🏔️ Andijon",
    "🌿 Farg'ona", "⛰️ Namangan", "🏛️ Samarqand", "🌾 Buxoro",
    "🏜️ Navoiy", "🌊 Xorazm", "🏝️ Qashqadaryo", "🌄 Surxondaryo",
    "🌱 Sirdaryo", "🏞️ Jizzax", "❄️ Qoraqalpog'iston"
]

MULK_TURLARI = ["🏢 Kvartira", "🏠 Uy", "🛏️ Xona", "🏪 Ofis/savdo"]
XONA_SONI    = ["1 xona", "2 xona", "3 xona", "4+ xona", "Farqi yo'q"]
NARX_ORALIQ  = ["100K gacha", "100-300K", "300-500K", "500K-1M", "1M+", "Farqi yo'q"]

# ╔══════════════════════════════════════╗
# ║           DATABASE                   ║
# ╚══════════════════════════════════════╝
def init_db():
    with sqlite3.connect("ijara.db") as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY,
            username    TEXT,
            name        TEXT,
            phone       TEXT,
            elon_count  INTEGER DEFAULT 0,
            is_premium  INTEGER DEFAULT 0,
            premium_end TEXT,
            joined      TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS elonlar (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            tur         TEXT,
            viloyat     TEXT,
            shahar      TEXT,
            xona        TEXT,
            qavat       TEXT,
            maydon      TEXT,
            narx        TEXT,
            tavsif      TEXT,
            telefon     TEXT,
            foto_ids    TEXT,
            is_premium  INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'pending',
            ko_rishlar  INTEGER DEFAULT 0,
            manzil      TEXT,
            created     TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sharhlar (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            elon_id   INTEGER,
            user_id   INTEGER,
            ball      INTEGER,
            matn      TEXT,
            created   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            elon_id   INTEGER,
            amount    INTEGER,
            method    TEXT,
            status    TEXT DEFAULT 'pending',
            created   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS saqlangan (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            elon_id   INTEGER,
            created   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER UNIQUE,
            viloyat   TEXT DEFAULT 'Barchasi',
            tur       TEXT DEFAULT 'Barchasi',
            created   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            elon_id   INTEGER,
            from_id   INTEGER,
            to_id     INTEGER,
            matn      TEXT,
            is_read   INTEGER DEFAULT 0,
            created   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS referrals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            created     TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS search_stats (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            viloyat   TEXT,
            tur       TEXT,
            created   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

def db():
    return sqlite3.connect("ijara.db")

def reg(uid, username, name):
    with db() as c:
        if not c.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone():
            c.execute("INSERT INTO users (id,username,name) VALUES (?,?,?)",
                      (uid, username or "", name or ""))
            c.commit()

def get_user(uid):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def is_premium(uid):
    with db() as c:
        r = c.execute("SELECT is_premium, premium_end FROM users WHERE id=?", (uid,)).fetchone()
        if r and r[0] and r[1] and r[1] >= str(date.today()):
            return True
        if r and r[0]:
            c.execute("UPDATE users SET is_premium=0 WHERE id=?", (uid,))
            c.commit()
        return False

def give_premium(uid, months=1):
    with db() as c:
        r = c.execute("SELECT premium_end FROM users WHERE id=?", (uid,)).fetchone()
        start = datetime.fromisoformat(r[0]) if r and r[0] and r[0] >= str(date.today()) else datetime.now()
        end = (start + timedelta(days=30*months)).date()
        c.execute("UPDATE users SET is_premium=1, premium_end=? WHERE id=?", (str(end), uid))
        c.commit()
        return str(end)

def fmt_narx(narx_str):
    """Narxni formatlash: 1500000 → 1,500,000"""
    try:
        n = int(re.sub(r'[^\d]', '', str(narx_str)))
        return f"{n:,}".replace(",", " ")
    except:
        return narx_str

def subscribe_notifications(uid, viloyat=None, tur=None):
    with db() as c:
        c.execute("""
            INSERT OR REPLACE INTO notifications (user_id, viloyat, tur)
            VALUES (?,?,?)
        """, (uid, viloyat or "Barchasi", tur or "Barchasi"))
        c.commit()

def unsubscribe_notifications(uid):
    with db() as c:
        c.execute("DELETE FROM notifications WHERE user_id=?", (uid,))
        c.commit()

def get_subscribers(viloyat, tur):
    with db() as c:
        return c.execute("""
            SELECT user_id FROM notifications
            WHERE (viloyat=? OR viloyat='Barchasi')
            AND (tur=? OR tur='Barchasi')
        """, (viloyat, tur)).fetchall()

# ─── REFERAL ───
def reg_referral(referrer_id, referred_id):
    with db() as c:
        if referrer_id == referred_id: return
        if c.execute("SELECT id FROM referrals WHERE referred_id=?", (referred_id,)).fetchone(): return
        c.execute("INSERT INTO referrals (referrer_id,referred_id) VALUES (?,?)", (referrer_id, referred_id))
        c.commit()
        cnt = c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (referrer_id,)).fetchone()[0]
        return cnt

def get_ref_count(uid):
    with db() as c:
        return c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,)).fetchone()[0]

# ─── CHAT ───
def send_chat(elon_id, from_id, to_id, matn):
    with db() as c:
        c.execute("INSERT INTO chat_messages (elon_id,from_id,to_id,matn) VALUES (?,?,?,?)",
                  (elon_id, from_id, to_id, matn))
        c.commit()

def get_chat_history(elon_id, uid1, uid2, limit=20):
    with db() as c:
        msgs = c.execute("""
            SELECT from_id, matn, created FROM chat_messages
            WHERE elon_id=? AND (
                (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
            ) ORDER BY created DESC LIMIT ?
        """, (elon_id, uid1, uid2, uid2, uid1, limit)).fetchall()
        c.execute("""
            UPDATE chat_messages SET is_read=1
            WHERE elon_id=? AND to_id=? AND is_read=0
        """, (elon_id, uid1))
        c.commit()
        return list(reversed(msgs))

def get_unread_count(uid):
    with db() as c:
        return c.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE to_id=? AND is_read=0", (uid,)
        ).fetchone()[0]

def get_my_chats(uid):
    with db() as c:
        return c.execute("""
            SELECT DISTINCT c.elon_id, c.from_id, c.to_id, e.tur, e.viloyat,
                   (SELECT COUNT(*) FROM chat_messages WHERE to_id=? AND elon_id=c.elon_id AND is_read=0)
            FROM chat_messages c
            JOIN elonlar e ON c.elon_id=e.id
            WHERE c.from_id=? OR c.to_id=?
            GROUP BY c.elon_id
            ORDER BY MAX(c.created) DESC LIMIT 10
        """, (uid, uid, uid)).fetchall()

# ─── STATISTIKA ───
def log_search(viloyat, tur):
    with db() as c:
        c.execute("INSERT INTO search_stats (viloyat,tur) VALUES (?,?)", (viloyat or "Barchasi", tur or "Barchasi"))
        c.commit()

def get_top_searches(limit=5):
    with db() as c:
        return c.execute("""
            SELECT viloyat, tur, COUNT(*) as cnt
            FROM search_stats
            WHERE created >= datetime('now', '-30 days')
            GROUP BY viloyat, tur
            ORDER BY cnt DESC LIMIT ?
        """, (limit,)).fetchall()

# ─── MANZIL ───
def save_manzil(elon_id, manzil_text, lat=None, lon=None):
    with db() as c:
        c.execute("UPDATE elonlar SET manzil=? WHERE id=?", (manzil_text, elon_id))
        c.commit()

def elon_ochirish(eid, uid):
    with db() as c:
        r = c.execute("SELECT user_id FROM elonlar WHERE id=?", (eid,)).fetchone()
        if r and (r[0] == uid or uid in ADMIN_IDS):
            c.execute("UPDATE elonlar SET status='deleted' WHERE id=?", (eid,))
            c.commit()
            return True
        return False

def elon_yangilash(eid, uid, narx=None, tavsif=None, telefon=None):
    with db() as c:
        r = c.execute("SELECT user_id FROM elonlar WHERE id=?", (eid,)).fetchone()
        if not r or (r[0] != uid and uid not in ADMIN_IDS):
            return False
        if narx:
            c.execute("UPDATE elonlar SET narx=? WHERE id=?", (narx, eid))
        if tavsif:
            c.execute("UPDATE elonlar SET tavsif=? WHERE id=?", (tavsif, eid))
        if telefon:
            c.execute("UPDATE elonlar SET telefon=? WHERE id=?", (telefon, eid))
        c.commit()
        return True

def elon_qoshish(data: dict):
    with db() as c:
        c.execute("""
            INSERT INTO elonlar
            (user_id,tur,viloyat,shahar,xona,qavat,maydon,narx,tavsif,telefon,foto_ids,is_premium,status,manzil)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["user_id"], data["tur"], data["viloyat"], data["shahar"],
            data["xona"], data.get("qavat","—"), data.get("maydon","—"),
            data["narx"], data["tavsif"], data["telefon"],
            ",".join(data.get("fotolar", [])),
            1 if data.get("premium") else 0,
            "active" if data.get("premium") else "pending",
            data.get("manzil", "")
        ))
        c.execute("UPDATE users SET elon_count=elon_count+1 WHERE id=?", (data["user_id"],))
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def qidirish(viloyat=None, tur=None, narx=None, xona=None, limit=10, offset=0):
    with db() as c:
        q = "SELECT * FROM elonlar WHERE status='active'"
        params = []
        if viloyat and viloyat != "Barchasi":
            q += " AND viloyat=?"; params.append(viloyat)
        if tur and tur != "Barchasi":
            q += " AND tur=?"; params.append(tur)
        if xona and xona != "Farqi yo'q":
            q += " AND xona=?"; params.append(xona)
        q += " ORDER BY is_premium DESC, created DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        return c.execute(q, params).fetchall()

def elon_ko_rish(eid):
    with db() as c:
        c.execute("UPDATE elonlar SET ko_rishlar=ko_rishlar+1 WHERE id=?", (eid,))
        c.commit()
        return c.execute("SELECT * FROM elonlar WHERE id=?", (eid,)).fetchone()

def get_sharhlar(eid):
    with db() as c:
        sharhlar = c.execute(
            "SELECT s.ball, s.matn, u.name, s.created FROM sharhlar s "
            "JOIN users u ON s.user_id=u.id WHERE s.elon_id=? ORDER BY s.created DESC",
            (eid,)
        ).fetchall()
        avg = c.execute("SELECT AVG(ball) FROM sharhlar WHERE elon_id=?", (eid,)).fetchone()[0]
        return sharhlar, round(avg, 1) if avg else 0

def saqlash(uid, eid):
    with db() as c:
        if not c.execute("SELECT id FROM saqlangan WHERE user_id=? AND elon_id=?", (uid, eid)).fetchone():
            c.execute("INSERT INTO saqlangan (user_id,elon_id) VALUES (?,?)", (uid, eid))
            c.commit()
            return True
        return False

def get_saqlangan(uid):
    with db() as c:
        return c.execute(
            "SELECT e.* FROM elonlar e JOIN saqlangan s ON e.id=s.elon_id "
            "WHERE s.user_id=? AND e.status='active' ORDER BY s.created DESC",
            (uid,)
        ).fetchall()

def get_stats():
    with db() as c:
        users   = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        elonlar = c.execute("SELECT COUNT(*) FROM elonlar WHERE status='active'").fetchone()[0]
        pending = c.execute("SELECT COUNT(*) FROM elonlar WHERE status='pending'").fetchone()[0]
        premium = c.execute("SELECT COUNT(*) FROM elonlar WHERE is_premium=1").fetchone()[0]
        pays    = c.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    return users, elonlar, pending, premium, pays

def get_pending_elonlar():
    with db() as c:
        return c.execute(
            "SELECT e.*, u.name, u.username FROM elonlar e JOIN users u ON e.user_id=u.id "
            "WHERE e.status='pending' ORDER BY e.created DESC LIMIT 10"
        ).fetchall()

def tasdiqlash(eid, rad=False):
    with db() as c:
        status = "rejected" if rad else "active"
        r = c.execute("SELECT user_id FROM elonlar WHERE id=?", (eid,)).fetchone()
        c.execute("UPDATE elonlar SET status=? WHERE id=?", (status, eid))
        c.commit()
        return r[0] if r else None

# ╔══════════════════════════════════════╗
# ║        ELON CARD FORMATLASH          ║
# ╚══════════════════════════════════════╝
def format_elon(e, show_full=False):
    sharhlar, avg = get_sharhlar(e[0])
    reyting = f"⭐ {avg}/5 ({len(sharhlar)} sharh)" if sharhlar else "⭐ Sharh yo'q"
    premium_badge = "👑 PREMIUM | " if e[12] else ""
    narx_fmt = fmt_narx(e[8])
    # manzil — index 15 (created 16)
    manzil = e[15] if len(e) > 15 else ""
    manzil_line = ""
    if manzil:
        if manzil.startswith("http"):
            manzil_line = f"🗺️ [Xaritada ko'rish]({manzil})\n"
        else:
            maps_url = f"https://maps.google.com/search/{manzil.replace(' ', '+')}"
            manzil_line = f"🗺️ [{manzil}]({maps_url})\n"
    matn = (
        f"{premium_badge}🏠 *{e[2]} — {e[3]}, {e[4]}*\n"
        f"{'━'*28}\n"
        f"🛏️ Xona: *{e[5]}*  |  🏗️ Qavat: *{e[6]}*\n"
        f"💰 Narx: *{narx_fmt} so'm/oy*\n"
        f"{manzil_line}"
        f"{'━'*28}\n"
    )
    if show_full:
        matn += f"📝 *Tavsif:*\n{e[9]}\n\n"
    matn += (
        f"📞 Tel: `{e[10]}`\n"
        f"{reyting}\n"
        f"👁️ Ko'rishlar: {e[14]}\n"
        f"📅 {e[16][:10] if len(e) > 16 else e[15][:10]}\n"
        f"🆔 E'lon #{e[0]}"
    )
    return matn

def elon_kb(eid, uid, show_full=False, owner_id=None):
    btns = []
    if not show_full:
        btns.append([InlineKeyboardButton("📋 To'liq ma'lumot", callback_data=f"full_{eid}")])
    btns.append([
        InlineKeyboardButton("📞 Telefon", callback_data=f"tel_{eid}"),
        InlineKeyboardButton("💬 Xabar", callback_data=f"msg_{eid}"),
    ])
    btns.append([
        InlineKeyboardButton("🔖 Saqlash", callback_data=f"save_{eid}"),
        InlineKeyboardButton("⭐ Sharh", callback_data=f"sharh_{eid}"),
    ])
    if owner_id == uid or uid in ADMIN_IDS:
        btns.append([
            InlineKeyboardButton("✏️ Yangilash", callback_data=f"update_{eid}"),
            InlineKeyboardButton("🗑️ O'chirish", callback_data=f"delete_{eid}"),
        ])
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(btns)

# ╔══════════════════════════════════════╗
# ║           KLAVIATURA                 ║
# ╚══════════════════════════════════════╝
def main_kb(uid, unread=0):
    chat_label = f"💬 Xabarlar 🔴{unread}" if unread else "💬 Xabarlar"
    rows = [
        [InlineKeyboardButton("📝 E'lon joylash", callback_data="elon_qosh"),
         InlineKeyboardButton("🔍 Qidirish", callback_data="qidirish")],
        [InlineKeyboardButton("🔖 Saqlanganlar", callback_data="saqlangan"),
         InlineKeyboardButton("📋 Mening e'lonlarim", callback_data="mening")],
        [InlineKeyboardButton(chat_label, callback_data="chatlar"),
         InlineKeyboardButton("🔔 Bildirishnoma", callback_data="notif_menu")],
        [InlineKeyboardButton("🎁 Do'st taklif", callback_data="referral"),
         InlineKeyboardButton("📊 Statistika", callback_data="statistika")],
        [InlineKeyboardButton("👑 Premium e'lon", callback_data="premium_info"),
         InlineKeyboardButton("🆘 Yordam", callback_data="yordam")],
    ]
    if uid in ADMIN_IDS:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(rows)

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]])

def viloyat_kb():
    rows = []
    for i in range(0, len(VILOYATLAR), 2):
        row = [InlineKeyboardButton(VILOYATLAR[i], callback_data=f"vil_{VILOYATLAR[i]}")]
        if i+1 < len(VILOYATLAR):
            row.append(InlineKeyboardButton(VILOYATLAR[i+1], callback_data=f"vil_{VILOYATLAR[i+1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

def tur_kb(prefix="tur"):
    rows = [[InlineKeyboardButton(t, callback_data=f"{prefix}_{t}")] for t in MULK_TURLARI]
    if prefix == "q_tur":
        rows.insert(0, [InlineKeyboardButton("🏘️ Barchasi", callback_data=f"{prefix}_Barchasi")])
    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

def xona_kb(prefix="xona"):
    rows = []
    for i in range(0, len(XONA_SONI), 2):
        row = [InlineKeyboardButton(XONA_SONI[i], callback_data=f"{prefix}_{XONA_SONI[i]}")]
        if i+1 < len(XONA_SONI):
            row.append(InlineKeyboardButton(XONA_SONI[i+1], callback_data=f"{prefix}_{XONA_SONI[i+1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def narx_kb(prefix="narx"):
    rows = []
    for i in range(0, len(NARX_ORALIQ), 2):
        row = [InlineKeyboardButton(NARX_ORALIQ[i], callback_data=f"{prefix}_{NARX_ORALIQ[i]}")]
        if i+1 < len(NARX_ORALIQ):
            row.append(InlineKeyboardButton(NARX_ORALIQ[i+1], callback_data=f"{prefix}_{NARX_ORALIQ[i+1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def yulduz_kb(eid):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐1", callback_data=f"ball_{eid}_1"),
        InlineKeyboardButton("⭐2", callback_data=f"ball_{eid}_2"),
        InlineKeyboardButton("⭐3", callback_data=f"ball_{eid}_3"),
        InlineKeyboardButton("⭐4", callback_data=f"ball_{eid}_4"),
        InlineKeyboardButton("⭐5", callback_data=f"ball_{eid}_5"),
    ]])

# ╔══════════════════════════════════════╗
# ║           HANDLERS                   ║
# ╚══════════════════════════════════════╝
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref_id = None
    if ctx.args and ctx.args[0].startswith("ref"):
        try: ref_id = int(ctx.args[0][3:])
        except: pass

    reg(u.id, u.username, u.full_name)
    ctx.user_data.clear()

    # Referal qaydnoma
    if ref_id and ref_id != u.id:
        cnt = reg_referral(ref_id, u.id)
        if cnt and cnt % REFERRAL_BONUS == 0:
            end = give_premium(ref_id, 1)
            try:
                await ctx.bot.send_message(
                    ref_id,
                    f"🎉 *{REFERRAL_BONUS} do'st taklif qildingiz!*\n\n"
                    f"👑 1 oy bepul Premium berildi!\n⏰ Muddat: *{end}* gacha",
                    parse_mode="Markdown"
                )
            except: pass

    unread = get_unread_count(u.id)
    ref_cnt = get_ref_count(u.id)
    elon_cnt = len(qidirish(limit=1000))
    chat_badge = f" 🔴{unread}" if unread else ""

    await update.message.reply_text(
        f"🏠 *UZB IJARA BOTI v2.0*\n\n"
        f"O'zbekistondagi eng qulay ijara platformasi!\n\n"
        f"📊 Faol e'lonlar: *{elon_cnt}* ta\n"
        f"👥 Siz taklif qilgan: *{ref_cnt}* ta do'st\n"
        f"🆓 Bepul e'lon: *{FREE_ELONLAR}* tagacha\n\n"
        f"👇 Nima qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=main_kb(u.id, unread)
    )

# ─── E'LON QOSHISH ───
async def elon_boshlash(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    ctx.user_data["elon"] = {"user_id": uid}
    await q.edit_message_text(
        "📝 *E'lon joylash*\n\nMulk turini tanlang:",
        parse_mode="Markdown",
        reply_markup=tur_kb()
    )
    return ELON_TUR

async def elon_tur(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["elon"]["tur"] = q.data.replace("tur_", "")
    await q.edit_message_text(
        "📍 *Viloyatni tanlang:*",
        parse_mode="Markdown",
        reply_markup=viloyat_kb()
    )
    return ELON_VILOYAT

async def elon_viloyat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["elon"]["viloyat"] = q.data.replace("vil_", "")
    await q.edit_message_text(
        "🏙️ *Shahar/tuman nomini yozing:*\n\n_Misol: Yunusobod, Chilonzor_",
        parse_mode="Markdown",
        reply_markup=back_kb()
    )
    return ELON_SHAHAR

async def elon_shahar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["elon"]["shahar"] = update.message.text.strip()
    await update.message.reply_text(
        "🛏️ *Xona sonini tanlang:*",
        parse_mode="Markdown",
        reply_markup=xona_kb()
    )
    return ELON_XONA

async def elon_xona(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["elon"]["xona"] = q.data.replace("xona_", "")
    await q.edit_message_text(
        "🏗️ *Qavat raqamini yozing:*\n\n_Misol: 3/9_\n_(bilmasangiz: — yozing)_",
        parse_mode="Markdown"
    )
    return ELON_QAVAT

async def elon_qavat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["elon"]["qavat"] = update.message.text.strip()
    ctx.user_data["elon"]["maydon"] = "—"
    await update.message.reply_text(
        "💰 *Oylik narxni yozing (so'mda):*\n\n_Misol: 1500000_",
        parse_mode="Markdown"
    )
    return ELON_NARX

async def elon_narx(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip()
    ctx.user_data["elon"]["narx"] = matn
    await update.message.reply_text(
        "📝 *Tavsif yozing:*\n\n_Nima bor, sharoitlar, qo'shni transport..._",
        parse_mode="Markdown"
    )
    return ELON_TAVSIF

async def elon_tavsif(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["elon"]["tavsif"] = update.message.text.strip()
    await update.message.reply_text(
        "📞 *Telefon raqamingizni yozing:*\n\n_Misol: +998901234567_",
        parse_mode="Markdown"
    )
    return ELON_TEL

async def elon_tel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tel = update.message.text.strip()
    if not re.match(r'^\+?998\d{9}$', tel.replace(" ", "").replace("-", "")):
        await update.message.reply_text("❌ Noto'g'ri raqam! Qaytadan kiriting:\n_Misol: +998901234567_", parse_mode="Markdown")
        return ELON_TEL
    ctx.user_data["elon"]["telefon"] = tel
    await update.message.reply_text(
        "🗺️ *Manzilni yozing:*\n\n"
        "_Misol: Yunusobod 4-mavze, 12-uy_\n\n"
        "Yoki Google Maps havolasini yuboring:\n"
        "_https://maps.google.com/..._\n\n"
        "O'tkazib yuborish uchun — *—* yozing",
        parse_mode="Markdown"
    )
    return ELON_MANZIL

async def elon_manzil(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip()
    ctx.user_data["elon"]["manzil"] = "" if matn == "—" else matn
    ctx.user_data["elon"]["fotolar"] = []
    await update.message.reply_text(
        "📸 *Foto yuboring* (3-5 ta)\n\nHamma fotolarni yuborgach *'Tayyor'* yozing:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Tayyor (fotosiz)", callback_data="foto_skip")
        ]])
    )
    return ELON_FOTO

async def elon_foto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        foto_id = update.message.photo[-1].file_id
        ctx.user_data["elon"].setdefault("fotolar", []).append(foto_id)
        n = len(ctx.user_data["elon"]["fotolar"])
        more_text = "Ko'proq yuboring yoki" if n < 5 else ""
        await update.message.reply_text(
            f"✅ {n} ta foto qabul qilindi.\n{more_text} *Tayyor* yozing.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Tayyor", callback_data="foto_done")
            ]])
        )
        return ELON_FOTO
    elif update.message.text and update.message.text.lower() in ["tayyor", "готово", "done"]:
        return await elon_saqlash(update, ctx)
    return ELON_FOTO

async def elon_foto_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data in ("foto_skip", "foto_done"):
        return await elon_saqlash_cb(update, ctx)

async def elon_saqlash_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    elon = ctx.user_data.get("elon", {})

    # Premium taklif
    await q.edit_message_text(
        f"✅ *E'lon ma'lumotlari tayyor!*\n\n"
        f"🏠 {elon.get('tur')} — {elon.get('viloyat')}\n"
        f"💰 {elon.get('narx')} so'm/oy\n\n"
        f"*E'lon turini tanlang:*\n\n"
        f"🆓 *Bepul* — Admin tasdiqidan keyin chiqadi\n"
        f"👑 *Premium* ({PREMIUM_PRICE:,} so'm) — Darhol + tepada ko'rinadi!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆓 Bepul joylash", callback_data="elon_bepul")],
            [InlineKeyboardButton(f"👑 Premium ({PREMIUM_PRICE:,} so'm)", callback_data="elon_premium")],
        ])
    )
    return ConversationHandler.END

async def elon_saqlash(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    elon = ctx.user_data.get("elon", {})
    await update.message.reply_text(
        f"✅ *E'lon ma'lumotlari tayyor!*\n\n"
        f"🏠 {elon.get('tur')} — {elon.get('viloyat')}\n"
        f"💰 {elon.get('narx')} so'm/oy\n\n"
        f"*E'lon turini tanlang:*\n\n"
        f"🆓 *Bepul* — Admin tasdiqidan keyin chiqadi\n"
        f"👑 *Premium* ({PREMIUM_PRICE:,} so'm) — Darhol + tepada ko'rinadi!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆓 Bepul joylash", callback_data="elon_bepul")],
            [InlineKeyboardButton(f"👑 Premium ({PREMIUM_PRICE:,} so'm)", callback_data="elon_premium")],
        ])
    )
    return ConversationHandler.END

# ─── QIDIRUV ───
async def qidiruv_boshlash(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["qidiruv"] = {}
    await q.edit_message_text(
        "🔍 *Qidiruv*\n\nViloyatni tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏘️ Barchasi", callback_data="q_vil_Barchasi")]] +
            [[InlineKeyboardButton(v, callback_data=f"q_vil_{v}")] for v in VILOYATLAR[0:7:1]] +
            [[InlineKeyboardButton(v, callback_data=f"q_vil_{v}")] for v in VILOYATLAR[7:]] +
            [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
        )
    )
    return QIDIRUV_VILOYAT

async def q_viloyat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["qidiruv"]["viloyat"] = q.data.replace("q_vil_", "")
    await q.edit_message_text(
        "🏠 *Mulk turini tanlang:*",
        parse_mode="Markdown",
        reply_markup=tur_kb("q_tur")
    )
    return QIDIRUV_TUR

async def q_tur(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["qidiruv"]["tur"] = q.data.replace("q_tur_", "")
    await q.edit_message_text(
        "🛏️ *Xona sonini tanlang:*",
        parse_mode="Markdown",
        reply_markup=xona_kb("q_xona")
    )
    return QIDIRUV_XONA

async def q_xona(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["qidiruv"]["xona"] = q.data.replace("q_xona_", "")
    await q.edit_message_text(
        "💰 *Narx oralig'ini tanlang:*",
        parse_mode="Markdown",
        reply_markup=narx_kb("q_narx")
    )
    return QIDIRUV_NARX

async def q_narx(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    qid = ctx.user_data.get("qidiruv", {})
    log_search(qid.get("viloyat"), qid.get("tur"))
    natijalar = qidirish(
        viloyat=qid.get("viloyat"),
        tur=qid.get("tur"),
        xona=qid.get("xona"),
        limit=10
    )
    ctx.user_data["natijalar"] = [e[0] for e in natijalar]
    ctx.user_data["natija_index"] = 0

    if not natijalar:
        await q.edit_message_text(
            "😔 *Hech narsa topilmadi.*\n\nFilter o'zgartirib ko'ring.",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return ConversationHandler.END

    await q.edit_message_text(
        f"✅ *{len(natijalar)} ta e'lon topildi!*",
        parse_mode="Markdown"
    )
    await show_elon(q.message.chat_id, natijalar[0], q.from_user.id, ctx)
    return ConversationHandler.END

async def show_elon(chat_id, elon, uid, ctx):
    eid = elon[0]
    elon_ko_rish(eid)
    matn = format_elon(elon)
    fotolar = [f for f in (elon[11] or "").split(",") if f]
    try:
        if fotolar:
            if len(fotolar) == 1:
                await ctx.bot.send_photo(chat_id, fotolar[0], caption=matn,
                    parse_mode="Markdown", reply_markup=elon_kb(eid, uid))
            else:
                media = [InputMediaPhoto(f) for f in fotolar[:5]]
                await ctx.bot.send_media_group(chat_id, media)
                await ctx.bot.send_message(chat_id, matn, parse_mode="Markdown",
                    reply_markup=elon_kb(eid, uid))
        else:
            await ctx.bot.send_message(chat_id, matn, parse_mode="Markdown",
                reply_markup=elon_kb(eid, uid))
    except Exception as e:
        log.error(f"Elon ko'rsatish xatosi: {e}")
        await ctx.bot.send_message(chat_id, matn, parse_mode="Markdown",
            reply_markup=elon_kb(eid, uid))

# ─── CALLBACK HANDLER ───
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    d   = q.data

    if d == "notif_menu":
        with db() as c:
            sub = c.execute("SELECT viloyat, tur FROM notifications WHERE user_id=?", (uid,)).fetchone()
        if sub:
            await q.edit_message_text(
                f"🔔 *Bildirishnoma yoqilgan!*\n\n"
                f"📍 Viloyat: *{sub[0]}*\n"
                f"🏠 Tur: *{sub[1]}*\n\n"
                f"Yangi e'lon kelganda xabar olasiz!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔕 O'chirish", callback_data="notif_off")],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
                ])
            )
        else:
            await q.edit_message_text(
                "🔔 *Bildirishnoma sozlamalari*\n\nQaysi viloyat bo'yicha xabar olmoqchisiz?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏘️ Barchasi", callback_data="notif_vil_Barchasi")]] +
                    [[InlineKeyboardButton(v, callback_data=f"notif_vil_{v}")] for v in VILOYATLAR] +
                    [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
                )
            )
        return

    if d.startswith("notif_vil_"):
        vil = d.replace("notif_vil_", "")
        ctx.user_data["notif_vil"] = vil
        await q.edit_message_text(
            "🏠 *Mulk turini tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏘️ Barchasi", callback_data="notif_tur_Barchasi")]] +
                [[InlineKeyboardButton(t, callback_data=f"notif_tur_{t}")] for t in MULK_TURLARI] +
                [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
            )
        )
        return

    if d.startswith("notif_tur_"):
        tur = d.replace("notif_tur_", "")
        vil = ctx.user_data.get("notif_vil", "Barchasi")
        subscribe_notifications(uid, vil, tur)
        await q.edit_message_text(
            f"✅ *Bildirishnoma yoqildi!*\n\n"
            f"📍 Viloyat: *{vil}*\n"
            f"🏠 Tur: *{tur}*\n\n"
            f"Yangi e'lon kelganda darhol xabar olasiz! 🔔",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return

    if d == "notif_off":
        unsubscribe_notifications(uid)
        await q.edit_message_text(
            "🔕 *Bildirishnoma o'chirildi.*",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return

    if d == "referral":
        ref_cnt = get_ref_count(uid)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{uid}"
        progress = ref_cnt % REFERRAL_BONUS
        await q.edit_message_text(
            f"🎁 *Do'st taklif qilish*\n\n"
            f"Havolangizni do'stlaringizga yuboring:\n"
            f"`{ref_link}`\n\n"
            f"👥 Jami taklif qilgansiz: *{ref_cnt}* do'st\n"
            f"🎯 Har *{REFERRAL_BONUS}* do'st = 👑 1 oy bepul Premium!\n"
            f"📈 Hozirgi progress: *{progress}/{REFERRAL_BONUS}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Do'stlarga yuborish", switch_inline_query=f"Ijara botiga qo'shiling! {ref_link}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
            ])
        )
        return

    if d == "statistika":
        top = get_top_searches()
        matn = "📊 *So'nggi 30 kundagi qidirishlar:*\n\n"
        if top:
            for i, s in enumerate(top, 1):
                matn += f"{i}. {s[0]} — {s[1]}: *{s[2]}* marta\n"
        else:
            matn += "_Hali qidiruv yo'q_\n"
        with db() as c:
            total_e = c.execute("SELECT COUNT(*) FROM elonlar WHERE status='active'").fetchone()[0]
            total_u = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_p = c.execute("SELECT COUNT(*) FROM elonlar WHERE is_premium=1 AND status='active'").fetchone()[0]
        matn += (
            f"\n{'━'*20}\n"
            f"🏠 Faol e'lonlar: *{total_e}*\n"
            f"👑 Premium: *{total_p}*\n"
            f"👥 Foydalanuvchilar: *{total_u}*"
        )
        await q.edit_message_text(matn, parse_mode="Markdown", reply_markup=back_kb())
        return

    if d == "chatlar":
        chats = get_my_chats(uid)
        if not chats:
            await q.edit_message_text(
                "💬 *Xabarlar yo'q.*\n\nE'lon egasiga xabar yuborish uchun e'lonni oching → 💬 Xabar.",
                parse_mode="Markdown", reply_markup=back_kb()
            )
            return
        kb_rows = []
        for ch in chats:
            elon_id  = ch[0]
            other_id = ch[2] if ch[1] == uid else ch[1]
            unread_n = ch[5]
            badge    = f" 🔴{unread_n}" if unread_n else ""
            kb_rows.append([InlineKeyboardButton(
                f"🏠 E'lon #{elon_id} — {ch[3]}{badge}",
                callback_data=f"chat_open_{elon_id}_{other_id}"
            )])
        kb_rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
        await q.edit_message_text(
            f"💬 *{len(chats)} ta suhbat:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb_rows)
        )
        return

    if d.startswith("chat_open_"):
        parts    = d.split("_")
        elon_id  = int(parts[2])
        other_id = int(parts[3])
        history  = get_chat_history(elon_id, uid, other_id)
        matn = f"💬 *E'lon #{elon_id} — Suhbat:*\n{'━'*25}\n"
        if history:
            for msg in history:
                who = "✉️ Siz" if msg[0] == uid else "🏠 Egasi"
                matn += f"{who} [{msg[2][11:16]}]: {msg[1]}\n"
        else:
            matn += "_Hali xabar yo'q_\n"
        ctx.user_data["chat_elon_id"]  = elon_id
        ctx.user_data["chat_other_id"] = other_id
        ctx.user_data["in_chat"]       = True
        await q.edit_message_text(
            matn + "\n✏️ *Javob yozing:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Chatlardan chiqish", callback_data="chatlar")
            ]])
        )
        return

    if d.startswith("msg_"):
        eid      = int(d.split("_")[1])
        elon     = elon_ko_rish(eid)
        if not elon:
            await q.answer("❌ E'lon topilmadi!", show_alert=True); return
        owner_id = elon[1]
        if owner_id == uid:
            await q.answer("Bu sizning e'loningiz!", show_alert=True); return
        ctx.user_data["chat_elon_id"]  = eid
        ctx.user_data["chat_other_id"] = owner_id
        ctx.user_data["in_chat"]       = True
        await q.message.reply_text(
            f"💬 *E'lon #{eid} egasiga xabar yozing:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor qilish", callback_data="back_main")
            ]])
        )
        return

    if d.startswith("delete_"):
        eid = int(d.split("_")[1])
        await q.edit_message_text(
            f"🗑️ *E'lon #{eid} ni o'chirishni tasdiqlaysizmi?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_del_{eid}"),
                 InlineKeyboardButton("❌ Yo'q", callback_data="back_main")],
            ])
        )
        return

    if d.startswith("confirm_del_"):
        eid = int(d.split("_")[2])
        ok = elon_ochirish(eid, uid)
        if ok:
            await q.edit_message_text(
                f"✅ *E'lon #{eid} o'chirildi!*",
                parse_mode="Markdown", reply_markup=main_kb(uid)
            )
        else:
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    if d.startswith("update_"):
        eid = int(d.split("_")[1])
        ctx.user_data["update_eid"] = eid
        await q.edit_message_text(
            f"✏️ *E'lon #{eid} ni yangilash*\n\nNimani o'zgartirmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Narx", callback_data=f"upd_narx_{eid}"),
                 InlineKeyboardButton("📝 Tavsif", callback_data=f"upd_tavsif_{eid}")],
                [InlineKeyboardButton("📞 Telefon", callback_data=f"upd_tel_{eid}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
            ])
        )
        return

    if d.startswith("upd_narx_"):
        eid = int(d.split("_")[2])
        ctx.user_data["update_eid"] = eid
        ctx.user_data["update_field"] = "narx"
        await q.edit_message_text(
            "💰 *Yangi narxni yozing (so'mda):*\n\n_Misol: 1500000_",
            parse_mode="Markdown"
        )
        return

    if d.startswith("upd_tavsif_"):
        eid = int(d.split("_")[2])
        ctx.user_data["update_eid"] = eid
        ctx.user_data["update_field"] = "tavsif"
        await q.edit_message_text(
            "📝 *Yangi tavsifni yozing:*",
            parse_mode="Markdown"
        )
        return

    if d.startswith("upd_tel_"):
        eid = int(d.split("_")[2])
        ctx.user_data["update_eid"] = eid
        ctx.user_data["update_field"] = "telefon"
        await q.edit_message_text(
            "📞 *Yangi telefon raqamini yozing:*",
            parse_mode="Markdown"
        )
        return

    if d == "back_main":
        ctx.user_data.clear()
        unread = get_unread_count(uid)
        await q.edit_message_text(
            "🏠 *UZB IJARA BOTI v2.0*\n\n👇 Nima qilmoqchisiz?",
            parse_mode="Markdown", reply_markup=main_kb(uid, unread)
        )
        return

    if d == "elon_bepul":
        elon = ctx.user_data.get("elon", {})
        if not elon:
            await q.edit_message_text("❌ Ma'lumot topilmadi. /start bosing.", reply_markup=back_kb())
            return
        eid = elon_qoshish(elon)
        # Admin ga xabar
        for aid in ADMIN_IDS:
            try:
                u_info = await ctx.bot.get_chat(uid)
                uname = f"@{u_info.username}" if u_info.username else u_info.full_name
                await ctx.bot.send_message(
                    aid,
                    f"📋 *Yangi e'lon tasdiq kutmoqda!*\n\n"
                    f"👤 {uname} (`{uid}`)\n"
                    f"🏠 {elon.get('tur')} — {elon.get('viloyat')}\n"
                    f"💰 {elon.get('narx')} so'm/oy\n\n"
                    f"✅ `/tasdiqlash {eid}`\n"
                    f"❌ `/rad {eid}`",
                    parse_mode="Markdown"
                )
            except: pass
        await q.edit_message_text(
            f"✅ *E'lon yuborildi!*\n\n"
            f"🆔 E'lon #{eid}\n"
            f"⏳ Admin ko'rib chiqadi (odatda 1-2 soat)\n\n"
            f"👑 *Premium e'lon* bilan tezroq ko'rinsiz!",
            parse_mode="Markdown", reply_markup=main_kb(uid)
        )
        ctx.user_data.clear()
        return

    if d == "elon_premium":
        elon = ctx.user_data.get("elon", {})
        if not elon:
            await q.edit_message_text("❌ Ma'lumot topilmadi.", reply_markup=back_kb())
            return
        elon["premium"] = True
        ctx.user_data["elon"] = elon
        await q.edit_message_text(
            f"👑 *PREMIUM E'LON*\n\n"
            f"✅ Darhol faollashadi\n"
            f"✅ Qidiruv tepasida ko'rinadi\n"
            f"✅ Ko'proq mijoz\n\n"
            f"💰 *Narx: {PREMIUM_PRICE:,} so'm*\n\n"
            f"To'lov usulini tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Payme", callback_data="epay_payme"),
                 InlineKeyboardButton("💳 Click", callback_data="epay_click")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
            ])
        )
        return

    if d in ("epay_payme", "epay_click"):
        method = "Payme" if d == "epay_payme" else "Click"
        number = PAYME_NUMBER if d == "epay_payme" else CLICK_NUMBER
        admin_user = ""
        for aid in ADMIN_IDS:
            try:
                adm = await ctx.bot.get_chat(aid)
                admin_user = adm.username or str(aid)
                break
            except: pass
        await q.edit_message_text(
            f"💳 *{method} orqali to'lov*\n\n"
            f"💰 Summa: *{PREMIUM_PRICE:,} so'm*\n\n"
            f"📲 Quyidagi raqamga o'tkazing:\n`{number}`\n\n"
            f"📝 Izohga yozing: `Premium {uid}`\n\n"
            f"📸 Chekni @{admin_user} ga yuboring!\n"
            f"✅ Admin tasdiqlaydi va e'lon darhol chiqadi.",
            parse_mode="Markdown",
            reply_markup=back_kb()
        )
        # Adminga xabar
        for aid in ADMIN_IDS:
            try:
                elon = ctx.user_data.get("elon", {})
                await ctx.bot.send_message(
                    aid,
                    f"💳 *Premium e'lon to'lovi!*\n\n"
                    f"👤 `{uid}`\n"
                    f"🏠 {elon.get('tur','?')} — {elon.get('viloyat','?')}\n"
                    f"💰 Summa: *{PREMIUM_PRICE:,} so'm* | 📲 {method}\n\n"
                    f"✅ Tasdiqlash: `/premium_elon {uid}`",
                    parse_mode="Markdown"
                )
            except: pass
        return

    if d == "saqlangan":
        saqlanganlar = get_saqlangan(uid)
        if not saqlanganlar:
            await q.edit_message_text(
                "🔖 *Saqlanganlar bo'sh.*\n\nE'lonlarni ko'rib ♥️ saqlang!",
                parse_mode="Markdown", reply_markup=back_kb()
            )
            return
        await q.edit_message_text(
            f"🔖 *{len(saqlanganlar)} ta saqlangan e'lon:*",
            parse_mode="Markdown"
        )
        for elon in saqlanganlar[:5]:
            await show_elon(q.message.chat_id, elon, uid, ctx)
        return

    if d == "mening":
        with db() as c:
            elonlar = c.execute(
                "SELECT id,tur,viloyat,narx,status,is_premium,ko_rishlar FROM elonlar "
                "WHERE user_id=? ORDER BY created DESC LIMIT 10", (uid,)
            ).fetchall()
        if not elonlar:
            await q.edit_message_text(
                "📋 *Sizda hali e'lon yo'q.*\n\nBirinchi e'loni joylang!",
                parse_mode="Markdown", reply_markup=main_kb(uid)
            )
            return
        matn = "📋 *Sizning e'lonlaringiz:*\n\n"
        for e in elonlar:
            status_icon = "✅" if e[4] == "active" else "⏳" if e[4] == "pending" else "❌"
            premium_icon = "👑" if e[5] else "🆓"
            matn += f"{status_icon} {premium_icon} *{e[1]}* — {e[2]}\n💰 {e[3]} so'm | 👁️ {e[6]} | `#{e[0]}`\n\n"
        await q.edit_message_text(matn, parse_mode="Markdown", reply_markup=back_kb())
        return

    if d == "premium_info":
        await q.edit_message_text(
            f"👑 *PREMIUM E'LON*\n\n"
            f"✅ Qidiruv natijalarida eng tepada\n"
            f"✅ Darhol faollashadi (admin kutilmaydi)\n"
            f"✅ Ko'proq mijoz jalb qiladi\n"
            f"✅ Alohida *Premium* belgisi\n\n"
            f"💰 *Narx: {PREMIUM_PRICE:,} so'm / e'lon*\n\n"
            f"E'lon joylaganingizda Premium tanlang!",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return

    if d == "yordam":
        admin_user = ""
        for aid in ADMIN_IDS:
            try:
                adm = await ctx.bot.get_chat(aid)
                admin_user = adm.username or str(aid)
                break
            except: pass
        await q.edit_message_text(
            f"🆘 *Yordam*\n\n"
            f"👤 Admin: @{admin_user}\n\n"
            f"❓ *Ko'p so'raladigan savollar:*\n\n"
            f"❔ E'lon qancha turadi?\n└ Bepul — {FREE_ELONLAR} tagacha\n└ Premium — {PREMIUM_PRICE:,} so'm\n\n"
            f"❔ E'lon qachon chiqadi?\n└ Bepul: 1-2 soat (admin tasdiqidan keyin)\n└ Premium: darhol\n\n"
            f"❔ Fotolar nechta bo'lishi kerak?\n└ 1-5 ta foto\n\n"
            f"❔ E'lonni qanday o'chiraman?\n└ Adminga xabar yuboring",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return

    # Elon full ko'rish
    if d.startswith("full_"):
        eid = int(d.split("_")[1])
        elon = elon_ko_rish(eid)
        if elon:
            matn = format_elon(elon, show_full=True)
            try:
                await q.edit_message_text(matn, parse_mode="Markdown",
                    reply_markup=elon_kb(eid, uid, show_full=True))
            except:
                await q.message.reply_text(matn, parse_mode="Markdown",
                    reply_markup=elon_kb(eid, uid, show_full=True))
        return

    if d.startswith("tel_"):
        eid = int(d.split("_")[1])
        elon = elon_ko_rish(eid)
        if elon:
            await q.message.reply_text(
                f"📞 *Bog'lanish ma'lumoti:*\n\n"
                f"🏠 {elon[2]} — {elon[3]}\n"
                f"📱 Tel: `{elon[10]}`\n\n"
                f"_Iltimos, ehtiyotkorlik bilan muomala qiling!_",
                parse_mode="Markdown"
            )
        return

    if d.startswith("save_"):
        eid = int(d.split("_")[1])
        ok = saqlash(uid, eid)
        await q.answer("✅ Saqlandi!" if ok else "ℹ️ Avval saqlangan!", show_alert=True)
        return

    if d.startswith("sharh_"):
        eid = int(d.split("_")[1])
        ctx.user_data["sharh_eid"] = eid
        await q.message.reply_text(
            f"⭐ *E'lon #{eid} uchun baho bering:*",
            parse_mode="Markdown",
            reply_markup=yulduz_kb(eid)
        )
        return

    if d.startswith("ball_"):
        parts = d.split("_")
        eid   = int(parts[1])
        ball  = int(parts[2])
        ctx.user_data["sharh_eid"] = eid
        ctx.user_data["sharh_ball"] = ball
        await q.edit_message_text(
            f"⭐ *{ball}/5 ball berdingiz!*\n\nQisqacha sharh yozing (ixtiyoriy):\n_(o'tkazib yuborish uchun — yozing)_",
            parse_mode="Markdown"
        )
        return

    # Admin
    if d == "admin" and uid in ADMIN_IDS:
        users, elonlar, pending, premium, pays = get_stats()
        await q.edit_message_text(
            f"⚙️ *ADMIN PANEL*\n{'━'*25}\n"
            f"👥 Foydalanuvchilar: *{users}*\n"
            f"🏠 Faol e'lonlar: *{elonlar}*\n"
            f"⏳ Tasdiq kutayotgan: *{pending}*\n"
            f"👑 Premium e'lonlar: *{premium}*\n"
            f"💳 To'lov kutayotgan: *{pays}*\n\n"
            f"📌 *Buyruqlar:*\n"
            f"`/tasdiqlash [id]` — E'lonni tasdiqlash\n"
            f"`/rad [id]` — E'lonni rad etish\n"
            f"`/broadcast [matn]` — Hammaga xabar\n"
            f"`/premium_elon [user_id]` — Premium berish",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ Kutayotgan e'lonlar", callback_data="admin_pending")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
            ])
        )
        return

    if d == "admin_pending" and uid in ADMIN_IDS:
        pending = get_pending_elonlar()
        if not pending:
            await q.edit_message_text("✅ Kutayotgan e'lonlar yo'q.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="admin")
                ]]))
            return
        for e in pending[:5]:
            matn = (
                f"⏳ *Tasdiq kutmoqda #{e[0]}*\n"
                f"👤 {e[16]} (@{e[17] or '?'})\n"
                f"🏠 {e[2]} — {e[3]}, {e[4]}\n"
                f"💰 {e[8]} so'm/oy\n"
                f"📞 {e[10]}\n"
                f"📝 {e[9][:100]}..."
            )
            await ctx.bot.send_message(
                uid, matn, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{e[0]}"),
                     InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{e[0]}")],
                ])
            )
        return

    if d.startswith("approve_") and uid in ADMIN_IDS:
        eid = int(d.split("_")[1])
        target = tasdiqlash(eid)
        await q.answer("✅ Tasdiqlandi!", show_alert=True)
        if target:
            try:
                await ctx.bot.send_message(target,
                    f"🎉 *E'longiz tasdiqlandi!*\n\n"
                    f"🏠 E'lon #{eid} endi faol.\n"
                    f"Ko'p mijozlar bog'lansin! 🤝",
                    parse_mode="Markdown"
                )
            except: pass
        # Kanal ga yuborish
        if CHANNEL_ID:
            elon = elon_ko_rish(eid)
            if elon:
                try:
                    await ctx.bot.send_message(
                        CHANNEL_ID,
                        format_elon(elon, show_full=True) + f"\n\n🤖 @{BOT_USERNAME}",
                        parse_mode="Markdown"
                    )
                except: pass
        # 🔔 Obunachilarga bildirishnoma
        elon = elon_ko_rish(eid)
        if elon:
            subscribers = get_subscribers(elon[3], elon[2])
            notif_matn = (
                f"🔔 *Yangi e'lon!*\n\n"
                f"{format_elon(elon)}\n\n"
                f"🤖 @{BOT_USERNAME} da ko'rish"
            )
            for sub in subscribers:
                if sub[0] != target:
                    try:
                        await ctx.bot.send_message(sub[0], notif_matn, parse_mode="Markdown")
                    except: pass
        return

    if d.startswith("reject_") and uid in ADMIN_IDS:
        eid = int(d.split("_")[1])
        target = tasdiqlash(eid, rad=True)
        await q.answer("❌ Rad etildi!", show_alert=True)
        if target:
            try:
                await ctx.bot.send_message(target,
                    f"😔 *E'longiz rad etildi.*\n\n"
                    f"E'lon #{eid} qoidalarga mos kelmadi.\n"
                    f"Yangi e'lon joylashingiz mumkin.",
                    parse_mode="Markdown"
                )
            except: pass
        return

# ─── TEXT HANDLER ───
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    matn = update.message.text.strip()

    # Chat xabar yuborish
    if ctx.user_data.get("in_chat"):
        elon_id  = ctx.user_data.get("chat_elon_id")
        other_id = ctx.user_data.get("chat_other_id")
        if elon_id and other_id:
            send_chat(elon_id, uid, other_id, matn)
            # Qabul qiluvchiga bildirishnoma
            try:
                elon = elon_ko_rish(elon_id)
                await ctx.bot.send_message(
                    other_id,
                    f"💬 *Yangi xabar — E'lon #{elon_id}*\n\n"
                    f"_{matn}_\n\n"
                    f"Javob berish uchun botni oching 👇",
                    parse_mode="Markdown"
                )
            except: pass
            await update.message.reply_text(
                f"✅ *Xabar yuborildi!*\n\n_{matn}_\n\nDavom etish uchun yozing:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 Chatga qaytish", callback_data=f"chat_open_{elon_id}_{other_id}"),
                    InlineKeyboardButton("🏠 Bosh menu", callback_data="back_main"),
                ]])
            )
            ctx.user_data["in_chat"] = False
        return

    # E'lon yangilash
    if ctx.user_data.get("update_field"):
        eid   = ctx.user_data.pop("update_eid", None)
        field = ctx.user_data.pop("update_field")
        if eid:
            kwargs = {field: matn}
            ok = elon_yangilash(eid, uid, **kwargs)
            if ok:
                await update.message.reply_text(
                    f"✅ *E'lon #{eid} yangilandi!*\n\n"
                    f"{'💰 Narx' if field=='narx' else '📝 Tavsif' if field=='tavsif' else '📞 Telefon'}: *{fmt_narx(matn) if field=='narx' else matn}*",
                    parse_mode="Markdown", reply_markup=main_kb(uid)
                )
            else:
                await update.message.reply_text("❌ Ruxsat yo'q!", reply_markup=main_kb(uid))
        return

    # Sharh yozish
    if ctx.user_data.get("sharh_ball"):
        eid  = ctx.user_data.get("sharh_eid")
        ball = ctx.user_data.pop("sharh_ball")
        ctx.user_data.pop("sharh_eid", None)
        with db() as c:
            c.execute("INSERT INTO sharhlar (elon_id,user_id,ball,matn) VALUES (?,?,?,?)",
                      (eid, uid, ball, matn))
            c.commit()
        await update.message.reply_text(
            f"✅ *Sharhingiz qabul qilindi!*\n\n"
            f"⭐ Ball: {ball}/5\n"
            f"📝 {matn}",
            parse_mode="Markdown", reply_markup=main_kb(uid)
        )
        return

    await update.message.reply_text(
        "🏠 *UZB IJARA BOTI*\n\n👇 Nima qilmoqchisiz?",
        parse_mode="Markdown", reply_markup=main_kb(uid)
    )

# ─── ADMIN COMMANDS ───
async def tasdiqlash_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS: return
    try:
        eid = int(ctx.args[0])
        target = tasdiqlash(eid)
        await update.message.reply_text(f"✅ E'lon #{eid} tasdiqlandi!")
        if target:
            elon = elon_ko_rish(eid)
            try:
                await ctx.bot.send_message(target,
                    f"🎉 *E'lon #{eid} tasdiqlandi!*\n\nEndi faol! 🏠",
                    parse_mode="Markdown")
            except: pass
            if CHANNEL_ID and elon:
                try:
                    await ctx.bot.send_message(CHANNEL_ID,
                        format_elon(elon, True) + f"\n\n🤖 @{BOT_USERNAME}",
                        parse_mode="Markdown")
                except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ {e}\nFoydalanish: /tasdiqlash [id]")

async def rad_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS: return
    try:
        eid = int(ctx.args[0])
        target = tasdiqlash(eid, rad=True)
        await update.message.reply_text(f"❌ E'lon #{eid} rad etildi.")
        if target:
            try:
                await ctx.bot.send_message(target,
                    f"😔 E'lon #{eid} rad etildi.", parse_mode="Markdown")
            except: pass
    except Exception as e:
        await update.message.reply_text(f"❌ {e}\nFoydalanish: /rad [id]")

async def premium_elon_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS: return
    try:
        target = int(ctx.args[0])
        elon = ctx.user_data.get("elon", {})
        if elon:
            eid = elon_qoshish({**elon, "premium": True})
            await update.message.reply_text(f"✅ Premium e'lon #{eid} joylandi!")
            try:
                await ctx.bot.send_message(target,
                    f"🎉 *Premium e'loningiz faollashdi!*\n\nE'lon #{eid} tepada ko'rinmoqda! 👑",
                    parse_mode="Markdown")
            except: pass
        else:
            end = give_premium(target, 1)
            await update.message.reply_text(f"✅ {target} ga premium berildi! ({end} gacha)")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS: return
    if not ctx.args:
        await update.message.reply_text("❌ /broadcast [matn]"); return
    xabar = " ".join(ctx.args)
    with db() as c:
        users = c.execute("SELECT id FROM users").fetchall()
    ok = err = 0
    for u in users:
        try:
            await ctx.bot.send_message(u[0], f"📢 *E'lon:*\n\n{xabar}", parse_mode="Markdown")
            ok += 1
        except:
            err += 1
    await update.message.reply_text(f"✅ Yuborildi: {ok}\n❌ Xato: {err}")

# ╔══════════════════════════════════════╗
# ║              MAIN                    ║
# ╚══════════════════════════════════════╝
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def main():
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    log.info("🏠 UZB Ijara Boti ishga tushdi!")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # E'lon qo'shish conversation
    elon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(elon_boshlash, pattern="^elon_qosh$")],
        states={
            ELON_TUR:     [CallbackQueryHandler(elon_tur, pattern="^tur_")],
            ELON_VILOYAT: [CallbackQueryHandler(elon_viloyat, pattern="^vil_")],
            ELON_SHAHAR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_shahar)],
            ELON_XONA:    [CallbackQueryHandler(elon_xona, pattern="^xona_")],
            ELON_QAVAT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_qavat)],
            ELON_NARX:    [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_narx)],
            ELON_TAVSIF:  [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_tavsif)],
            ELON_TEL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_tel)],
            ELON_MANZIL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_manzil)],
            ELON_FOTO:    [
                MessageHandler(filters.PHOTO, elon_foto),
                MessageHandler(filters.TEXT & ~filters.COMMAND, elon_foto),
                CallbackQueryHandler(elon_foto_skip, pattern="^foto_"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    # Qidiruv conversation
    qidiruv_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(qidiruv_boshlash, pattern="^qidirish$")],
        states={
            QIDIRUV_VILOYAT: [CallbackQueryHandler(q_viloyat, pattern="^q_vil_")],
            QIDIRUV_TUR:     [CallbackQueryHandler(q_tur,     pattern="^q_tur_")],
            QIDIRUV_XONA:    [CallbackQueryHandler(q_xona,    pattern="^q_xona_")],
            QIDIRUV_NARX:    [CallbackQueryHandler(q_narx,    pattern="^q_narx_")],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("tasdiqlash",   tasdiqlash_cmd))
    app.add_handler(CommandHandler("rad",          rad_cmd))
    app.add_handler(CommandHandler("broadcast",    broadcast_cmd))
    app.add_handler(CommandHandler("premium_elon", premium_elon_cmd))
    app.add_handler(elon_conv)
    app.add_handler(qidiruv_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("🏠 UZB Ijara Boti ishga tushdi!")
    print("🏠 UZB Ijara Boti ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()