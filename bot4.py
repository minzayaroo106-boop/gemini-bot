"""
Best STORY membership bot  (python-telegram-bot v21+)
pip install "python-telegram-bot>=21"

Env vars:
  BOT_TOKEN  - token from @BotFather
  ADMIN_ID   - your own Telegram numeric user id (get from @userinfobot)
  GROUP_ID   - the members group id (e.g. -1001234567890)
              * Bot must be ADMIN in the group (Invite users + Manage topics)
              * Group should be a supergroup with "Topics" enabled
              * Group link must be a "Request admin approval" invite link
"""
import json, logging, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ChatJoinRequestHandler,
                          ContextTypes, filters)

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
ADMIN = int(os.environ["ADMIN_ID"])
GROUP = int(os.environ["GROUP_ID"])
DB_FILE = "db.json"

WELCOME = """မင်္ဂလာပါ BS (@beststoryken) ခင်ဗျာ 🙏

💎 Member Price - 3000 Ks
(တစ်ခါသွင်းရုံနဲ့ တစ်သက်စာပါဗျ)

💳 ငွေလွှဲရန် အကောင့် -
• KPay Number - 09764199664
• Name - Min Zayar Oo

📝 ငွေလွှဲပြေစာ (ဓာတ်ပုံ) ကို ဒီ bot ဆီ ပို့ပေးပါ။ ငွေလွှဲမှတ်ချက် (Note) မှာ Telegram Name ထည့်ရေးပေးပါခင်ဗျာ။

🔗 အောက်ပါ Group Link မှာ Request (Join) ထားပေးပါ -
https://t.me/+ypuQf6aZRkdjMzk9"""


def load():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"approved": [], "pending_join": [], "topic": None}


def save(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f)


DB = load()


# ---------- customers ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME)


async def customer_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Any private message from a non-admin."""
    m, u = update.message, update.effective_user
    if m.photo or m.document:  # looks like a payment receipt
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"ok:{u.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"no:{u.id}"),
        ]])
        await ctx.bot.send_message(
            ADMIN, f"💰 ပြေစာအသစ်\nName: {u.full_name}\n"
                   f"Username: @{u.username or '-'}\nID: {u.id}")
        await m.copy(ADMIN, reply_markup=kb)
        await m.reply_text("ပြေစာ လက်ခံရရှိပါပြီ။ စစ်ဆေးပြီး မကြာမီ အကြောင်းကြားပါမယ်ခင်ဗျာ 🙏")
    else:
        await m.reply_text(WELCOME)


async def on_join_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    r = update.chat_join_request
    if r.chat.id != GROUP:
        return
    uid = r.from_user.id
    if uid in DB["approved"]:
        await r.approve()
        return
    if uid not in DB["pending_join"]:
        DB["pending_join"].append(uid)
        save(DB)
    try:
        await ctx.bot.send_message(r.user_chat_id,
                                   "Join Request ရရှိပါပြီ။ အောက်ပါအတိုင်း ငွေလွှဲပြီး ပြေစာပို့ပေးပါ 👇\n\n" + WELCOME)
    except Exception:
        pass


# ---------- admin ----------
async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN:
        return await q.answer("Admin only", show_alert=True)
    action, uid = q.data.split(":")
    uid = int(uid)
    if action == "ok":
        if uid not in DB["approved"]:
            DB["approved"].append(uid)
        joined = False
        if uid in DB["pending_join"]:
            try:
                await ctx.bot.approve_chat_join_request(GROUP, uid)
                joined = True
            except Exception as e:
                logging.warning(e)
            DB["pending_join"].remove(uid)
        save(DB)
        msg = ("ငွေလွှဲမှု အတည်ပြုပြီးပါပြီ ✅ Group ထဲ ဝင်ခွင့်ပြုပြီးပါပြီ။" if joined else
               "ငွေလွှဲမှု အတည်ပြုပြီးပါပြီ ✅ Group Link မှာ Request (Join) လုပ်ပေးပါ၊ အလိုအလျောက် လက်ခံပေးပါမယ်။")
        await ctx.bot.send_message(uid, msg)
        await q.edit_message_reply_markup(None)
        await q.message.reply_text(f"✅ Approved {uid}")
    else:
        await ctx.bot.send_message(uid, "ပြေစာ မမှန်ကန်ပါ။ ပြန်လည်စစ်ဆေးပြီး ထပ်ပို့ပေးပါခင်ဗျာ။")
        await q.edit_message_reply_markup(None)
        await q.message.reply_text(f"❌ Rejected {uid}")
    await q.answer()


async def new_series(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/series ဇာတ်လမ်းအမည်  -> creates a topic; then send episodes in order."""
    name = " ".join(ctx.args)
    if not name:
        return await update.message.reply_text("အသုံးပြုပုံ: /series ဇာတ်လမ်းအမည်")
    topic = await ctx.bot.create_forum_topic(GROUP, name)
    DB["topic"] = topic.message_thread_id
    save(DB)
    await update.message.reply_text(
        f"📁 '{name}' topic ဖန်တီးပြီးပါပြီ။\nအခုကစပြီး ပို့တဲ့ video/ဖိုင်/စာတွေကို အစဉ်လိုက် တင်ပေးပါမယ်။\nပြီးရင် /done")


async def done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    DB["topic"] = None
    save(DB)
    await update.message.reply_text("✅ ပြီးပါပြီ။ ဆက်တင်ရန် /series အသစ်သုံးပါ။")


async def admin_content(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if DB["topic"] is None:
        return await update.message.reply_text("အရင်ဆုံး /series ဇာတ်လမ်းအမည် နဲ့ စတင်ပါ။")
    await update.message.copy(GROUP, message_thread_id=DB["topic"])


def main():
    app = Application.builder().token(TOKEN).build()
    admin = filters.User(ADMIN) & filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("series", new_series, filters=admin))
    app.add_handler(CommandHandler("done", done, filters=admin))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(ChatJoinRequestHandler(on_join_request))
    app.add_handler(MessageHandler(admin & ~filters.COMMAND, admin_content))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, customer_msg))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
