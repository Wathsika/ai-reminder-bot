import os
import discord
import pytz
from discord.ext import commands, tasks
from app.database import init_db, SessionLocal, Reminder
from app.ai_logic import get_ai_response, get_reminders, complete_task
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Database
init_db()

# Setup Timezone (Must match ai_logic.py)
COLOMBO_TZ = pytz.timezone('Asia/Colombo')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Ensure ADMIN_ID is treated as a string for comparison
ADMIN_ID = os.getenv("ADMIN_ID")

@bot.command()
async def reminders(ctx):
    """Lists all your reminders."""
    if str(ctx.author.id) != ADMIN_ID:
        return
    # get_reminders is not async, so we run in executor to keep bot responsive
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
    # Use the same timezone as the AI
    now = datetime.now(COLOMBO_TZ).replace(tzinfo=None) # Strip tzinfo for DB comparison
    
    db = SessionLocal()
    try:
        # Fetch tasks that are due and not completed
        due_tasks = db.query(Reminder).filter(Reminder.remind_at <= now).all()
        
        for r in due_tasks:
            # Try to get user from cache, then fetch if needed
            user = bot.get_user(int(r.user_id)) or await bot.fetch_user(int(r.user_id))
            
            if user:
                if r.status == "PENDING":
                    await user.send(f"🔔 **REMINDER**: {r.task}!")
                    r.status = "NAGGING"
                else:
                    await user.send(f"❓ Still waiting on: **{r.task}**. Use `!done {r.id}` to stop this.")
                
                # Reschedule nag for 20 minutes from now
                r.remind_at = now + timedelta(minutes=20)
        
        db.commit()
    except Exception as e:
        print(f"Error in nagging loop: {e}")
    finally:
        db.close()

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} is live!")
    if not check_reminders.is_running():
        check_reminders.start()

@bot.event
async def on_message(message):
    # 1. Ignore own messages
    if message.author == bot.user:
        return

    # 2. Only respond to the Admin
    if str(message.author.id) != ADMIN_ID:
        return

    # 3. Process commands (like !done or !reminders)
    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.process_commands(message)
        return

    # 4. If not a command, send to AI
    async with message.channel.typing():
        try:
            # We pass the user_id to the AI so it can use tools automatically
            response = await bot.loop.run_in_executor(
                None, 
                get_ai_response, 
                message.content, 
                str(message.author.id)
            )
            if response:
                await message.channel.send(response)
        except Exception as e:
            await message.channel.send(f"❌ AI Error: {e}")

# Start the bot
bot.run(os.getenv("DISCORD_TOKEN"))