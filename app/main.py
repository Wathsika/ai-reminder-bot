import os
import discord
import pytz
import io
import speech_recognition as sr
from pydub import AudioSegment
from discord.ext import commands, tasks
# Added ChatHistory to imports
from app.database import init_db, SessionLocal, Reminder, ChatHistory 
from app.ai_logic import get_ai_response, get_reminders, complete_task
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Database
init_db()

# Setup Timezone
COLOMBO_TZ = pytz.timezone('Asia/Colombo')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_ID = os.getenv("ADMIN_ID")

def transcribe_audio(audio_bytes):
    """Transcribes audio bytes in-memory using Google Speech Recognition."""
    try:
        # Load audio from bytes (Discord uses OGG/Opus for voice messages)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Export to WAV in-memory
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # Transcribe using SpeechRecognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        return "[Could not understand audio]"
    except sr.RequestError as e:
        return f"[Speech Recognition API error: {e}]"
    except Exception as e:
        print(f"Transcription error: {e}")
        return "[Error processing audio]"

@bot.command()
async def reminders(ctx):
    """Lists all your reminders."""
    if str(ctx.author.id) != ADMIN_ID:
        return
    response = await bot.loop.run_in_executor(None, get_reminders, str(ctx.author.id))
    await ctx.send(response)

@bot.command()
async def done(ctx, task_id: int):
    """Marks a reminder as done."""
    if str(ctx.author.id) != ADMIN_ID:
        return
    response = await bot.loop.run_in_executor(None, complete_task, str(ctx.author.id), task_id)
    await ctx.send(response)

# --- NAGGING LOOP ---
@tasks.loop(minutes=1)
async def check_reminders():
    now = datetime.now(COLOMBO_TZ).replace(tzinfo=None)
    
    db = SessionLocal()
    try:
        due_tasks = db.query(Reminder).filter(Reminder.remind_at <= now).all()
        
        for r in due_tasks:
            user = bot.get_user(int(r.user_id)) or await bot.fetch_user(int(r.user_id))
            
            if user:
                if r.status == "PENDING":
                    msg_content = f"🔔 **REMINDER**: {r.task}!"
                    r.status = "NAGGING"
                else:
                    msg_content = f"❓ Still waiting on: **{r.task}**. Use `!done {r.id}` to stop this."
                
                await user.send(msg_content)

                # --- FIX: SAVE TO CHAT HISTORY ---
                # This is the "secret sauce" so the AI knows what it just sent you.
                history_entry = ChatHistory(
                    user_id=r.user_id, 
                    role="model", 
                    content=msg_content
                )
                db.add(history_entry)
                # ----------------------------------
                
                # Reschedule nag
                r.remind_at = now + timedelta(minutes=20)
        
        db.commit()
    except Exception as e:
        print(f"Error in nagging loop: {e}")
    finally:
        db.close()

# --- CLEANUP LOOP ---
@tasks.loop(hours=24)
async def cleanup_db():
    """Deletes chat history older than 30 days to prevent overstorage."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    db = SessionLocal()
    try:
        deleted_count = db.query(ChatHistory).filter(ChatHistory.timestamp < cutoff).delete()
        db.commit()
        if deleted_count > 0:
            print(f"🧹 Database Cleanup: Removed {deleted_count} old chat history records.")
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} is live!")
    if not check_reminders.is_running():
        check_reminders.start()
    if not cleanup_db.is_running():
        cleanup_db.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if str(message.author.id) != ADMIN_ID:
        return

    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.process_commands(message)
        return

    user_input = message.content

    # Handle Audio Attachments
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("audio/"):
                async with message.channel.typing():
                    audio_bytes = await attachment.read()
                    transcription = await bot.loop.run_in_executor(None, transcribe_audio, audio_bytes)
                    if transcription:
                        user_input = f"{user_input} [Audio Message]: {transcription}".strip()
                break # Process only the first audio attachment for now

    if not user_input:
        return

    async with message.channel.typing():
        try:
            # get_ai_response now handles database history internally
            response = await bot.loop.run_in_executor(
                None, 
                get_ai_response, 
                user_input, 
                str(message.author.id)
            )
            if response:
                await message.channel.send(response)
        except Exception as e:
            # Avoid sending long error stack traces to Discord
            print(f"AI error: {e}")
            await message.channel.send("❌ Something went wrong with the AI.")

# Start the bot
bot.run(os.getenv("DISCORD_TOKEN"))