import os
import re
import time
import html
import sqlite3
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====================================================
# 1. CONFIGURATION
# ====================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
DB_PATH = os.environ.get("DB_PATH", "bot_data.sqlite3")
TIMEZONE = ZoneInfo(os.environ.get("BOT_TIMEZONE", "Asia/Yangon"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

if not ADMIN_ID or not ADMIN_ID.isdigit():
    raise RuntimeError("Set ADMIN_ID to your Telegram numeric user ID")

ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

VIP_CLOSED = False
VIP_GROUP_ID = None

# ====================================================
# 2. ORIGINAL INFORMATION AND LINKS
# ====================================================

MEMBER_PRICE = "5,000 Ks"

KPAY_NUMBER = "09764199664"
KPAY_NAME = "Min Zayar Oo"

FREE_GROUP_LINK = "https://t.me/translatemoviesken"
VIP_GROUP_LINK = "https://t.me/+9DtdlPnxAKcxZWI1"
BOT_LINK = "http://t.me/translatemoviesken_bot"

# ====================================================
# 3. DATABASE
# ====================================================

def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    global VIP_GROUP_ID
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS member_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_time TEXT NOT NULL,
                event_date TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL
            )
        """)
        row = conn.execute(
            "SELECT value FROM settings WHERE key='vip_group_id'"
        ).fetchone()
        if row:
            VIP_GROUP_ID = int(row["value"])

def save_setting(key, value):
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO settings(key, value)
            VALUES(?, ?)
            ON CONFLICT(key)
            DO UPDATE SET value=excluded.value
        """, (key, str(value)))

def now_local():
    return datetime.now(TIMEZONE)

def is_admin(message):
    return (
        message.from_user is not None
        and message.from_user.id == ADMIN_ID
    )

def admin_only(message):
    if not is_admin(message):
        bot.reply_to(
            message,
            "⛔ ဒီ Command ကို Admin သာ အသုံးပြုနိုင်ပါသည်။"
        )
        return False
    return True

# ====================================================
# 4. WEB SERVER & KEEP ALIVE PING
# ====================================================

@app.route("/")
def home():
    status = "CLOSED" if VIP_CLOSED else "OPEN"
    return f"Translate Movies Ken Bot ({BOT_LINK}) is running 24/7! VIP: {status}"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive_ping():
    while True:
        time.sleep(600)  # ၁၀ မိနစ်တစ်ကြိမ် Server ကိုယ်တိုင် လှမ်းနှိုးမည်
        url = os.environ.get("RENDER_EXTERNAL_URL")
        if url:
            try:
                urllib.request.urlopen(url, timeout=10)
            except Exception as e:
                print(f"Ping error: {e}")

# ====================================================
# 5. CUSTOMER BUTTONS
# ====================================================

