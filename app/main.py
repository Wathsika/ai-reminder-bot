import os
import discord
import pytz
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

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} is live!")
    if not check_reminders.is_running():
        check_reminders.start()

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

    async with message.channel.typing():
        try:
            # get_ai_response now handles database history internally
            response = await bot.loop.run_in_executor(
                None, 
                get_ai_response, 
                message.content, 
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