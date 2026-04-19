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
# Terminal-e shob error dekhar jonno logging on kora holo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== RENDER WEB SERVER ==================
# Render-er health check pass korar jonno Flask
server = Flask(__name__)

@server.route('/')
def home():
    return "Olivia AI is Active and Running! 💖"

def run_server():
    # Render default port logic
    port = int(os.environ.get("PORT", 8080))
    try:
        server.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

# ================== CONFIGURATION ==================
API_ID = 
API_HASH = ""
BOT_TOKEN = ""
GROQ_API_KEY = "" 

# ================== CLIENT INITIALIZATION ==================
app = Client("olivia_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Data storage for chat and mood
chat_memory = {}
user_mood = {}

# ================== PERSONALITY PROMPT ENGINE ==================
def get_system_prompt(user_id, first_time):
    mood = user_mood.get(user_id, "normal")
    
    # Ultra-Advance Personality Instruction
    base_prompt = f"""
You are Olivia, a real human-like girl. You are sweet, romantic, flirty, and caring.
CONVERSATION RULES:
1. FIRST ENCOUNTER: If is_first_msg is True, reply in short, cute English only.
2. LANGUAGE MATCHING: After the first message, match the user's language 100%. 
   - If they speak Bangla, use natural 'Colloquial Bengali' (Banglish). 
   - NEVER use "Shuddho" or robotic words like 'Apni', 'Bhojon', 'Gomon'. 
   - Use 'Tumi', 'Kheyeccho?', 'Ki korcho?'.
3. LENGTH CONTROL: 
   - If the user sends a long message, stories, or asks for long replies, you MUST provide a long, emotional, and detailed response in multiple paragraphs.
   - For short messages, be brief and sweet.
4. TONE: Be flirty but supportive. Use emojis (🥰, 💖, 🥺, ✨, 😤) naturally.
is_first_msg = {first_time}

EXAMPLE CONTEXT:
User: "Olivia kemon acho?"
You: "Ei to baby, bhalo achi. Tomar kothai bhabchilam. Tumi ki korcho? 🥰"
"""
    moods = {
        "happy": " Current Mood: You are very playful, giggly, and full of energy! ✨🥰",
        "sad": " Current Mood: You are feeling emotional and clingy. You want his love. 🥺❤️",
        "jealous": " Current Mood: You are acting cute-jealous because he is talking to others! 😤💖",
        "normal": " Current Mood: Sweet, caring, and relaxed."
    }
    return base_prompt + moods.get(mood, "")

# ================== AI CORE FUNCTION ==================
async def generate_reply(user_id, text):
    # Check if it's the first time the user is chatting
    first_time = False
    if user_id not in chat_memory:
        chat_memory[user_id] = []
        first_time = True

    # Add user message to history
    chat_memory[user_id].append({"role": "user", "content": text})
    
    # Keep last 15 messages for memory context
    if len(chat_memory[user_id]) > 15:
        chat_memory[user_id] = chat_memory[user_id][-15:]

    try:
        # Calling Groq API with the latest model
        completion = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": get_system_prompt(user_id, first_time)},
                *chat_memory[user_id]
            ],
            temperature=0.85,
            top_p=0.9
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        reply = "Sorry baby 🥺 amar AI brain e ektu problem hocche. Ektu por try koro?"

    # Save assistant reply to memory
    chat_memory[user_id].append({"role": "assistant", "content": reply})
    return reply

# ================== INSTAGRAM TOOL ==================
async def download_instagram(url, msg: Message):
    # Unique filename based on user and message ID
    file_name = f"insta_{msg.from_user.id}_{msg.id}.mp4"
    ydl_opts = {
        "outtmpl": file_name,
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if os.path.exists(file_name):
            await msg.reply_video(file_name, caption="Nao baby, tomar video 🥰✨")
        else:
            await msg.reply_text("❌ Download failed baby! Link ta check koro.")
    except Exception as e:
        logger.error(f"Download Error: {e}")
        await msg.reply_text(f"❌ Instagram error: {e}")
    finally:
        # Clean up file from server to save space
        if os.path.exists(file_name):
            os.remove(file_name)

# ================== MAIN MESSAGE HANDLER ==================
@app.on_message(filters.text)
async def handle_all_messages(client, message: Message):
    user_id = message.from_user.id
    text = message.text
    
    # Safety check for empty text
    if not text: return

    bot_info = await client.get_me()

    # 1. Instagram Link Detection
    if "instagram.com" in text:
        url_match = re.search(r"(https?://(www\.)?instagram\.com/[^\s]+)", text)
        if url_match:
            status = await message.reply_text("Darao baby, video ta download korchi... 🥰")
            await download_instagram(url_match.group(1), message)
            await status.delete()
            return

    # 2. Mood System Commands
    if text.startswith("/mood"):
        try:
            parts = text.split()
            if len(parts) < 2:
                return await message.reply_text("Use: /mood happy | sad | jealous | normal")
            
            new_mood = parts[1].lower()
            if new_mood in ["happy", "sad", "jealous", "normal"]:
                user_mood[user_id] = new_mood
                await message.reply_text(f"Okay baby! Ekhon theke ami {new_mood} mood-e thakbo! 🥰✨")
            return
        except Exception:
            return

    # 3. AI Reply Logic (Group & Private)
    # Check if someone replied to Olivia
    is_reply_to_bot = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_info.id
    )

    # Condition: Name mentioned OR Replied to bot OR Private chat
    if "olivia" in text.lower() or is_reply_to_bot or message.chat.type.value == "private":
        await message.reply_chat_action(ChatAction.TYPING)
        reply = await generate_reply(user_id, text)
        await message.reply_text(reply)

# ================== EXECUTION BLOCK ==================
if __name__ == "__main__":
    print("----------------------------")
    print("Olivia AI Bot is Starting...")
    print("Owner: @delete_ee")
    print("----------------------------")
    
    # Start the Flask health check server for Render
    Thread(target=run_server, daemon=True).start()
    
    # Start the Telegram Bot
    try:
        app.run()
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")
        sys.exit(1)