def get_user_display(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    safe_name = html.escape(full_name) if full_name else "Customer"
    if user.username:
        return f"{safe_name} (@{html.escape(user.username)})"
    return safe_name

def get_customer_buttons():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_free = InlineKeyboardButton(
        "🎬 ကြည့်ရှုနိုင်တဲ့ ဇာတ်ကားများ (Free Join ရန်)",
        url=FREE_GROUP_LINK
    )
    btn_vip = InlineKeyboardButton(
        "🔗 Privacy (VIP) Group တွင် Request ထားရန်",
        url=VIP_GROUP_LINK
    )
    markup.add(btn_free, btn_vip)
    return markup

def get_admin_action_buttons(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_approve = InlineKeyboardButton(
        "✅ စစ်ဆေးပြီး (Approve)",
        callback_data=f"approve_{user_id}"
    )
    btn_reject = InlineKeyboardButton(
        "⚠️ ပုံမရှင်း/ပြန်ပို့ရန်",
        callback_data=f"reject_{user_id}"
    )
    markup.add(btn_approve, btn_reject)
    return markup

# ====================================================
# 6. AUTO REPLY
# ====================================================

def build_auto_reply(user):
    display_name = get_user_display(user)
    if VIP_CLOSED:
        return (
            f"မင်္ဂလာပါ <b>{display_name}</b> ခင်ဗျာ 🙏\n\n"
            f"⚠️ <b>လက်ရှိတွင် VIP MEMBER ဝင်ခွင့် ခဏပိတ်ထားပါသည်ဗျ။</b>\n\n"
            f"🎬 <b>ကြည့်ရှုနိုင်တဲ့ ဇာတ်ကားများ ဒီ Link ကို Join ပါ (Free) -</b>\n"
            f"{FREE_GROUP_LINK}\n\n"
            f"ပြန်လည်ဖွင့်လှစ်ပေးသည့်အခါ အသိပေးသွားပါမည်ခင်ဗျာ။ ကျေးဇူးတင်ပါတယ်ဗျ 🙏"
        )
    return (
        f"မင်္ဂလာပါ <b>{display_name}</b> ခင်ဗျာ 🙏\n\n"
        f"💎 <b>VIP Member Price - {MEMBER_PRICE}</b>\n"
        f"(ငွေသွင်းပြီးနောက် သတ်မှတ်ထားသော ဇာတ်လမ်းတွဲများကို VIP Group မှာ ကြည့်ရှုနိုင်ပါသည်ဗျ)\n\n"
        f"💳 <b>ငွေလွှဲရန် အကောင့် -</b>\n"
        f"• KPay Number - <code>{KPAY_NUMBER}</code>\n"
        f"• Name - <b>{KPAY_NAME}</b>\n\n"
        f"⚠️ <b>သတိပေးချက် (အရေးကြီးပါသည်) -</b>\n"
        f"၁။ ငွေလွှဲမှတ်ချက် (Note) မှာ မိမိ၏ <b>Telegram Name</b> ထည့်ရေးပေးပါခင်ဗျာ။\n"
        f"၂။ ငွေလွှဲပြီးပါက <b>KPay ငွေလွှဲပြေစာ (Screenshot - SS)</b> ကို ဒီ Bot ({BOT_LINK}) ဆီသို့ မဖြစ်မနေ ပေးပို့ပေးရပါမည်ဗျ။\n\n"
        f"🎬 <b>ကြည့်ရှုနိုင်တဲ့ ဇာတ်ကားများ ဒီ Link ကို Join ပါ (Free) -</b>\n"
        f"{FREE_GROUP_LINK}\n\n"
        f"🔗 <b>Privacy (VIP) Group Link မှာလည်း Request (Join) ထားပေးပါ -</b>\n"
        f"{VIP_GROUP_LINK}"
    )

# ====================================================
# 7. ADMIN PANEL
# ====================================================

@bot.message_handler(commands=["admin"])
def admin_info(message):
    if not admin_only(message):
        return
    status = "🔒 ပိတ်ထားသည် (CLOSED)" if VIP_CLOSED else f"🔓 ဖွင့်ထားသည် (OPEN - {MEMBER_PRICE})"
    bot.reply_to(
        message,
        f"✅ <b>Admin Panel</b>\n"
        f"🆔 Admin ID: <code>{ADMIN_ID}</code>\n"
        f"🤖 Bot Link: {BOT_LINK}\n"
        f"📊 VIP Status: <b>{status}</b>\n"
        f"👥 VIP Group ID: <code>{VIP_GROUP_ID or 'မသတ်မှတ်ရသေးပါ'}</code>\n\n"
        f"<b>အသုံးပြုနိုင်သော Command များ</b>\n"
        f"/open - VIP ဖွင့်ရန်\n"
        f"/close - VIP ပိတ်ရန်\n"
        f"/status - Bot အခြေအနေ\n"
        f"/setvipgroup - VIP Group သတ်မှတ်ရန်\n"
        f"/daily - ယနေ့ ဝင်/ထွက် စာရင်း\n"
        f"/stats - Member စာရင်းအကျဉ်း\n"
        f"/addseries ဇာတ်လမ်းအမည် - ဇာတ်လမ်းတွဲထည့်ရန်\n"
        f"/series - ဇာတ်လမ်းတွဲစာရင်း\n"
        f"/delseries ID - ဇာတ်လမ်းတွဲဖျက်ရန်",
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["open"])
def open_vip(message):
    global VIP_CLOSED
    if not admin_only(message):
        return
    VIP_CLOSED = False
    bot.reply_to(message, f"🔓 VIP Member လက်ခံမှု ဖွင့်ပေးထားပါပြီ ({MEMBER_PRICE})။")

@bot.message_handler(commands=["close"])
def close_vip(message):
    global VIP_CLOSED
    if not admin_only(message):
        return
    VIP_CLOSED = True
    bot.reply_to(message, "🔒 VIP MEMBER ဝင်ခွင့်ကို ခဏပိတ်ထားပါပြီ။")

@bot.message_handler(commands=["status"])
def check_status(message):
    if not admin_only(message):
        return
    status = "🔒 CLOSED" if VIP_CLOSED else "🔓 OPEN"
    count_text = "Group မသတ်မှတ်ရသေးပါ"
    if VIP_GROUP_ID:
        try:
            count_text = str(bot.get_chat_member_count(VIP_GROUP_ID))
        except Exception:
            count_text = "ရယူမရပါ (Bot Admin ဖြစ်/မဖြစ် စစ်ပါ)"
    bot.reply_to(message, f"📊 VIP Status: {status}\n👥 လက်ရှိ VIP Group Member: {count_text}")

@bot.message_handler(commands=["setvipgroup"])
def set_vip_group(message):
    global VIP_GROUP_ID
    if not admin_only(message):
        return
    if message.chat.type not in ("group", "supergroup"):
        bot.reply_to(message, "ဒီ Command ကို VIP Group ထဲမှာပဲ နှိပ်ပေးပါ။")
        return
    VIP_GROUP_ID = message.chat.id
    save_setting("vip_group_id", VIP_GROUP_ID)
    bot.reply_to(message, f"✅ VIP Group ID သိမ်းပြီးပါပြီ။\nGroup ID: <code>{VIP_GROUP_ID}</code>")

# ====================================================
# 8. SERIES MANAGEMENT
# ====================================================

@bot.message_handler(commands=["addseries"])
def add_series(message):
    if not admin_only(message):
        return
    title = (message.text or "").partition(" ")[2].strip()
    if not title:
        bot.reply_to(message, "အသုံးပြုပုံ: <code>/addseries ဇာတ်လမ်းအမည်</code>")
        return
    with db_connect() as conn:
        cur = conn.execute(
            "INSERT INTO series(title, added_by, added_at) VALUES(?, ?, ?)",
            (title, ADMIN_ID, now_local().isoformat(timespec="seconds"))
        )
        series_id = cur.lastrowid
    bot.reply_to(message, f"✅ ဇာတ်လမ်းတွဲ ထည့်ပြီးပါပြီ။\nID: <code>{series_id}</code>\nအမည်: <b>{html.escape(title)}</b>")

@bot.message_handler(commands=["series"])
def list_series(message):
    if not admin_only(message):
        return
    with db_connect() as conn:
        rows = conn.execute("SELECT id, title, added_at FROM series ORDER BY id DESC").fetchall()
    if not rows:
        bot.reply_to(message, "ဇာတ်လမ်းတွဲစာရင်း မရှိသေးပါ။ /addseries ဖြင့် ထည့်နိုင်ပါသည်။")
        return
    lines = ["🎬 <b>ဇာတ်လမ်းတွဲစာရင်း</b>"]
    for row in rows:
        lines.append(f"{row['id']}. {html.escape(row['title'])}")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["delseries"])
def delete_series(message):
    if not admin_only(message):
        return
    raw_id = (message.text or "").partition(" ")[2].strip()
    if not raw_id.isdigit():
        bot.reply_to(message, "အသုံးပြုပုံ: <code>/delseries ID</code>")
        return
    with db_connect() as conn:
        cur = conn.execute("DELETE FROM series WHERE id=?", (int(raw_id),))
    bot.reply_to(message, "🗑️ ဇာတ်လမ်းတွဲ ဖျက်ပြီးပါပြီ။" if cur.rowcount else "အဲဒီ ID ကို မတွေ့ပါ။")

# ====================================================
# 9. VIP GROUP MEMBER TRACKING
# ====================================================

def member_status(status):
    return status in ("member", "administrator", "creator")

@bot.chat_member_handler()
def track_group_members(update):
    chat_id = update.chat.id
    if VIP_GROUP_ID is None or chat_id != VIP_GROUP_ID:
        return
    old_member = member_status(update.old_chat_member.status)
    new_member = member_status(update.new_chat_member.status)
    if old_member == new_member:
        return
    user_id = update.new_chat_member.user.id
    event_type = "join" if new_member else "leave"
    stamp = now_local()
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO member_events(user_id, group_id, event_type, event_time, event_date) VALUES(?, ?, ?, ?, ?)",
            (user_id, chat_id, event_type, stamp.isoformat(timespec="seconds"), stamp.date().isoformat())
        )
    text = (
        f"🟢 <b>VIP Group Member အသစ်ဝင်လာပါသည်</b>\n🆔 User ID: <code>{user_id}</code>\n📅 {stamp.strftime('%Y-%m-%d %H:%M:%S')}"
        if event_type == "join" else
        f"🔴 <b>VIP Group Member တစ်ဦး ထွက်သွားပါသည်</b>\n🆔 User ID: <code>{user_id}</code>\n📅 {stamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    try:
        bot.send_message(ADMIN_ID, text)
    except Exception as exc:
        print(f"Could not notify admin: {exc}")

# ====================================================
# 10. DAILY REPORT & STATS
# ====================================================

@bot.message_handler(commands=["daily"])
def daily_report(message):
    if not admin_only(message):
        return
    today = now_local().date().isoformat()
    with db_connect() as conn:
        joins = conn.execute("SELECT COUNT(*) AS n FROM member_events WHERE event_date=? AND event_type='join'", (today,)).fetchone()["n"]
        leaves = conn.execute("SELECT COUNT(*) AS n FROM member_events WHERE event_date=? AND event_type='leave'", (today,)).fetchone()["n"]
    current = "မရရှိနိုင်ပါ"
    if VIP_GROUP_ID:
        try:
            current = str(bot.get_chat_member_count(VIP_GROUP_ID))
        except Exception:
            current = "ရယူမရပါ"
    bot.reply_to(
        message,
        f"📅 <b>ယနေ့ VIP Group Report ({today})</b>\n"
        f"🟢 ဝင်လာသူ: <b>{joins}</b> ဦး\n"
        f"🔴 ထွက်သွားသူ: <b>{leaves}</b> ဦး\n"
        f"👥 လက်ရှိ Member: <b>{current}</b> ဦး"
    )

@bot.message_handler(commands=["stats"])
def member_stats(message):
    if not admin_only(message):
        return
    with db_connect() as conn:
        total_joins = conn.execute("SELECT COUNT(*) AS n FROM member_events WHERE event_type='join'").fetchone()["n"]
        total_leaves = conn.execute("SELECT COUNT(*) AS n FROM member_events WHERE event_type='leave'").fetchone()["n"]
        series_count = conn.execute("SELECT COUNT(*) AS n FROM series").fetchone()["n"]
    current = "မရရှိနိုင်ပါ"
    if VIP_GROUP_ID:
        try:
            current = str(bot.get_chat_member_count(VIP_GROUP_ID))
        except Exception:
            current = "ရယူမရပါ"
    bot.reply_to(
        message,
        f"📊 <b>VIP Statistics</b>\n"
        f"👥 လက်ရှိ Group Member: <b>{current}</b>\n"
        f"🟢 စုစုပေါင်း ဝင်ရောက်မှုမှတ်တမ်း: <b>{total_joins}</b>\n"
        f"🔴 စုစုပေါင်း ထွက်ခွာမှုမှတ်တမ်း: <b>{total_leaves}</b>\n"
        f"🎬 သိမ်းထားသော ဇာတ်လမ်းတွဲ: <b>{series_count}</b>"
    )

# ====================================================
# 11. PAYMENT APPROVE / REJECT CALLBACKS
# ====================================================

@bot.callback_query_handler(func=lambda call: True)
def handle_admin_callbacks(call):
    if not call.from_user or call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Admin သာ အသုံးပြုနိုင်ပါသည်။", show_alert=True)
        return

    data = call.data or ""
    if not (data.startswith("approve_") or data.startswith("reject_")):
        return

    try:
        target_id = int(data.split("_", 1)[1])
    except ValueError:
        bot.answer_callback_query(call.id, "User ID မမှန်ပါ။", show_alert=True)
        return

    try:
        if data.startswith("approve_"):
            bot.send_message(
                target_id,
                f"🎉 <b>ဂုဏ်ယူပါတယ်ခင်ဗျာ!</b>\n\n"
                f"✅ လူကြီးမင်း၏ KPay ငွေလွှဲပြေစာကို Admin မှ စစ်ဆေးအတည်ပြုပြီးပါပြီ။\n"
                f"🔗 အောက်ပါ Privacy (VIP) Group Link တွင် Request မနှိပ်ရသေးပါက နှိပ်ပေးပါ -\n"
                f"{VIP_GROUP_LINK}",
                reply_markup=get_customer_buttons(),
                disable_web_page_preview=True
            )
            bot.answer_callback_query(call.id, "✅ Customer ဆီ Approve စာပို့ပြီးပါပြီ!")
            bot.edit_message_text(
                (call.message.text or "") + "\n\n✅ [Admin မှ Approve စာပို့ပြီးပါပြီ]",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.send_message(
                target_id,
                "⚠️ <b>Admin မှ အကြောင်းကြားစာ</b>\n\n"
                "လူကြီးမင်း ပေးပို့ထားသော ငွေလွှဲပြေစာ ပုံမရှင်းလင်းပါသဖြင့် (သို့မဟုတ်) အချက်အလက် မပြည့်စုံပါသဖြင့် "
                "<b>KPay ပြေစာ Screenshot (SS) အပြည့်အစုံ</b> ကို ပြန်လည်ပေးပို့ပေးပါခင်ဗျာ 🙏"
            )
            bot.answer_callback_query(call.id, "⚠️ ပြေစာပြန်ပို့ခိုင်းသည့်စာ ပို့ပြီးပါပြီ!")
            bot.edit_message_text(
                (call.message.text or "") + "\n\n⚠️ [ပြေစာပြန်ပို့ရန် အကြောင်းကြားပြီးပါပြီ]",
                call.message.chat.id,
                call.message.message_id
            )
    except Exception as exc:
        bot.answer_callback_query(call.id, "ပို့မရပါ။ Customer က Bot ကို Start လုပ်ထားခြင်း ရှိ/မရှိ စစ်ပါ။", show_alert=True)
        print(f"Approval/rejection error: {exc}")

# ====================================================
# 12. START / HELP & MEDIA / MESSAGE HANDLERS
# ====================================================

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    user = message.from_user
    display_name = get_user_display(user)
    if user.id != ADMIN_ID:
        try:
            bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Customer အသစ် Bot ကို စတင်နှိပ်လိုက်ပါသည်</b>\n"
                f"👤 အမည်: {display_name}\n"
                f"🆔 User ID: <code>{user.id}</code>"
            )
        except Exception as exc:
            print(f"Admin notification error: {exc}")

    bot.reply_to(
        message,
        build_auto_reply(user),
        reply_markup=get_customer_buttons(),
        disable_web_page_preview=True
    )

def extract_target_user_id(reply_msg):
    if reply_msg.forward_from:
        return reply_msg.forward_from.id
    text_to_search = reply_msg.text or reply_msg.caption or ""
    match = re.search(r"User ID:\s*(\d+)", text_to_search)
    if match:
        return int(match.group(1))
    return None

@bot.message_handler(content_types=['photo', 'document'])
def handle_media(message):
    user = message.from_user
    display_name = get_user_display(user)
    caption = html.escape(message.caption) if message.caption else "မှတ်ချက်စာသား မပါပါ"

    if ADMIN_ID and user.id == ADMIN_ID:
        return

    if ADMIN_ID:
        info_text = (
            f"🧾 <b>KPay ငွေလွှဲပြေစာ (SS) အသစ်ရောက်ရှိလာပါသည်!</b>\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: <code>{user.id}</code>\n"
            f"📝 မှတ်ချက်: {caption}\n\n"
            f"💡 <i>(ဤစာကို Reply ထောက်ပြီးလည်း Customer ဆီ တိုက်ရိုက်စာပြန်နိုင်ပါသည်)</i>"
        )
        try:
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(
                ADMIN_ID,
                info_text,
                reply_markup=get_admin_action_buttons(user.id)
            )
        except Exception as exc:
            print(f"Error forwarding media to admin: {exc}")

    bot.reply_to(
        message,
        build_auto_reply(user),
        reply_markup=get_customer_buttons(),
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = message.from_user
    display_name = get_user_display(user)

    if ADMIN_ID and user.id == ADMIN_ID:
        if message.reply_to_message:
            target_id = extract_target_user_id(message.reply_to_message)
            if target_id:
                try:
                    bot.send_message(
                        target_id,
                        f"📩 <b>Admin မှ အကြောင်းကြားစာ -</b>\n\n{html.escape(message.text)}"
                    )
                    bot.reply_to(message, "✅ Customer ဆီသို့ စာပို့ပြီးပါပြီ။")
                    return
                except Exception as e:
                    bot.reply_to(message, f"❌ ပို့မရပါ: {e}")
                    return
        return

    if ADMIN_ID:
        info_text = (
            f"💬 <b>Customer ဆီမှ စာအသစ် ရောက်ရှိလာပါသည်</b>\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: <code>{user.id}</code>\n"
            f"✉️ စာသား: {html.escape(message.text or '')}\n\n"
            f"💡 <i>(ဤစာကို Reply ထောက်ပြီး Customer ဆီ တိုက်ရိုက်စာပြန်နိုင်ပါသည်)</i>"
        )
        try:
            bot.send_message(ADMIN_ID, info_text)
        except Exception as exc:
            print(f"Error notifying admin about text message: {exc}")

    bot.reply_to(
        message,
        build_auto_reply(user),
        reply_markup=get_customer_buttons(),
        disable_web_page_preview=True
    )

# ====================================================
# 13. BOT STARTUP
# ====================================================

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    print("Translate Movies Ken Bot starting polling...")
    while True:
        try:
            bot.remove_webhook()
            time.sleep(2)
            bot.polling(non_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Polling error (restarting in 5s): {e}")
            time.sleep(5)
