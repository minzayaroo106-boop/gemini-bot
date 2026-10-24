import os
import threading
from flask import Flask
import telebot
from google import genai

# Render ၏ Environment Variables မှ Key များကို လှမ်းယူခြင်း
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Render မအိပ်သွားစေရန် အသေးစား Web Server တည်ဆောက်ခြင်း
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Telegram Bot လုပ်ဆောင်ချက်များ
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "မင်္ဂလာပါ! ကျွန်တော်က ၂၄ နာရီ အလုပ်လုပ်နေတဲ့ Gemini AI Bot ဖြစ်ပါတယ်။")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message.text
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"အမှားအယွင်းတစ်ခု ဖြစ်ပွားနေပါသည်: {str(e)}")

if __name__ == "__main__":
    # Web server ကို နောက်ကွယ် (Background) တွင် စတင် run ခြင်း
    t = threading.Thread(target=run_web)
    t.start()
    
    # Bot ကို စတင် run ခြင်း
    print("Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    bot.infinity_polling()
