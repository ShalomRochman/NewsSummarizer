"""
Telegram News Summarizer Bot

This bot allows whitelisted users to send a Telegram message containing a news link
and receive a concise summary (3–5 bullets) using Google Gemini 1.5 Flash API.
"""

import os
import re
import logging
from typing import Optional, Dict, Set

import requests
import trafilatura
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Load and validate environment variables ---
load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
ALLOWED_USERS: Set[int] = set(map(int, os.getenv("ALLOWED_USERS", "").split(",")))

if not BOT_TOKEN or not GEMINI_API_KEY or not ALLOWED_USERS:
    raise RuntimeError("Missing required environment variables.")

# --- Constants ---
GEMINI_API_URL: str = (
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    f"?key={GEMINI_API_KEY}"
)
HEADERS: Dict[str, str] = {"Content-Type": "application/json"}

user_lang: Dict[int, str] = {}
logging.basicConfig(level=logging.INFO)


# --- Utility Functions ---
def extract_link(text: Optional[str], entities=None) -> Optional[str]:
    """Extract the first URL from Telegram message text or entities.

    Parameters
    ----------
    text : str or None
        The message text (caption).
    entities : list or None
        Optional list of Telegram entities.

    Returns
    -------
    str or None
        The extracted URL, or None if not found.
    """
    if entities:
        for entity in entities:
            if entity.type == "text_link":
                return entity.url
            if entity.type == "url":
                return text[entity.offset : entity.offset + entity.length]

    if text:
        match = re.search(r'https?://\S+', text)
        if match:
            return match.group(0)

        match = re.search(r'\[.*?\]\((https?://.*?)\)', text)
        if match:
            return match.group(1)

    return None


def extract_article_text(url: str) -> Optional[str]:
    """Fetch and extract the main text content of an article from a URL.

    Parameters
    ----------
    url : str
        The URL of the article.

    Returns
    -------
    str or None
        The extracted article text, or None if extraction fails.
    """
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded) if downloaded else None


def summarize_with_gemini(prompt: str) -> str:
    """Generate a summary using the Gemini API.

    Parameters
    ----------
    prompt : str
        The prompt to send to Gemini.

    Returns
    -------
    str
        The summary returned by Gemini.

    Raises
    ------
    RuntimeError
        If Gemini API call fails.
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except (KeyError, IndexError):
            raise ValueError("Invalid Gemini response format.")
    raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")


# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command, set language preference."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    await update.message.reply_text(
        "👋 Welcome! Send me an article (image + caption + link).\nChoose language:",
        reply_markup=ReplyKeyboardMarkup([['English', 'Hebrew']], one_time_keyboard=True)
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user language preference."""
    user_id = update.effective_user.id
    if user_id in ALLOWED_USERS:
        selected_lang = update.message.text.lower()
        user_lang[user_id] = selected_lang
        await update.message.reply_text(f"🌍 Language set to: {selected_lang.capitalize()}")


async def summarize_article(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main handler to process forwarded messages and return article summaries."""
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


# --- Run Application ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.User(ALLOWED_USERS), set_language))
app.add_handler(MessageHandler(filters.ALL, summarize_article))
app.run_polling()
