import os
import time
import threading
import urllib.request
from flask import Flask
import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# True = VIP ခဏပိတ်ထားမည် / False = ပုံမှန်အတိုင်း မန်ဘာလက်ခံမည်
VIP_CLOSED = True

@app.route('/')
def home():
    return "VIP Auto Reply Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive_ping():
    while True:
        time.sleep(600)
        url = os.environ.get("RENDER_EXTERNAL_URL")
        if url:
            try:
                urllib.request.urlopen(url, timeout=10)
            except Exception as e:
                print(f"Ping error: {e}")

def get_user_display(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if user.username:
        return f"{full_name} (@{user.username})"
    return full_name

def build_auto_reply(user):
    display_name = get_user_display(user)
    
    # VIP ပိတ်ထားချိန် ပြန်မည့်စာသား
    if VIP_CLOSED:
        return (
            f"မင်္ဂလာပါ {display_name} ခင်ဗျာ 🙏\n\n"
            f"⚠️ လက်ရှိတွင် VIP MEMBER ဝင်ခွင့် ခဏပိတ်ထားပါသည်ဗျ။\n\n"
            f"ပြန်လည်ဖွင့်လှစ်ပေးသည့်အခါ အသိပေးသွားပါမည်ခင်ဗျာ။ ကျေးဇူးတင်ပါတယ်ဗျ 🙏"
        )
    
    # VIP ပြန်ဖွင့်ချိန် ပြန်မည့်စာသား (/open နှိပ်လျှင် ပေါ်မည့်စာ)
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

# Admin သတ်မှတ်ရန်
@bot.message_handler(commands=['admin'])
def set_admin(message):
    global ADMIN_ID
    ADMIN_ID = str(message.chat.id)
    bot.reply_to(
        message,
        f"✅ သင့်အကောင့်ကို Admin အဖြစ် သတ်မှတ်ပြီးပါပြီ!\n"
        f"🆔 Admin ID: {ADMIN_ID}\n\n"
        f"⚙️ အသုံးပြုနိုင်သော Command များ -\n"
        f"• /close - VIP Member ခဏပိတ်ထားရန်\n"
        f"• /open - VIP Member ပြန်ဖွင့်ရန်"
    )

# Telegram ထဲမှ VIP အပိတ်/အဖွင့် လုပ်ရန် Command များ
@bot.message_handler(commands=['close'])
def close_vip(message):
    global VIP_CLOSED
    if not ADMIN_ID or str(message.chat.id) == str(ADMIN_ID):
        VIP_CLOSED = True
        bot.reply_to(message, "🔒 'VIP MEMBER ခဏပိတ်ထားပါသည်' စာသားသို့ ပြောင်းလဲလိုက်ပါပြီ။")

@bot.message_handler(commands=['open'])
def open_vip(message):
    global VIP_CLOSED
    if not ADMIN_ID or str(message.chat.id) == str(ADMIN_ID):
        VIP_CLOSED = False
        bot.reply_to(message, "🔓 VIP Member လက်ခံသည့် စာသားသို့ ပြန်ဖွင့်ပေးလိုက်ပါပြီ။")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = message.from_user
    display_name = get_user_display(user)

    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        bot.send_message(
            ADMIN_ID,
            f"🔔 Customer အသစ် Bot ကို စတင်နှိပ်လိုက်ပါသည်\n"
            f"👤 အမည်: {display_name}\n"
            f"🆔 User ID: {user.id}"
        )

    bot.reply_to(message, build_auto_reply(user))

@bot.message_handler(content_types=['photo', 'document'])
def handle_media(message):
    user = message.from_user
    display_name = get_user_display(user)
    caption = message.caption or "မှတ်ချက်စာသား မပါပါ"

    if ADMIN_ID:
        info_text = (
            f"🧾 ပုံ/ပြေစာ အသစ်ရောက်ရှိလာပါသည်!\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: {user.id}\n"
            f"📝 မှတ်ချက်: {caption}"
        )
        bot.send_message(ADMIN_ID, info_text)
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    bot.reply_to(message, build_auto_reply(user))

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = message.from_user
    display_name = get_user_display(user)

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

    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        info_text = (
            f"💬 Customer ဆီမှ စာအသစ် ရောက်ရှိလာပါသည်\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: {user.id}\n"
            f"✉️ စာသား: {message.text}"
        )
        bot.send_message(ADMIN_ID, info_text)

    bot.reply_to(message, build_auto_reply(user))

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    print("Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    bot.infinity_polling(skip_pending=True)
      
