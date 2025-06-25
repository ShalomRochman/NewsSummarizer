# 📰 Telegram News Summarizer Bot

This bot receives Telegram messages containing article links (as captions to images), extracts the full article content from the link, and summarizes it into 3–5 bullet points using the **Gemini 1.5 Flash** model. The bot supports Hebrew and English output, with concise Markdown formatting optimized for Telegram.

---

## 🚀 Features

- Summarizes online articles in under 5 bullets
- Supports both **English** and **Hebrew**
- Uses Google's **Gemini 1.5 Flash** API
- Telegram-friendly formatting (e.g. `**bold**`, emojis, dashes)
- Secure user authorization (`ALLOWED_USERS`)
- Easy deployment on **Oracle Cloud**, **Fly.io**, or any VM

---

## 🛠️ Requirements

- Python 3.11+
- Telegram Bot Token
- Gemini API Key from Google AI Studio

---

## 📦 Installation

1. **Clone the repository** (or copy your files to the server):

   ```bash
   git clone git@github.com:ShalomRochman/NewsSummarizer.git
   cd NewsSummarizer
    ```

2. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3. **Create a .env file**:

   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ALLOWED_USERS=123456789,987654321  # Comma-separated Telegram user IDs
   ```
4. **Run the bot**:

    ```bash
    python bot.py
    ```

---
   
## 🔑 How to Get the Required Tokens

1. `BOT_TOKEN` - **Get your Telegram Bot Token**:
   - Create a new bot using [BotFather](https://t.me/botfather) on Telegram.
   - Send `/newbot` and follow the instructions.
   - Once your bot is created, BotFather will provide you with a token (e.g., `123456789:ABCdefGhIJKlmnoPQRstuVWXyZ`).


2. `GEMINI_API_KEY` - **Get your Gemini API Key**:
   - Sign up or log in to [Google AI Studio](https://ai.google.com/).
   - Press "Get API Key" and follow the instructions to create a new API key.
   - Copy the API key and paste it into your `.env` file.


3. `ALLOWED_USERS` - **Set allowed users**:
   - Add your Telegram user ID and any other users you want to allow to interact with the bot.
   - You can find your user ID using the bot [@userinfobot](https://t.me/userinfobot) on Telegram.
   - Format the IDs as a comma-separated list in the `.env` file (e.g., `123456789,987654321`).

---

## 📖 Usage
- Start the bot with /start.
- Choose your preferred language.
- Send an article link as a caption to an image.
- The bot will fetch the article and return a short summary in your chosen language.

---

## 🔐 Security Notes
- The bot only allows interactions with users listed in ALLOWED_USERS.
- Avoid hardcoding secrets; use a .env file and python-dotenv.

---

## 📋 License
MIT License © 2025 Your Name
