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

@server.route('/health')
def health():
    return "OK", 200

def run_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        logger.info(f"Starting Flask server on port {port}")
        # Use waitress or gunicorn for production
        server.run(host='0.0.0.0', port=port, threaded=True)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

# ================== CONFIGURATION ==================
# শুধু Environment Variables থেকে নিবে
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Validation
if not all([API_ID, API_HASH, BOT_TOKEN, GROQ_API_KEY]):
    logger.error("❌ Missing Environment Variables!")
    logger.error("Please set: API_ID, API_HASH, BOT_TOKEN, GROQ_API_KEY")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("❌ API_ID must be a number!")
    sys.exit(1)

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
            temperature=0.85,
            timeout=30.0  # Timeout যোগ করলাম
        )
        reply = completion.choices[0].message.content
    except asyncio.TimeoutError:
        logger.error(f"Groq Timeout Error for user {user_id}")
        reply = "Sorry baby 🥺 network ektu slow achhe."
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        reply = "Sorry baby 🥺 matha batha korche ektu."

    chat_memory[user_id].append({"role": "assistant", "content": reply})
    return reply

# ================== INSTAGRAM TOOL ==================
async def download_instagram(url, msg: Message):
    file_name = f"insta_{msg.from_user.id}_{msg.id}.mp4"
    ydl_opts = {
        "outtmpl": file_name, 
        "format": "mp4", 
        "quiet": True,
        "no_warnings": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
            await msg.reply_video(file_name, caption="Nao baby 🥰✨")
        else:
            await msg.reply_text("❌ Video download holo na baby!")
    except Exception as e:
        logger.error(f"Download Error: {e}")
        await msg.reply_text("❌ Download holo na baby! Link ta check koro.")
    finally:
        if os.path.exists(file_name): 
            try:
                os.remove(file_name)
            except:
                pass

# ================== MESSAGE HANDLER ==================
@app.on_message(filters.text)
async def handle_all_messages(client, message: Message):
    if not message.text: 
        return
    
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        bot_info = await client.get_me()
    except Exception as e:
        logger.error(f"Can't get bot info: {e}")
        return

    # Instagram Bypass
    if "instagram.com" in text:
        url_match = re.search(r"(https?://(?:www\.)?instagram\.com/[^\s]+)", text)
        if url_match:
            status = await message.reply_text("Darao baby... downloading 🥰")
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
                else:
                    await message.reply_text("Available moods: happy, sad, jealous, normal")
            return
        except Exception as e:
            logger.error(f"Mood command error: {e}")
            return

    # Trigger Logic
    is_reply_to_me = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_info.id
    )

    if "olivia" in text.lower() or is_reply_to_me or (message.chat and message.chat.type.value == "private"):
        try:
            await message.reply_chat_action(ChatAction.TYPING)
            reply = await generate_reply(user_id, text)
            # Split long messages
            if len(reply) > 4000:
                for i in range(0, len(reply), 4000):
                    await message.reply_text(reply[i:i+4000])
            else:
                await message.reply_text(reply)
        except Exception as e:
            logger.error(f"Reply error: {e}")
            await message.reply_text("Something went wrong baby 🥺")

# ================== ERROR HANDLERS ==================
@app.on_error()
async def error_handler(client, error):
    logger.error(f"Pyrogram Error: {error}")

# ================== START ==================
async def main():
    logger.info("🤖 Olivia AI is starting...")
    
    # Start health check server in background
    Thread(target=run_server, daemon=True).start()
    
    # Start bot
    logger.info("✅ Bot is running!")
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"❌ Bot failed: {e}")
        sys.exit(1)
