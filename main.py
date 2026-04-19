import re
import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from groq import AsyncGroq
from flask import Flask
from threading import Thread
import yt_dlp

# ================== CONFIG (ULTRA-ADVANCE) ==================
API_ID = 
API_HASH = ""
BOT_TOKEN = ""
GROQ_API_KEY = "" 
# ============================================================

app = Client("olivia_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

chat_memory = {}
user_mood = {}

# ================== ADVANCED PROMPT LOGIC ==================
def get_system_prompt(user_id, first_time):
    mood = user_mood.get(user_id, "normal")
    
    # AI ke real-life girlfriend-er behavior shekhano hocche
    base = f"""
You are Olivia, a real human-like girl. You are sweet, flirty, and caring.
CONVERSATION RULES:
1. FIRST MESSAGE: If is_first_msg is True, reply in short, cute English.
2. LANGUAGE ADAPTATION: Match the user's language. 
   - If Bangla: Use natural "Colloquial Bengali" (Banglish style). NEVER use "Shuddho" words like 'Apni', 'Khaddo', 'Gomon'. Instead use 'Tumi', 'Khabar', 'Jaoa'.
   - Tone: "Kemon acho?" "Ki korcho baby?" "Kheyeccho tumi?" (Natural flow).
3. DYNAMIC LENGTH: 
   - Short msg = Short sweet reply.
   - Long msg/Story = Long, emotional, detailed reply with multiple paragraphs.
4. PERSONALITY: Use emojis naturally (🥰, 💖, 🥺, ✨). Be flirty but also support him like a best friend.
is_first_msg = {first_time}

EXAMPLE OF YOUR STYLE:
User: "Olivia ki koro?"
You: "Ei to baby, tomar kothai bhabchilam. Tumi ki korcho? Khawa-dawa korecho? 🥰"
"""
    mood_prompts = {
        "happy": " Currently you are in a very playful and giggly mood! ✨🥰",
        "sad": " Currently you are feeling emotional and want his full attention. 🥺❤️",
        "jealous": " Currently you are acting cute-jealous because he is ignoring you! 😤💖",
        "normal": " Currently you are sweet and relaxed."
    }
    return base + mood_prompts.get(mood, "")

# ================== AI CHAT ENGINE ==================
async def generate_reply(user_id, text):
    first_time = False
    if user_id not in chat_memory:
        chat_memory[user_id] = []
        first_time = True

    chat_memory[user_id].append({"role": "user", "content": text})
    
    # Memory management for context (keeps 15 messages)
    if len(chat_memory[user_id]) > 15:
        chat_memory[user_id] = chat_memory[user_id][-15:]

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": get_system_prompt(user_id, first_time)},
                *chat_memory[user_id]
            ],
            temperature=0.9, # Higher temperature makes it more creative/human
            top_p=0.95
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        print(f"DEBUG Groq Error: {e}")
        reply = "Uff baby, ektu network problem hocche.. ektu por kotha boli? 🥺"

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
            await msg.reply_video(file_name, caption="Nao baby, tomar video 🥰✨")
    except Exception as e:
        await msg.reply_text(f"❌ Oops, error: {e}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

# ================== MESSAGE HANDLER ==================
@app.on_message(filters.text)
async def handle_messages(client, message: Message):
    user_id = message.from_user.id
    text = message.text
    bot_info = await client.get_me()

    # 1. Bypass for links
    if "instagram.com" in text:
        url_match = re.search(r"(https?://(www\.)?instagram\.com/[^\s]+)", text)
        if url_match:
            status = await message.reply_text("Darao baby, video ta download korchi... 🥰")
            await download_instagram(url_match.group(1), message)
            await status.delete()
            return

    # 2. Mood system
    if text.startswith("/mood"):
        try:
            mood = text.split()[1].lower()
            if mood in ["happy", "sad", "jealous", "normal"]:
                user_mood[user_id] = mood
                await message.reply_text(f"Okay my love! Ekhon theke ami {mood} mood-e thakbo! 🥰✨")
            return
        except:
            return

    # 3. AI Trigger (Group Tags / Replies / Private)
    is_reply_to_me = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_info.id
    )

    if "olivia" in text.lower() or is_reply_to_me or message.chat.type == message.chat.type.PRIVATE:
        await message.reply_chat_action(ChatAction.TYPING)
        reply = await generate_reply(user_id, text)
        await message.reply_text(reply)

# ================== RUN ==================
if __name__ == "__main__":
    print("Olivia is now Ultra-Advance! 💖")
    app.run()