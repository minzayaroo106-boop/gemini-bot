import os
import threading
from flask import Flask
import telebot
from google import genai

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_ID = os.environ.get("ADMIN_ID")

bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

@app.route('/')
def home():
    return "Auto Reply Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Customer အမည် နှင့် Username ယူသည့် စနစ်
def get_user_display(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if user.username:
        return f"{full_name} (@{user.username})"
    return full_name

# သင်သတ်မှတ်ထားသော Auto Reply စာသားတည်ဆောက်ခြင်း
def build_auto_reply(user):
    display_name = get_user_display(user)
    return (
        f"မင်္ဂလာပါ {display_name} ခင်ဗျာ 🙏\n\n"
        f"💎 Member Price - 3000 Ks\n"
        f"(တစ်ခါသွင်းရုံနဲ့ တစ်သက်စာပါဗျ)\n\n"
        f"💳 ငွေလွှဲရန် အကောင့် -\n"
        f"• KPay Number - 09764199664\n"
        f"• Name - Min Zayar Oo\n\n"
        f"📝 ငွေလွှဲပြေစာပို့ပေးရန်နှင့် ငွေလွှဲမှတ်ချက် (Note) မှာ Telegram Name ထည့်ရေးပေးပါခင်ဗျာ။\n\n"
        f"🔗 အောက်ပါ Group Link မှာ Request (Join) ထားပေးပါ -\n"
        f"https://t.me/+ypuQf6aZRkdjMzk9"
    )

# သင့်ကိုယ်ပိုင်အကောင့်ကို Admin အဖြစ် သတ်မှတ်ရန် (/admin ဟု ပို့ရန်)
@bot.message_handler(commands=['admin'])
def set_admin(message):
    global ADMIN_ID
    ADMIN_ID = str(message.chat.id)
    bot.reply_to(
        message,
        f"✅ သင့်အကောင့်ကို Admin အဖြစ် သတ်မှတ်ပြီးပါပြီ!\n"
        f"သင့် Admin ID မှာ: {ADMIN_ID}\n\n"
        f"တစ်ဖက်လူ ပို့သမျှ စာနှင့် ငွေလွှဲပြေစာများ သင့်ဆီသို့ တိုက်ရိုက်ရောက်ရှိပါမည်။"
    )

# /start နှိပ်လျှင် Auto Reply တန်းပို့ပေးမည့်အပိုင်း
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    reply_msg = build_auto_reply(message.from_user)
    bot.reply_to(message, reply_msg)

# ငွေလွှဲပြေစာ (Photo / Document) ပို့လာလျှင် လက်ခံပြီး သင့်ဆီ Forward လုပ်မည့်အပိုင်း
@bot.message_handler(content_types=['photo', 'document'])
def handle_media(message):
    user = message.from_user
    display_name = get_user_display(user)
    caption = message.caption or "စာသား မပါပါ"

    if ADMIN_ID:
        info_text = (
            f"🧾 ငွေလွှဲပြေစာ အသစ်ရောက်ရှိလာပါသည်!\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"📝 မှတ်ချက်စာ: {caption}"
        )
        bot.send_message(ADMIN_ID, info_text)
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    bot.reply_to(
        message,
        f"ကျေးဇူးတင်ပါတယ် {display_name} ခင်ဗျာ။ 🙏\n"
        f"လူကြီးမင်း၏ ငွေလွှဲပြေစာကို Admin ထံ ပေးပို့ထားပြီး ဖြစ်ပါသည်။\n"
        f"အောက်ပါ Group Link တွင် Request ထားပေးပါ၊ မကြာမီ စစ်ဆေးပြီး Approve လုပ်ပေးပါမည်ဗျ -\n"
        f"https://t.me/+ypuQf6aZRkdjMzk9"
    )

# Customer စာပို့လိုက်တိုင်း သင့်ဆီ အကြောင်းကြားပြီး Auto Reply ပြန်မည့်အပိုင်း
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = message.from_user
    display_name = get_user_display(user)

    # ၁။ Customer ပို့သောစာကို သင့်ဆီသို့ လှမ်းပို့ခြင်း
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        info_text = (
            f"💬 Customer ဆီမှ စာအသစ် ရောက်ရှိလာပါသည်\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"✉️ စာသား: {message.text}"
        )
        bot.send_message(ADMIN_ID, info_text)

    # ၂။ Customer ဆီသို့ သင်သတ်မှတ်ထားသော Auto Reply ချက်ချင်းပြန်ပို့ခြင်း
    reply_msg = build_auto_reply(user)
    bot.reply_to(message, reply_msg)

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    bot.infinity_polling()
  
