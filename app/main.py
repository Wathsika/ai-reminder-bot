import os
import discord
from discord.ext import commands
from google import genai  # <--- New import style
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID')

# 2. Setup Gemini AI (New way for google-genai)
client = genai.Client(api_key=GEMINI_KEY)

# 3. Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # Force the status to Online
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="AI Reminders"))
    print(f'---------------------------------------')
    print(f'✅ SUCCESS: Bot is logged in as {bot.user}')
    print(f'---------------------------------------')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if str(message.author.id) != str(ADMIN_ID):
        return 

    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    # 4. Gemini AI Response (New way for google-genai)
    try:
        async with message.channel.typing():
            # Use the client object to generate content
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=message.content
            )
            await message.channel.send(response.text)
    except Exception as e:
        await message.channel.send(f"❌ Gemini Error: {e}")

@bot.command()
async def status(ctx):
    await ctx.send("🚀 System is online!")

if __name__ == "__main__":
    bot.run(TOKEN)