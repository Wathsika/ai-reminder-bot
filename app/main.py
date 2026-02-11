import os
import discord
from discord.ext import commands, tasks
from app.database import init_db, SessionLocal, Reminder
from app.ai_logic import get_ai_response
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
init_db()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_ID = os.getenv("ADMIN_ID")

# --- NAGGING LOOP ---
@tasks.loop(minutes=1)
async def check_reminders():
    db = SessionLocal()
    now = datetime.now()
    due_tasks = db.query(Reminder).filter(Reminder.remind_at <= now).all()
    
    for r in due_tasks:
        user = await bot.fetch_user(int(r.user_id))
        if user:
            if r.status == "PENDING":
                await user.send(f"🔔 **REMINDER**: {r.task}!")
                r.status = "NAGGING"
                # Set next nag for 20 mins from now
                r.remind_at = now + timedelta(minutes=20)
            else:
                await user.send(f"❓ Still waiting on: **{r.task}**. Done yet?")
                r.remind_at = now + timedelta(minutes=20)
        db.commit()
    db.close()

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} is live on AWS!")
    check_reminders.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if str(message.author.id) != ADMIN_ID: return

    async with message.channel.typing():
        response = get_ai_response(message.content, str(message.author.id))
        await message.channel.send(response)

bot.run(os.getenv("DISCORD_TOKEN"))