import os
import time
import threading
import urllib.request
from flask import Flask
import telebot

# Render Environment Variables မှ Key များကို ရယူခြင်း
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ----------------------------------------------------
# ၁။ Bot ၂၄ နာရီ မအိပ်သွားအောင် ထိန်းထားပေးမည့် Web Server နှင့် Auto-Ping စနစ်
# ----------------------------------------------------
@app.route('/')
def home():
    return "VIP Auto Reply Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive_ping():
    """တခြား Website မလိုဘဲ ၁၀ မိနစ်တစ်ကြိမ် Server ကို သူ့ဘာသာ ပြန်နှိုးပေးသည့် စနစ်"""
    while True:
        time.sleep(600)  # ၁၀ မိနစ် (စက္ကန့် ၆၀၀) တစ်ကြိမ် အလုပ်လုပ်မည်
        url = os.environ.get("RENDER_EXTERNAL_URL")
        if url:
            try:
                urllib.request.urlopen(url, timeout=10)
                print("Self-ping successful! Bot is awake.")
            except Exception as e:
                print(f"Ping error: {e}")

# ----------------------------------------------------
# ၂။ Customer အမည်နှင့် Auto Reply စာသား တည်ဆောက်သည့် စနစ်
# ----------------------------------------------------
def get_user_display(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if user.username:
        return f"{full_name} (@{user.username})"
    return full_name

def build_auto_reply(user):
    display_name = get_user_display(user)
    return (
        f"မင်္ဂလာပါ {display_name} ခင်ဗျာ 🙏\n\n"
        f"💎 Member Price - 3,000 Ks\n"
        f"(တစ်ခါသွင်းရုံနဲ့ တစ်သက်စာပါဗျ)\n\n"
        f"💳 ငွေလွှဲရန် အကောင့် -\n"
        f"• KPay Number - 09764199664\n"
        f"• Name - Min Zayar Oo\n\n"
        f"📝 ငွေလွှဲပြေစာပို့ပေးရန်နှင့် ငွေလွှဲမှတ်ချက် (Note) မှာ Telegram Name ထည့်ရေးပေးပါခင်ဗျာ။\n\n"
        f"🔗 အောက်ပါ Group Link မှာ Request (Join) ထားပေးပါ -\n"
        f"https://t.me/+ypuQf6aZRkdjMzk9"
    )

# ----------------------------------------------------
# ၃။ Admin သတ်မှတ်ခြင်း (/admin ရိုက်ပို့ရန်)
# ----------------------------------------------------
@bot.message_handler(commands=['admin'])
def set_admin(message):
    global ADMIN_ID
    ADMIN_ID = str(message.chat.id)
    bot.reply_to(
        message,
        f"✅ သင့်အကောင့်ကို Admin အဖြစ် သတ်မှတ်ပြီးပါပြီ!\n"
        f"🆔 သင့် Admin ID မှာ: {ADMIN_ID}\n\n"
        f"📌 အကြံပြုချက် - Render ၏ Environment တွင် Key: ADMIN_ID နှင့် Value: {ADMIN_ID} ဟု ထည့်ထားပါက Server Restart ကျလျှင်လည်း အမြဲမှတ်မိနေပါမည်။\n\n"
        f"ယခုချိန်မှစ၍ Customer များပို့သမျှ စာနှင့် ငွေလွှဲပြေစာများ သင့်ဆီသို့ တိုက်ရိုက်ရောက်ရှိပါမည်။"
    )

# ----------------------------------------------------
# ၄။ /start နှိပ်လျှင် Auto Reply ပြန်မည့်အပိုင်း
# ----------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = message.from_user
    display_name = get_user_display(user)

    # Admin ဆီသို့ Customer အသစ်ဝင်လာကြောင်း အသိပေးခြင်း
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        bot.send_message(
            ADMIN_ID,
            f"🔔 Customer အသစ် Bot ကို စတင်နှိပ်လိုက်ပါသည်\n"
            f"👤 အမည်: {display_name}\n"
            f"🆔 User ID: {user.id}"
        )

    bot.reply_to(message, build_auto_reply(user))

# ----------------------------------------------------
# ၅။ ငွေလွှဲပြေစာ (Photo / Document) လက်ခံပြီး သင့်ဆီ ပို့ပေးမည့်အပိုင်း
# ----------------------------------------------------
@bot.message_handler(content_types=['photo', 'document'])
def handle_media(message):
    user = message.from_user
    display_name = get_user_display(user)
    caption = message.caption or "မှတ်ချက်စာသား မပါပါ"

    if ADMIN_ID:
        info_text = (
            f"🧾 ငွေလွှဲပြေစာ အသစ်ရောက်ရှိလာပါသည်!\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: {user.id}\n"
            f"📝 မှတ်ချက်: {caption}"
        )
        bot.send_message(ADMIN_ID, info_text)
        # ပြေစာပုံကို Admin ဆီ တိုက်ရိုက် Forward လုပ်ပေးခြင်း
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    # Customer ဆီသို့ ပြေစာလက်ခံရရှိကြောင်း ပြန်ဖြေခြင်း
    bot.reply_to(
        message,
        f"ကျေးဇူးတင်ပါတယ် {display_name} ခင်ဗျာ 🙏\n\n"
        f"✅ လူကြီးမင်း၏ ငွေလွှဲပြေစာကို Admin ထံ ပေးပို့ထားပြီး ဖြစ်ပါသည်။\n"
        f"🔗 အောက်ပါ Group Link တွင် Request (Join) နှိပ်ထားပေးပါ၊ မကြာမီ စစ်ဆေးပြီး Approve လုပ်ပေးပါမည်ဗျ -\n"
        f"https://t.me/+ypuQf6aZRkdjMzk9"
    )

# ----------------------------------------------------
# ၆။ Customer စာပို့လျှင် သင့်ဆီ အကြောင်းကြားပြီး Auto Reply ပြန်မည့်အပိုင်း
# ----------------------------------------------------
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = message.from_user
    display_name = get_user_display(user)

    # Admin က Customer ၏ Forward စာကို Reply ထောက်ပြီး ပြန်ပို့လျှင် Customer ဆီ တိုက်ရိုက်ပို့ပေးခြင်း
    if ADMIN_ID and str(message.chat.id) == str(ADMIN_ID):
        if message.reply_to_message and message.reply_to_message.forward_from:
            target_id = message.reply_to_message.forward_from.id
            try:
                bot.send_message(target_id, f"📩 Admin မှ အကြောင်းကြားစာ -\n\n{message.text}")
                bot.reply_to(message, "✅ Customer ဆီသို့ စာပို့ပြီးပါပြီ။")
                return
            except Exception as e:
                bot.reply_to(message, f"❌ ပို့မရပါ: {e}")
                return

    # Customer ပို့သောစာကို သင့် (Admin) ဆီသို့ လှမ်းပို့ခြင်း
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        info_text = (
            f"💬 Customer ဆီမှ စာအသစ် ရောက်ရှိလာပါသည်\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: {user.id}\n"
            f"✉️ စာသား: {message.text}"
        )
        bot.send_message(ADMIN_ID, info_text)

    # Customer ဆီသို့ သတ်မှတ်ထားသော Auto Reply ချက်ချင်းပြန်ပို့ခြင်း
    bot.reply_to(message, build_auto_reply(user))

# ----------------------------------------------------
# ၇။ စနစ်အားလုံးကို စတင် Run ခြင်း
# ----------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    print("Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    bot.infinity_polling(skip_pending=True)
