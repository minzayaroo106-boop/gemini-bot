import os
import threading
from flask import Flask
import telebot
from google import genai

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# အလုပ်လုပ်သော Gemini Model ကို အလိုအလျောက် ရှာဖွေပေးသည့် စနစ်
def ask_gemini(prompt):
    # ၁။ မော်ဒယ်အသစ်များကို အစဉ်လိုက် အရင်စမ်းမည်
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.0-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash"
    ]
    for model_name in models_to_try:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            return res.text
        except Exception:
            continue

    # ၂။ မရသေးပါက သင့် API Key တွင် ခွင့်ပြုထားသော မော်ဒယ်စာရင်းထဲမှ ရှာသုံးမည်
    for m in client.models.list():
        if "flash" in m.name.lower() or "gemini" in m.name.lower():
            try:
                res = client.models.generate_content(model=m.name, contents=prompt)
                return res.text
            except Exception:
                continue

    raise Exception("အသုံးပြုနိုင်သော Gemini Model ရှာမတွေ့ပါ။")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "မင်္ဂလာပါ! ကျွန်တော်က ၂၄ နာရီ အလုပ်လုပ်နေတဲ့ Gemini AI Bot ဖြစ်ပါတယ်။")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        reply_text = ask_gemini(message.text)
        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, f"အမှားအယွင်းတစ်ခု ဖြစ်ပွားနေပါသည်: {str(e)}")

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    bot.infinity_polling()
