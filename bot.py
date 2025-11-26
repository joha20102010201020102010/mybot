import telebot
from telebot import types
import os
from flask import Flask, request

# 🔹 Tokenni muhit o'zgaruvchisidan olamiz
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

users = {}
waiting = []

CHANNEL_1 = "https://t.me/web_saites"
CHANNEL_2 = "https://t.me/AI_SI_II"

# ------------------------
# START COMMAND
# ------------------------
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.chat.id
    users[user_id] = {
        "gender": None,
        "age": None,
        "looking_for": None,
        "partner": None,
        "status": "none"
    }

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("1-kanal", url=CHANNEL_1))
    kb.add(types.InlineKeyboardButton("2-kanal", url=CHANNEL_2))

    bot.send_message(
        user_id,
        "📢 *Iltimos homiy kanallarimizga obuna bo‘ling*\n\n"
        "Obuna shart emas, davom etishingiz mumkin.",
        parse_mode="Markdown",
        reply_markup=kb
    )
    bot.send_message(user_id, "Registratsiya uchun /run bosing.")

# ------------------------
# RUN — GENDER SELECT
# ------------------------
@bot.message_handler(commands=['run'])
def run_reg(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("👦 O‘g‘il", "👧 Qiz")
    bot.send_message(msg.chat.id, "Jinsingizni tanlang:", reply_markup=kb)

# ------------------------
# GENDER SAVE → AGE
# ------------------------
@bot.message_handler(func=lambda m: m.text in ["👦 O‘g‘il", "👧 Qiz"])
def set_gender(msg):
    user = users[msg.chat.id]
    user["gender"] = "male" if msg.text == "👦 O‘g‘il" else "female"

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("-18", "18-20", "20-25", "25+")

    bot.send_message(msg.chat.id, "Yoshingizni tanlang:", reply_markup=kb)

# ------------------------
# AGE SELECTED
# ------------------------
@bot.message_handler(func=lambda m: m.text in ["-18", "18-20", "20-25", "25+"])
def set_age(msg):
    users[msg.chat.id]["age"] = msg.text
    bot.send_message(msg.chat.id, "Hammasi tayyor!\n\nChatni boshlash uchun 👉 /hi")

# ------------------------
# HI — CHOOSE PARTNER GENDER
# ------------------------
@bot.message_handler(commands=['hi'])
def hi_cmd(msg):
    user = users[msg.chat.id]

    if user["gender"] is None or user["age"] is None:
        bot.send_message(msg.chat.id, "Avval /run orqali registratsiya qiling.")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👦 O‘g‘il qidirish", "👧 Qiz qidirish", "♻ Farqi yo‘q")

    bot.send_message(msg.chat.id, "Qaysi jinsni qidirasiz?", reply_markup=kb)

# ------------------------
# CHOOSE PARTNER GENDER → MATCHING
# ------------------------
@bot.message_handler(func=lambda m: m.text in ["👦 O‘g‘il qidirish", "👧 Qiz qidirish", "♻ Farqi yo‘q"])
def look_for(msg):
    user_id = msg.chat.id
    user = users[user_id]

    if msg.text == "👦 O‘g‘il qidirish":
        user["looking_for"] = "male"
    elif msg.text == "👧 Qiz qidirish":
        user["looking_for"] = "female"
    else:
        user["looking_for"] = "any"

    bot.send_message(user_id, "🔎 Sobesednik qidirilmoqda...")

    for other_id in waiting:
        other = users[other_id]

        if user["looking_for"] != "any" and user["looking_for"] != other["gender"]:
            continue
        if other["looking_for"] != "any" and other["looking_for"] != user["gender"]:
            continue
        if user["age"] != other["age"]:
            continue

        waiting.remove(other_id)

        user["partner"] = other_id
        other["partner"] = user_id
        user["status"] = "in_chat"
        other["status"] = "in_chat"

        bot.send_message(user_id, "🎉 Sobesednik topildi! Chat boshlang.")
        bot.send_message(other_id, "🎉 Sobesednik topildi! Chat boshlang.")
        return

    waiting.append(user_id)
    user["status"] = "search"

    bot.send_message(user_id, "❗ Sizning yoshingizga mos odam topilmadi.\n"
                              "Biroz kuting, balki hozir oflayn bo‘lishi mumkin.")

# ----------------------------------------
# FORWARD TEXT
# ----------------------------------------
@bot.message_handler(content_types=['text'])
def chat_text(msg):
    user_id = msg.chat.id
    user = users.get(user_id)

    if not user or user["status"] != "in_chat":
        return

    partner = user["partner"]
    if partner:
        bot.send_message(partner, "👤≈ Sobesednik:\n" + msg.text)

# ----------------------------------------
# FORWARD MEDIA
# ----------------------------------------
@bot.message_handler(content_types=['photo', 'video', 'voice', 'audio', 'document', 'sticker'])
def media_forward(msg):
    user_id = msg.chat.id
    user = users.get(user_id)

    if not user or user["status"] != "in_chat":
        return

    partner = user["partner"]

    if msg.content_type == 'sticker':
        bot.send_sticker(partner, msg.sticker.file_id)
    elif msg.content_type == 'voice':
        bot.send_voice(partner, msg.voice.file_id)
    elif msg.content_type == 'photo':
        bot.send_photo(partner, msg.photo[-1].file_id)
    elif msg.content_type == 'video':
        bot.send_video(partner, msg.video.file_id)
    elif msg.content_type == 'audio':
        bot.send_audio(partner, msg.audio.file_id)
    elif msg.content_type == 'document':
        bot.send_document(partner, msg.document.file_id)

# ----------------------------------------
# FLASK + WEBHOOK (Render uchun)
# ----------------------------------------
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    data = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(data)
    bot.process_new_updates([update])
    return '', 200

@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    port = int(os.environ.get("PORT", 10000))  # Render port
    app.run(host='0.0.0.0', port=port)
