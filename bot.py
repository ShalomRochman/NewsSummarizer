import re
import os
import logging
import requests
import trafilatura
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
try:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise KeyError
except KeyError:
    raise KeyError("BOT_TOKEN environment variable not set")

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise KeyError
except KeyError:
    raise KeyError("GEMINI_API_KEY environment variable not set")

try:
    ALLOWED_USERS = set([int(uid) for uid in os.getenv("ALLOWED_USERS").split(",")])
except KeyError:
    raise KeyError("ALLOWED_USERS environment variable not set")

# --- INIT ---
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
HEADERS = {
    "Content-Type": "application/json",
}
user_lang = {}
logging.basicConfig(level=logging.INFO)

# --- UTILS ---
def extract_link(text: str, entities=None) -> str | None:
    if entities:
        for entity in entities:
            if entity.type == "text_link":
                return entity.url
            elif entity.type == "url":
                offset = entity.offset
                length = entity.length
                return text[offset:offset + length]

    match = re.search(r'https?://\S+', text or "")
    if match:
        return match.group(0)

    match = re.search(r'\[.*?\]\((https?://.*?)\)', text or "")
    if match:
        return match.group(1)

    return None

def extract_article_text(url: str) -> str | None:
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return trafilatura.extract(downloaded)
    return None

def summarize_with_gemini(prompt: str) -> str:
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    response = requests.post(GEMINI_API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            raise ValueError("Invalid Gemini response format.")
    else:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "👋 Welcome! Send me an article (image + caption + link).\nChoose language:",
        reply_markup=ReplyKeyboardMarkup([["English", "Hebrew"]], one_time_keyboard=True)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ALLOWED_USERS:
        lang = update.message.text.lower()
        user_lang[user_id] = lang
        await update.message.reply_text(f"🌍 Language set to: {lang.capitalize()}")

async def summarize_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    message = update.message
    if message.caption:
        link = extract_link(message.caption, message.caption_entities)
        if not link:
            await update.message.reply_text("❌ Couldn't detect a link.")
            return

        await update.message.reply_text("🔍 Fetching article...")
        article_text = extract_article_text(link)

        if not article_text or len(article_text) < 100:
            await update.message.reply_text("⚠️ Couldn’t extract meaningful article content.")
            return

        lang = user_lang.get(user_id, "english")
        prompt = (
            f"סכם בקצרה ממש את המאמר ב-3-5 נקודות קצרות "
            f"(מאחר שבפלט שלך נשלח לבוט בטלגרם, בבקשה תתאים את סגנון הטקסט לסגנון של הפונט סטייל בטלגרם):\n\n{article_text}"
            if lang == "hebrew"
            else f"Give a very brief summary of the article in 3-5 concise bullets "
                 f"(as your output is sent to a Telegram bot, please adjust the text style to Telegram font style):\n\n{article_text}"
        )

        try:
            summary = summarize_with_gemini(prompt)
            await update.message.reply_text(summary)
        except Exception as e:
            logging.exception("Gemini HTTP API error:")
            await update.message.reply_text(f"⚠️ Gemini error: {str(e)}")
    else:
        await update.message.reply_text("❌ Please send a message with a caption containing a link.")

# --- RUN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.User(ALLOWED_USERS), set_language))
app.add_handler(MessageHandler(filters.ALL, summarize_article))
app.run_polling()
