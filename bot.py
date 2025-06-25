import os
import re
import logging
import requests
import trafilatura
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_USERS = set(map(int, os.getenv("ALLOWED_USERS", "").split(",")))

if not BOT_TOKEN or not GEMINI_API_KEY or not ALLOWED_USERS:
    raise RuntimeError("Missing required environment variables.")

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
HEADERS = {"Content-Type": "application/json"}
user_lang = {}

# --- UTILS ---
def extract_link(text, entities=None):
    if entities:
        for entity in entities:
            if entity.type == "text_link":
                return entity.url
            if entity.type == "url":
                return text[entity.offset:entity.offset + entity.length]
    match = re.search(r'https?://\S+', text or "")
    if match:
        return match.group(0)
    match = re.search(r'\[.*?\]\((https?://.*?)\)', text or "")
    return match.group(1) if match else None

def extract_article_text(url):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded) if downloaded else None

def summarize_with_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(GEMINI_API_URL, headers=HEADERS, json=payload)
    if resp.status_code == 200:
        try:
            return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            raise ValueError("Invalid Gemini response format.")
    raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "👋 Welcome! Send me an article (image + caption + link).\nChoose language:",
        reply_markup=ReplyKeyboardMarkup([["English", "Hebrew"]], one_time_keyboard=True)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ALLOWED_USERS:
        user_lang[user_id] = update.message.text.lower()
        await update.message.reply_text(f"🌍 Language set to: {update.message.text.capitalize()}")

async def summarize_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    message = update.message
    if not message.caption:
        await update.message.reply_text("❌ Please send a message with a caption containing a link.")
        return

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
        f"סכם את המאמר ב-3 עד 5 נקודות קצרות. עצב את הפלט עם Markdown פשוט (כמו **bold**)."
        f"\nתתחיל כל בולט במקף (-) או באימוג׳י שמשתנה בהתאם לתוכן של אותו הבולט\n\n{article_text}"
        if lang == "hebrew"
        else f"Summarize the article in 3–5 short bullet points. Use simple Markdown formatting (like **bold**)."
             f"\nStart each bullet with a dash (-) or an emoji that varies based on the content of that bullet\n\n{article_text}"
    )

    try:
        summary = summarize_with_gemini(prompt)
        await update.message.reply_text(summary, parse_mode="Markdown")
    except Exception as e:
        logging.exception("Gemini HTTP API error:")
        await update.message.reply_text(f"⚠️ Gemini error: {str(e)}")

# --- RUN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.User(ALLOWED_USERS), set_language))
app.add_handler(MessageHandler(filters.ALL, summarize_article))
app.run_polling()