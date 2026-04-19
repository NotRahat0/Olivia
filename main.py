import re
import asyncio
import os
import sys
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from groq import AsyncGroq
import yt_dlp
from flask import Flask
from threading import Thread

# ================== LOGGING SETUP ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================== RENDER WEB SERVER ==================
server = Flask(__name__)

@server.route('/')
def home():
    return "Olivia AI is online! 💖"

def run_server():
    # Render automatic 'PORT' environment variable provide kore
    port = int(os.environ.get("PORT", 8080))
    try:
        logger.info(f"Starting Flask server on port {port}")
        server.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

# ================== CONFIGURATION (SECURE) ==================
# Os.environ.get use kora hoyeche jate Render theke data nite pare
API_ID_ENV = os.environ.get("API_ID")
API_HASH_ENV = os.environ.get("API_HASH")
BOT_TOKEN_ENV = os.environ.get("BOT_TOKEN")
GROQ_API_KEY_ENV = os.environ.get("GROQ_API_KEY")

# Safety check: Environment variables missing thakle error dibe
if not all([API_ID_ENV, API_HASH_ENV, BOT_TOKEN_ENV, GROQ_API_KEY_ENV]):
    logger.critical("One or more Environment Variables are missing! Check Render Settings.")
    # Agar variable na thake, manually hardcode kore deya holo (Only for emergency)
    API_ID = 30836681
    API_HASH = "1c8a1a16a0b66fd24108b24dae8c8a26"
    BOT_TOKEN = "8628834580:AAEh-Q9eTntpY84M_dEoiWMUGgXq442hgnk"
    GROQ_API_KEY = "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"
else:
    API_ID = int(API_ID_ENV)
    API_HASH = API_HASH_ENV
    BOT_TOKEN = BOT_TOKEN_ENV
    GROQ_API_KEY = GROQ_API_KEY_ENV

# ================== CLIENT INITIALIZATION ==================
app = Client("olivia_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

chat_memory = {}
user_mood = {}

# ================== PERSONALITY PROMPT ENGINE ==================
def get_system_prompt(user_id, first_time):
    mood = user_mood.get(user_id, "normal")
    base_prompt = f"""
You are Olivia, a real human-like girl. You are sweet, flirty, and caring.
CONVERSATION RULES:
1. FIRST ENCOUNTER: If is_first_msg is True, reply in short, cute English.
2. LANGUAGE: Match the user's language. If Bangla, use natural 'Tumi' style. 
3. LENGTH: Match user's message length. Long for long, short for short.
4. PERSONALITY: Be flirty, emotional and natural.
is_first_msg = {first_time}
"""
    moods = {
        "happy": " Current Mood: Very playful and giggly! ✨🥰",
        "sad": " Current Mood: Feeling emotional and clingy. 🥺❤️",
        "jealous": " Current Mood: Acting cute-jealous! 😤💖",
        "normal": " Current Mood: Sweet and relaxed."
    }
    return base_prompt + moods.get(mood, "")

# ================== AI CORE FUNCTION ==================
async def generate_reply(user_id, text):
    first_time = False
    if user_id not in chat_memory:
        chat_memory[user_id] = []
        first_time = True

    chat_memory[user_id].append({"role": "user", "content": text})
    if len(chat_memory[user_id]) > 15:
        chat_memory[user_id] = chat_memory[user_id][-15:]

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "system", "content": get_system_prompt(user_id, first_time)}, *chat_memory[user_id]],
            temperature=0.85
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        reply = "Sorry baby 🥺 matha batha korche ektu."

    chat_memory[user_id].append({"role": "assistant", "content": reply})
    return reply

# ================== INSTAGRAM TOOL ==================
async def download_instagram(url, msg: Message):
    file_name = f"insta_{msg.from_user.id}_{msg.id}.mp4"
    ydl_opts = {"outtmpl": file_name, "format": "mp4", "quiet": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        if os.path.exists(file_name):
            await msg.reply_video(file_name, caption="Nao baby 🥰✨")
    except Exception as e:
        logger.error(f"Download Error: {e}")
        await msg.reply_text("❌ Download holo na baby!")
    finally:
        if os.path.exists(file_name): os.remove(file_name)

# ================== MESSAGE HANDLER ==================
@app.on_message(filters.text)
async def handle_all_messages(client, message: Message):
    if not message.text: return
    user_id = message.from_user.id
    text = message.text
    bot_info = await client.get_me()

    # Instagram Bypass
    if "instagram.com" in text:
        url_match = re.search(r"(https?://(www\.)?instagram\.com/[^\s]+)", text)
        if url_match:
            status = await message.reply_text("Darao baby... 🥰")
            await download_instagram(url_match.group(1), message)
            await status.delete()
            return

    # Mood Command
    if text.startswith("/mood"):
        try:
            parts = text.split()
            if len(parts) >= 2:
                new_mood = parts[1].lower()
                if new_mood in ["happy", "sad", "jealous", "normal"]:
                    user_mood[user_id] = new_mood
                    await message.reply_text(f"Okay baby! Ekhon theke ami {new_mood}! 🥰✨")
            return
        except: return

    # Trigger Logic
    is_reply_to_me = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_info.id
    )

    if "olivia" in text.lower() or is_reply_to_me or message.chat.type.value == "private":
        await message.reply_chat_action(ChatAction.TYPING)
        reply = await generate_reply(user_id, text)
        await message.reply_text(reply)

# ================== START ==================
if __name__ == "__main__":
    logger.info("Olivia AI is waking up... Owner: @delete_ee")
    # Health check server start
    Thread(target=run_server, daemon=True).start()
    # Bot run
    try:
        app.run()
    except Exception as e:
        logger.critical(f"Bot failed: {e}")
        sys.exit(1)
