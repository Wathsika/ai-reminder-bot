import os
import discord
from discord.ext import commands, tasks
from app.ai_logic import get_ai_response
from app.database import SessionLocal, Reminder 
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- THE NAGGING LOOP ---
# This runs every 1 minute in the background
@tasks.loop(minutes=1)
async def check_reminders():
    db = SessionLocal()
    now = datetime.now()
    # Find reminders that are due and NOT completed
    due_tasks = db.query(Reminder).filter(Reminder.remind_at <= now).all()
    
    for r in due_tasks:
        user = await bot.fetch_user(int(r.user_id))
        if user:
            if r.status == "PENDING":
                await user.send(f"🔔 REMINDER: {r.task}!")
                r.status = "NAGGING"
                r.remind_at = now + timedelta(minutes=20) # Nag in 20 mins
            else:
                await user.send(f"❓ Did you finish this yet?: {r.task}")
                r.remind_at = now + timedelta(minutes=20) # Keep nagging
        db.commit()
    db.close()

@bot.event
async def on_ready():
    check_reminders.start() # Start the nagging clock
    print(f"✅ Bot Online: {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user or str(message.author.id) != os.getenv("ADMIN_ID"):
        return

    # Process AI Response
    async with message.channel.typing():
        response = get_ai_response(message.content, str(message.author.id))
        await message.channel.send(response)

bot.run(os.getenv("DISCORD_TOKEN"))